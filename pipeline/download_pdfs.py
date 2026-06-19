#!/usr/bin/env python3
"""
download_pdfs.py — Download and keep arXiv PDFs for finance papers.

Reads papers from the Supabase `papers` table and downloads each paper's PDF
from arXiv (all ingested papers have an arxiv_id) to:

    CONVEXPI_DATA_DIR/pdf/{arxiv_id}.pdf

PDFs are kept on disk — they're the source of truth. Text is NOT extracted
here; generate_factor_wiki.py extracts text from these PDFs in real time at
generation time (and falls back to the abstract when a PDF is missing). Since
every paper is on arXiv, the PDFs are also directly viewable at
https://arxiv.org/abs/{arxiv_id}.

Usage:
    python pipeline/download_pdfs.py                 # all papers without a PDF
    python pipeline/download_pdfs.py --topic momentum
    python pipeline/download_pdfs.py --limit 50
    python pipeline/download_pdfs.py --force         # re-download existing

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

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("CONVEXPI_DATA_DIR", "/Users/smc77/convexpi-data"))
PDF_DIR  = DATA_DIR / "pdf"

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

ARXIV_PDF = "https://arxiv.org/pdf/{arxiv_id}"

# Be a good arXiv citizen — descriptive UA and modest request rate.
USER_AGENT = "ConvexPi-Lab/1.0 (https://convexpi.ai; research pipeline)"
ARXIV_DELAY = 3.0  # seconds between downloads


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

    papers: list[dict] = []
    async with httpx.AsyncClient() as client:
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
# Download
# ---------------------------------------------------------------------------

async def download_pdf(client: httpx.AsyncClient, arxiv_id: str, dest: Path) -> bool:
    url = ARXIV_PDF.format(arxiv_id=arxiv_id)
    try:
        resp = await client.get(url, follow_redirects=True, timeout=120)
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    papers = await fetch_papers(args.topic, args.limit)
    log.info("Fetched %d papers with arXiv IDs", len(papers))

    counts = {"ok": 0, "skip": 0, "fail": 0}
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        for i, paper in enumerate(papers, 1):
            arxiv_id = paper["arxiv_id"]
            dest = PDF_DIR / f"{arxiv_id}.pdf"

            if dest.exists() and not args.force:
                counts["skip"] += 1
                continue

            log.info("[%d/%d] %s  (%s)", i, len(papers), paper["title"][:60], arxiv_id)
            ok = await download_pdf(client, arxiv_id, dest)
            counts["ok" if ok else "fail"] += 1
            await asyncio.sleep(ARXIV_DELAY)

    log.info("Done. ok=%d skip=%d fail=%d  → PDFs in %s",
             counts["ok"], counts["skip"], counts["fail"], PDF_DIR)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download and keep arXiv PDFs.")
    p.add_argument("--topic", help="Only papers tagged with this topic")
    p.add_argument("--limit", type=int, help="Max papers to process")
    p.add_argument("--force", action="store_true", help="Re-download existing PDFs")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
