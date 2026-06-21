#!/usr/bin/env python3
"""
ingest_openalex_journals.py — Ingest finance-journal papers from OpenAlex.

Complements two existing sources:
  - ingest_finance_papers.py  → recent arXiv q-fin preprints
  - seed_osap_papers.py       → the canonical anomaly-defining papers

This pulls the *breadth* of published factor / asset-pricing research from a
whitelist of top finance and accounting journals (by ISSN), filtered to papers
that are actually about cross-sectional return predictability — so it skips the
ESG / corporate-governance / banking papers those journals also publish.

Pipeline per journal:
  1. Cursor-paginate OpenAlex works for the journal's ISSN since --since-year.
  2. Reconstruct the abstract from OpenAlex's inverted index.
  3. Keep only papers that pass the finance-relevance gate AND get >=1 factor
     topic from the classifier (both reused from ingest_finance_papers).
  4. Upsert into Supabase `papers` (source='openalex', dedup by DOI).

All sources are free and open (OpenAlex polite pool; no key needed).

Usage:
    python pipeline/ingest_openalex_journals.py --dry-run        # preview counts
    python pipeline/ingest_openalex_journals.py                  # full ingest
    python pipeline/ingest_openalex_journals.py --journal JF --since-year 2010
    python pipeline/ingest_openalex_journals.py --per-journal-limit 200

Env vars:
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key
    CONTACT_EMAIL         OpenAlex polite pool (default below)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from pathlib import Path

import httpx

# Reuse the relevance gate, topic classifier, and OOS detector.
sys.path.insert(0, str(Path(__file__).parent))
from ingest_finance_papers import (  # noqa: E402
    is_finance_relevant, classify_topics, detect_oos_paper,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
CONTACT_EMAIL        = os.environ.get("CONTACT_EMAIL", "shane.conway@gmail.com")

OPENALEX_API = "https://api.openalex.org/works"
UA = f"ConvexPi-Lab/1.0 (https://convexpi.ai; mailto:{CONTACT_EMAIL})"

# Whitelist of finance + asset-pricing-relevant accounting journals (abbr → ISSN).
JOURNAL_WHITELIST: dict[str, str] = {
    "JF":      "0022-1082",   # Journal of Finance
    "JFE":     "0304-405X",   # Journal of Financial Economics
    "RFS":     "0893-9454",   # Review of Financial Studies
    "JFQA":    "0022-1090",   # Journal of Financial and Quantitative Analysis
    "ROF":     "1572-3097",   # Review of Finance
    "JFM":     "1386-4181",   # Journal of Financial Markets
    "JEmpFin": "0927-5398",   # Journal of Empirical Finance
    "FAJ":     "0015-198X",   # Financial Analysts Journal
    "JPM":     "0095-4918",   # Journal of Portfolio Management
    "AR":      "0001-4826",   # The Accounting Review
    "JAE":     "0165-4101",   # Journal of Accounting and Economics
    "JAR":     "0021-8456",   # Journal of Accounting Research
    "RAS":     "1380-6653",   # Review of Accounting Studies
    "RAPS":    "2045-9920",   # Review of Asset Pricing Studies
    "RCFS":    "2046-9128",   # Review of Corporate Finance Studies
    "JBF":     "0378-4266",   # Journal of Banking & Finance
    "QF":      "1469-7688",   # Quantitative Finance
    "JFDS":    "2640-3943",   # Journal of Financial Data Science
    # Broad econ journals — the relevance gate keeps only asset-pricing/finance papers.
    "AER":     "0002-8282",   # American Economic Review
    "JPE":     "0022-3808",   # Journal of Political Economy
    "QJE":     "0033-5533",   # Quarterly Journal of Economics
    "ECMA":    "0012-9682",   # Econometrica
    "REStud":  "0034-6527",   # Review of Economic Studies
}


# ---------------------------------------------------------------------------
# OpenAlex helpers
# ---------------------------------------------------------------------------

def _abstract_from_inverted(inv: dict | None) -> str | None:
    if not inv:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions) or None


def iter_journal_works(client: httpx.Client, issn: str, since_year: int,
                       per_journal_limit: int | None):
    """Yield OpenAlex work dicts for a journal, newest first, via cursor paging."""
    cursor = "*"
    yielded = 0
    while cursor:
        params = {
            "filter": f"primary_location.source.issn:{issn},"
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
            if per_journal_limit and yielded >= per_journal_limit:
                return
        cursor = data.get("meta", {}).get("next_cursor")


def work_to_paper(w: dict, journal_abbr: str,
                  min_citations: int, recent_from_year: int) -> dict | None:
    title = w.get("display_name") or w.get("title")
    if not title:
        return None
    abstract = _abstract_from_inverted(w.get("abstract_inverted_index"))

    # Relevance + topic gate — keep only cross-sectional / factor research.
    if not is_finance_relevant(title, abstract or ""):
        return None
    topics = classify_topics(title, abstract or "")
    if not topics:
        return None

    # Citation floor, with a recency exemption: recent papers haven't had time
    # to accrue citations, so keep them regardless of count.
    cites = w.get("cited_by_count") or 0
    year = w.get("publication_year") or 0
    if cites < min_citations and year < recent_from_year:
        return None

    src = (w.get("primary_location") or {}).get("source") or {}
    oa = w.get("open_access") or {}
    best = w.get("best_oa_location") or {}
    doi = (w.get("doi") or "").replace("https://doi.org/", "").lower() or None
    authors = [
        {"name": (a.get("author") or {}).get("display_name", "")}
        for a in w.get("authorships", [])
        if (a.get("author") or {}).get("display_name")
    ]
    return {
        "id":              str(uuid.uuid4()),
        "source":          "openalex",
        "source_id":       (w.get("id") or "").rsplit("/", 1)[-1],
        "doi":             doi,
        "arxiv_id":        None,
        "title":           title,
        "authors":         authors,
        "year":            w.get("publication_year"),
        "journal":         src.get("display_name") or journal_abbr,
        "abstract":        abstract,
        "open_access_url": oa.get("oa_url") or best.get("pdf_url"),
        "citation_count":  w.get("cited_by_count"),
        "topics":          topics,
        "factor_signals":  [],
        "is_preprint":     False,
        "is_open_access":  bool(oa.get("is_oa")),
        "is_oos_paper":    detect_oos_paper(title, abstract or ""),
        "quality_score":   0.6,
        "curation_status": "candidate",
    }


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def _headers(extra: dict | None = None) -> dict:
    h = {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
    }
    if extra:
        h.update(extra)
    return h


def existing_dois(client: httpx.Client) -> set[str]:
    """Pre-fetch all existing DOIs to skip duplicates cheaply."""
    dois: set[str] = set()
    offset = 0
    while True:
        r = client.get(f"{SUPABASE_URL}/rest/v1/papers",
                       params={"select": "doi", "doi": "not.is.null",
                               "limit": "1000", "offset": str(offset)},
                       headers=_headers(), timeout=30)
        batch = r.json() if r.status_code == 200 else []
        if not batch:
            break
        dois.update((row["doi"] or "").lower() for row in batch)
        offset += len(batch)
        if len(batch) < 1000:
            break
    return dois


def upsert_batch(client: httpx.Client, rows: list[dict]) -> int:
    if not rows:
        return 0
    r = client.post(f"{SUPABASE_URL}/rest/v1/papers", json=rows,
                    headers=_headers({"Prefer": "resolution=ignore-duplicates,return=minimal"}),
                    timeout=60)
    if r.status_code not in (200, 201):
        log.warning("  upsert failed %d: %s", r.status_code, r.text[:160])
        return 0
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> None:
    if not args.dry_run and (not SUPABASE_URL or not SUPABASE_SERVICE_KEY):
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    journals = ({args.journal: JOURNAL_WHITELIST[args.journal]}
                if args.journal else JOURNAL_WHITELIST)
    if args.journal and args.journal not in JOURNAL_WHITELIST:
        log.error("Unknown journal %r. Valid: %s", args.journal, sorted(JOURNAL_WHITELIST))
        sys.exit(1)

    import datetime
    recent_from_year = datetime.date.today().year - args.recent_years
    log.info("Citation floor: %d (papers since %d exempt)",
             args.min_citations, recent_from_year)

    grand_seen = grand_kept = grand_added = 0
    with httpx.Client() as client:
        seen_dois = set() if args.dry_run else existing_dois(client)
        if not args.dry_run:
            log.info("Loaded %d existing DOIs for dedup", len(seen_dois))

        for abbr, issn in journals.items():
            seen = kept = 0
            batch: list[dict] = []
            for w in iter_journal_works(client, issn, args.since_year, args.per_journal_limit):
                seen += 1
                paper = work_to_paper(w, abbr, args.min_citations, recent_from_year)
                if not paper:
                    continue
                doi = paper["doi"]
                if doi and doi in seen_dois:
                    continue
                if doi:
                    seen_dois.add(doi)
                kept += 1
                if args.dry_run:
                    continue
                batch.append(paper)
                if len(batch) >= 50:
                    grand_added += upsert_batch(client, batch)
                    batch = []
            if batch:
                grand_added += upsert_batch(client, batch)
            log.info("%-8s seen=%4d kept=%4d", abbr, seen, kept)
            grand_seen += seen
            grand_kept += kept

    log.info("Done. seen=%d kept(relevant+new)=%d added=%d",
             grand_seen, grand_kept, grand_added)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest finance-journal papers from OpenAlex.")
    p.add_argument("--journal", help="Single journal abbreviation (e.g. JF)")
    p.add_argument("--since-year", type=int, default=2000, help="Earliest publication year (default 2000)")
    p.add_argument("--min-citations", type=int, default=20,
                   help="Citation floor; older papers below it are dropped (default 20)")
    p.add_argument("--recent-years", type=int, default=2,
                   help="Papers from the last N years are exempt from the citation floor (default 2)")
    p.add_argument("--per-journal-limit", type=int, help="Cap works scanned per journal")
    p.add_argument("--dry-run", action="store_true", help="Preview kept counts, write nothing")
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
