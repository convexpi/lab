#!/usr/bin/env python3
"""
fetch_full_text.py — Download arXiv PDFs and extract plain text for finance papers.

Reads papers from the Supabase `papers` table, downloads each paper's PDF from
arXiv (all ingested papers have an arxiv_id), extracts text with PyMuPDF, and
writes:

    CONVEXPI_DATA_DIR/pdf/{arxiv_id}.pdf        (raw PDF — kept off Dropbox)
    CONVEXPI_DATA_DIR/fulltext/{paper_id}.txt   (extracted text, read by generate_factor_wiki.py)

generate_factor_wiki.py's load_full_text() reads fulltext/{paper_id}.txt and
falls back to the abstract when it's missing — so running this first produces
richer, full-text-grounded wikis.

Usage:
    python pipeline/fetch_full_text.py                 # all papers without fulltext
    python pipeline/fetch_full_text.py --topic momentum
    python pipeline/fetch_full_text.py --limit 50
    python pipeline/fetch_full_text.py --force         # re-download existing
    python pipeline/fetch_full_text.py --keep-pdf      # keep PDFs (default deletes after extract)

Env vars:
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key
    CONVEXPI_DATA_DIR     data root (default: /Users/smc77/convexpi-data)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import httpx

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF is required: pip install pymupdf", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_DIR     = Path(os.environ.get("CONVEXPI_DATA_DIR", "/Users/smc77/convexpi-data"))
PDF_DIR      = DATA_DIR / "pdf"
FULLTEXT_DIR = DATA_DIR / "fulltext"

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

ARXIV_PDF = "https://arxiv.org/pdf/{arxiv_id}"

# Be a good arXiv citizen — they ask for a descriptive UA and modest rates.
USER_AGENT = "ConvexPi-Lab/1.0 (https://convexpi.ai; research pipeline)"
ARXIV_DELAY = 3.0  # seconds between PDF downloads


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def _supabase_headers() -> dict[str, str]:
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }


async def fetch_papers(topic: str | None, limit: int | None) -> list[dict]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    url = f"{SUPABASE_URL}/rest/v1/papers"
    params = {
        "select": "id,arxiv_id,title,topics",
        "arxiv_id": "not.is.null",
        "order": "citation_count.desc.nullslast",
    }
    if topic:
        params["topics"] = f'cs.["{topic}"]'  # JSONB array contains
    if limit:
        params["limit"] = str(limit)

    papers: list[dict] = []
    async with httpx.AsyncClient() as client:
        # Page through results
        offset = 0
        page = 1000
        while True:
            p = dict(params)
            p["offset"] = str(offset)
            p["limit"] = str(min(page, limit - offset)) if limit else str(page)
            resp = await client.get(url, params=p, headers=_supabase_headers(), timeout=30)
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            papers.extend(batch)
            offset += len(batch)
            if limit and len(papers) >= limit:
                return papers[:limit]
            if len(batch) < page:
                break
    return papers


# ---------------------------------------------------------------------------
# Download + extract
# ---------------------------------------------------------------------------

async def download_pdf(client: httpx.AsyncClient, arxiv_id: str, dest: Path) -> bool:
    url = ARXIV_PDF.format(arxiv_id=arxiv_id)
    try:
        resp = await client.get(url, follow_redirects=True, timeout=60)
        if resp.status_code != 200:
            log.warning("  arXiv returned %d for %s", resp.status_code, arxiv_id)
            return False
        if not resp.content.startswith(b"%PDF"):
            log.warning("  %s did not return a PDF (got %s)", arxiv_id, resp.headers.get("content-type"))
            return False
        dest.write_bytes(resp.content)
        return True
    except httpx.HTTPError as exc:
        log.warning("  download failed for %s: %s", arxiv_id, exc)
        return False


def extract_text(pdf_path: Path) -> str:
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:  # corrupt / encrypted
        log.warning("  could not open %s: %s", pdf_path.name, exc)
        return ""
    parts = []
    for page in doc:
        parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(parts).strip()


async def process_paper(
    client: httpx.AsyncClient,
    paper: dict,
    keep_pdf: bool,
    force: bool,
) -> str:
    """Returns one of: 'ok', 'skip', 'fail'."""
    paper_id = paper["id"]
    arxiv_id = paper["arxiv_id"]
    txt_path = FULLTEXT_DIR / f"{paper_id}.txt"

    if txt_path.exists() and not force:
        return "skip"

    pdf_path = PDF_DIR / f"{arxiv_id}.pdf"
    if not pdf_path.exists() or force:
        ok = await download_pdf(client, arxiv_id, pdf_path)
        if not ok:
            return "fail"

    text = extract_text(pdf_path)
    if len(text) < 500:  # extraction produced nothing usable
        log.warning("  extracted only %d chars from %s — skipping", len(text), arxiv_id)
        if not keep_pdf and pdf_path.exists():
            pdf_path.unlink()
        return "fail"

    txt_path.write_text(text, encoding="utf-8")
    if not keep_pdf and pdf_path.exists():
        pdf_path.unlink()
    return "ok"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    FULLTEXT_DIR.mkdir(parents=True, exist_ok=True)

    papers = await fetch_papers(args.topic, args.limit)
    log.info("Fetched %d papers with arXiv IDs", len(papers))

    counts = {"ok": 0, "skip": 0, "fail": 0}
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers) as client:
        for i, paper in enumerate(papers, 1):
            log.info("[%d/%d] %s  (%s)", i, len(papers),
                     paper["title"][:60], paper["arxiv_id"])
            result = await process_paper(client, paper, args.keep_pdf, args.force)
            counts[result] += 1
            # Only sleep when we actually hit arXiv
            if result != "skip":
                await asyncio.sleep(ARXIV_DELAY)

    log.info("Done. ok=%d skip=%d fail=%d  → fulltext in %s",
             counts["ok"], counts["skip"], counts["fail"], FULLTEXT_DIR)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download arXiv PDFs and extract full text.")
    p.add_argument("--topic", help="Only papers tagged with this topic")
    p.add_argument("--limit", type=int, help="Max papers to process")
    p.add_argument("--force", action="store_true", help="Re-download / re-extract existing")
    p.add_argument("--keep-pdf", action="store_true",
                   help="Keep downloaded PDFs (default: delete after extraction)")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
