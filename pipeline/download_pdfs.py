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

With --include-oa, DOI-only papers (no arXiv id) additionally get a legal
open-access PDF via Unpaywall, saved to pdf/{doi-slug}.pdf. The arXiv path
stays the default/primary; --include-oa is off by default.

Usage:
    python pipeline/download_pdfs.py                 # all papers without a PDF
    python pipeline/download_pdfs.py --topic momentum
    python pipeline/download_pdfs.py --limit 50
    python pipeline/download_pdfs.py --force         # re-download existing
    python pipeline/download_pdfs.py --include-oa    # also OA PDFs for DOI-only papers

Env vars:
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key
    CONVEXPI_DATA_DIR     data root (default: /Users/smc77/convexpi-data)
    CONTACT_EMAIL         Unpaywall polite pool (default: shane.conway@gmail.com)
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
CONTACT_EMAIL        = os.environ.get("CONTACT_EMAIL", "shane.conway@gmail.com")

ARXIV_PDF      = "https://arxiv.org/pdf/{arxiv_id}"
UNPAYWALL_API  = "https://api.unpaywall.org/v2/{doi}"

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


async def fetch_papers(topic: str | None, limit: int | None,
                       include_oa: bool = False) -> list[dict]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    url = f"{SUPABASE_URL}/rest/v1/papers"
    params = {
        "select": "id,arxiv_id,doi,title,topics",
        "order": "citation_count.desc.nullslast",
    }
    if not include_oa:
        # Default behaviour: arXiv papers only.
        params["arxiv_id"] = "not.is.null"
    else:
        # Include DOI-only papers (no arXiv) so they can get an OA PDF.
        params["or"] = "(arxiv_id.not.is.null,doi.not.is.null)"
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
# Unpaywall open-access fallback (for DOI-only papers with no arXiv id)
# ---------------------------------------------------------------------------

def doi_slug(doi: str) -> str:
    """Filesystem-safe filename stem for a DOI (e.g. 10.1093/rfs/hhaa009)."""
    return doi.strip().lower().replace("/", "_").replace(":", "_")


async def unpaywall_pdf_url(doi: str, email: str = CONTACT_EMAIL) -> str | None:
    """Return the best open-access PDF URL for a DOI via Unpaywall, or None.

    Reads best_oa_location.url_for_pdf, falling back to .url, then scans all
    oa_locations for any url_for_pdf. Returns None for non-OA papers or errors.
    """
    url = UNPAYWALL_API.format(doi=doi.strip().lower())
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params={"email": email},
                                    follow_redirects=True, timeout=60)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("  Unpaywall lookup failed for %s: %s", doi, exc)
        return None

    best = data.get("best_oa_location") or {}
    if best.get("url_for_pdf"):
        return best["url_for_pdf"]
    if best.get("url"):
        return best["url"]
    for loc in data.get("oa_locations") or []:
        if loc.get("url_for_pdf"):
            return loc["url_for_pdf"]
    return None


async def download_oa_pdf(client: httpx.AsyncClient, url: str, dest: Path) -> bool:
    """Download an open-access PDF from an arbitrary URL."""
    try:
        resp = await client.get(url, follow_redirects=True, timeout=120)
        if resp.status_code != 200:
            log.warning("  OA host returned %d for %s", resp.status_code, url)
            return False
        if not resp.content.startswith(b"%PDF"):
            log.warning("  %s did not return a PDF (got %s)", url, resp.headers.get("content-type"))
            return False
        dest.write_bytes(resp.content)
        return True
    except httpx.HTTPError as exc:
        log.warning("  OA download failed for %s: %s", url, exc)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    papers = await fetch_papers(args.topic, args.limit, args.include_oa)
    log.info("Fetched %d papers%s", len(papers),
             " (arXiv + DOI-only)" if args.include_oa else " with arXiv IDs")

    counts = {"ok": 0, "skip": 0, "fail": 0, "oa": 0, "no_oa": 0}
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        for i, paper in enumerate(papers, 1):
            arxiv_id = paper.get("arxiv_id")

            if arxiv_id:
                # Primary path: arXiv PDF.
                dest = PDF_DIR / f"{arxiv_id}.pdf"
                if dest.exists() and not args.force:
                    counts["skip"] += 1
                    continue
                log.info("[%d/%d] %s  (%s)", i, len(papers), paper["title"][:60], arxiv_id)
                ok = await download_pdf(client, arxiv_id, dest)
                counts["ok" if ok else "fail"] += 1
                await asyncio.sleep(ARXIV_DELAY)
                continue

            # Fallback path (--include-oa): DOI-only paper → Unpaywall OA PDF.
            doi = paper.get("doi")
            if not args.include_oa or not doi:
                continue
            dest = PDF_DIR / f"{doi_slug(doi)}.pdf"
            if dest.exists() and not args.force:
                counts["skip"] += 1
                continue
            log.info("[%d/%d] %s  (doi:%s)", i, len(papers), paper["title"][:60], doi)
            oa_url = await unpaywall_pdf_url(doi)
            if not oa_url:
                counts["no_oa"] += 1
                continue
            ok = await download_oa_pdf(client, oa_url, dest)
            counts["oa" if ok else "fail"] += 1
            await asyncio.sleep(ARXIV_DELAY)

    log.info("Done. ok=%d oa=%d skip=%d fail=%d no_oa=%d  → PDFs in %s",
             counts["ok"], counts["oa"], counts["skip"], counts["fail"],
             counts["no_oa"], PDF_DIR)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download and keep arXiv PDFs.")
    p.add_argument("--topic", help="Only papers tagged with this topic")
    p.add_argument("--limit", type=int, help="Max papers to process")
    p.add_argument("--force", action="store_true", help="Re-download existing PDFs")
    p.add_argument("--include-oa", action="store_true",
                   help="Also fetch OA PDFs for DOI-only papers via Unpaywall")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
