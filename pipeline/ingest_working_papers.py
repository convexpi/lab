#!/usr/bin/env python3
"""
ingest_working_papers.py — Ingest finance working papers from OpenAlex.

Complements the journal / arXiv / OSAP paths with the *pre-publication* layer:
working-paper series from NBER, the Federal Reserve, and (where resolvable in
OpenAlex) other central banks. These are the ideas that show up in seminars and
SSRN years before — or instead of — a journal version, so the published-journal
and arXiv crawlers miss them.

Pipeline per source (mirrors ingest_openalex_journals.py):
  1. Cursor-paginate OpenAlex works whose primary location is the source id,
     since --since-year, type=article.
  2. Reconstruct the abstract from OpenAlex's inverted index.
  3. Keep only papers that pass the finance-relevance gate AND get >=1 topic
     from the classifier (both reused from ingest_finance_papers).
  4. Build a row via work_to_paper, force is_preprint=True (working papers),
     and upsert into Supabase `papers` (source='openalex', dedup by DOI).

All sources are free and open (OpenAlex polite pool; no key needed).

Usage:
    python pipeline/ingest_working_papers.py --dry-run
    python pipeline/ingest_working_papers.py --source NBER --since-year 2015
    python pipeline/ingest_working_papers.py --per-source-limit 500

Env vars:
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key
    CONTACT_EMAIL         OpenAlex polite pool (default below)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import httpx

# Reuse the OpenAlex + Supabase plumbing from the journal ingester, and the
# relevance/topic/OOS gates from the arXiv ingester. Everything below is just
# a different OpenAlex *filter* (source id instead of ISSN) over the same path.
sys.path.insert(0, str(Path(__file__).parent))
from ingest_openalex_journals import (  # noqa: E402
    CONTACT_EMAIL, OPENALEX_API, UA,
    work_to_paper, existing_dois, upsert_batch,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Whitelist of finance-relevant working-paper series (abbr → OpenAlex source id).
# Resolved via https://api.openalex.org/sources?search=<name> (display_name +
# works_count confirmed). Counts noted as of resolution; they only grow.
#
#   NBER  S2809516038  36,351 works  National Bureau of Economic Research
#   FEDS  S4210212089   2,486 works  Finance and Economics Discussion Series (Fed Board)
#   IFDP  S4210204989   1,474 works  International Finance Discussion Paper (Fed Board)
#
# Could NOT resolve a dedicated working-paper source in OpenAlex (skipped):
#   - BIS Working Papers       (only BIS eBook collections exist as sources)
#   - ECB Working Paper Series  (no OpenAlex source; ECB WPs are indexed only
#                                as bare works, not grouped under a source)
#   - CEPR Discussion Papers    (only CEPR eBook collections exist as sources)
# Their papers still arrive via the journal/arXiv paths once published; add them
# here if/when OpenAlex grows a proper source id for the series.
SOURCE_WHITELIST: dict[str, str] = {
    "NBER": "S2809516038",   # National Bureau of Economic Research
    "FEDS": "S4210212089",   # Finance and Economics Discussion Series (Fed)
    "IFDP": "S4210204989",   # International Finance Discussion Paper (Fed)
}


# ---------------------------------------------------------------------------
# OpenAlex helpers
# ---------------------------------------------------------------------------

def iter_source_works(client: httpx.Client, source_id: str, since_year: int,
                      per_source_limit: int | None):
    """Yield OpenAlex work dicts for a working-paper source, newest first.

    We filter on primary_location.source.id (not the broader locations.source.id)
    so each work is attributed to the series it was actually published in — this
    keeps journal-republished copies from double-counting and gives a clean DOI
    for dedup. Both filter forms return NBER results; primary_location is the
    tighter one.
    """
    cursor = "*"
    yielded = 0
    while cursor:
        params = {
            "filter": f"primary_location.source.id:{source_id},"
                      f"from_publication_date:{since_year}-01-01,type:article",
            "per-page": "200",
            "cursor": cursor,
            "sort": "publication_date:desc",
            "mailto": CONTACT_EMAIL,
        }
        try:
            r = client.get(OPENALEX_API, params=params, timeout=60, headers={"User-Agent": UA})
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as exc:
            log.warning("  OpenAlex page failed: %s", exc)
            return
        for w in data.get("results", []):
            yield w
            yielded += 1
            if per_source_limit and yielded >= per_source_limit:
                return
        cursor = data.get("meta", {}).get("next_cursor")


# ---------------------------------------------------------------------------
# Optional secondary path: RePEc/NEP curated lists → Crossref DOI resolution
# ---------------------------------------------------------------------------
#
# STUB — NOT WIRED INTO run(). The NEP (New Economics Papers) reports are
# curated topic lists (e.g. NEP-FMK financial markets, NEP-RMG risk management)
# whose archive pages list paper titles + RePEc handles. Resolving those to DOIs
# via Crossref is fiddly (title-match false positives, RePEc handle parsing,
# Crossref rate limits) and the OpenAlex working-paper sources already cover the
# main deliverable, so this is left as a documented stub.
#
# Sketch of the intended implementation:
#   1. Fetch the report archive page, e.g.
#        https://nep.repec.org/2024/  →  per-issue pages list titles + handles.
#      (No clean JSON API; the pages are plain HTML lists.)
#   2. Parse out paper titles.
#   3. For each title, resolve a DOI via Crossref:
#        https://api.crossref.org/works?query.bibliographic=<title>&rows=1
#      and accept only high-similarity matches.
#   4. Gate with is_finance_relevant / classify_topics, build a row like
#      work_to_paper does, set is_preprint=True, dedup by DOI, upsert.

def ingest_nep_report(report_id: str) -> list[dict]:
    """Resolve one RePEc/NEP curated list to gated paper rows. STUB.

    Args:
        report_id: NEP report code, e.g. "nep-fmk" (financial markets) or
                   "nep-rmg" (risk management).

    Returns:
        list of paper rows ready for upsert. Currently always [] — see the
        module comment above for the intended Crossref-resolution design.
    """
    log.warning("ingest_nep_report(%r) is a stub; no papers ingested. "
                "See module comment for the intended RePEc/Crossref design.", report_id)
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> None:
    from ingest_openalex_journals import SUPABASE_URL, SUPABASE_SERVICE_KEY
    if not args.dry_run and (not SUPABASE_URL or not SUPABASE_SERVICE_KEY):
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    if args.source and args.source not in SOURCE_WHITELIST:
        log.error("Unknown source %r. Valid: %s", args.source, sorted(SOURCE_WHITELIST))
        sys.exit(1)
    sources = ({args.source: SOURCE_WHITELIST[args.source]}
               if args.source else SOURCE_WHITELIST)

    import datetime
    recent_from_year = datetime.date.today().year - args.recent_years
    log.info("Working papers since %d. Citation floor: %d (papers since %d exempt)",
             args.since_year, args.min_citations, recent_from_year)

    grand_seen = grand_kept = grand_added = 0
    with httpx.Client() as client:
        seen_dois = set() if args.dry_run else existing_dois(client)
        if not args.dry_run:
            log.info("Loaded %d existing DOIs for dedup", len(seen_dois))

        for abbr, source_id in sources.items():
            seen = kept = 0
            batch: list[dict] = []
            samples: list[str] = []
            for w in iter_source_works(client, source_id, args.since_year, args.per_source_limit):
                seen += 1
                paper = work_to_paper(w, abbr, args.min_citations, recent_from_year)
                if not paper:
                    continue
                paper["is_preprint"] = True  # these are working papers
                doi = paper["doi"]
                if doi and doi in seen_dois:
                    continue
                if doi:
                    seen_dois.add(doi)
                kept += 1
                if len(samples) < 5:
                    samples.append(paper["title"])
                if args.dry_run:
                    continue
                batch.append(paper)
                if len(batch) >= 50:
                    grand_added += upsert_batch(client, batch)
                    batch = []
            if batch:
                grand_added += upsert_batch(client, batch)
            log.info("%-6s seen=%5d kept=%5d", abbr, seen, kept)
            for t in samples:
                log.info("    · %s", t[:90])
            grand_seen += seen
            grand_kept += kept

    log.info("Done. seen=%d kept(relevant+new)=%d added=%d",
             grand_seen, grand_kept, grand_added)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest finance working papers from OpenAlex.")
    p.add_argument("--source", help="Single source abbreviation (e.g. NBER)")
    p.add_argument("--since-year", type=int, default=2015, help="Earliest publication year (default 2015)")
    p.add_argument("--min-citations", type=int, default=0,
                   help="Citation floor; working papers have few cites (default 0)")
    p.add_argument("--recent-years", type=int, default=2,
                   help="Papers from the last N years are exempt from the citation floor (default 2)")
    p.add_argument("--per-source-limit", type=int, help="Cap works scanned per source")
    p.add_argument("--dry-run", action="store_true", help="Preview kept counts, write nothing")
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
