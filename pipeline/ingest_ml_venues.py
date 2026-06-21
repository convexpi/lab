#!/usr/bin/env python3
"""
ingest_ml_venues.py — Ingest finance papers published at AI/ML conferences.

Complements three existing sources:
  - ingest_finance_papers.py     → recent arXiv q-fin preprints
  - seed_osap_papers.py          → the canonical anomaly-defining papers
  - ingest_openalex_journals.py  → published factor research from finance journals

The journal ingester captures finance/accounting venues, but a growing share of
quant-finance method work (deep learning, LLMs, reinforcement learning for
trading/hedging, NLP on filings) is published at AI/ML conferences instead. This
script discovers those papers by OpenAlex **venue (source id)** rather than by
journal ISSN, then applies the same finance-relevance gate + topic classifier so
only the finance-relevant subset is kept.

Pipeline per venue:
  1. Cursor-paginate OpenAlex works for the venue's source id since --since-year.
     For general ML venues a finance text `search=` pre-narrows the query so we
     don't scan thousands of irrelevant papers; ICAIF would be finance-native, so
     it would not need pre-narrowing (see VENUE_WHITELIST note below).
  2. Reconstruct the abstract from OpenAlex's inverted index.
  3. Keep only papers that pass the finance-relevance gate AND get >=1 topic from
     the classifier (both reused from ingest_finance_papers via work_to_paper).
  4. Upsert into Supabase `papers` (source='openalex', dedup by DOI).

All sources are free and open (OpenAlex polite pool; no key needed).

Usage:
    python pipeline/ingest_ml_venues.py --dry-run        # preview counts
    python pipeline/ingest_ml_venues.py                  # full ingest
    python pipeline/ingest_ml_venues.py --venue NeurIPS --since-year 2018
    python pipeline/ingest_ml_venues.py --per-venue-limit 200

Env vars:
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key
    CONTACT_EMAIL         OpenAlex polite pool (default below)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
import uuid
from pathlib import Path

import httpx

# Reuse the OpenAlex helpers, row builder, and Supabase client from the journal
# ingester (work_to_paper already applies the finance gate + topic classifier and
# sets is_preprint=False, which is correct for conference papers).
sys.path.insert(0, str(Path(__file__).parent))
from ingest_openalex_journals import (  # noqa: E402
    CONTACT_EMAIL, OPENALEX_API, SUPABASE_SERVICE_KEY, SUPABASE_URL, UA,
    _abstract_from_inverted, _headers, existing_dois, upsert_batch, work_to_paper,
)
from ingest_finance_papers import (  # noqa: E402
    is_finance_relevant, classify_topics, detect_oos_paper,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Whitelist of AI/ML conference venues (abbr → OpenAlex source id).
# Resolved via https://api.openalex.org/sources?search=<name> (confirmed by
# display_name + works_count). These are general ML venues: mostly non-finance,
# so a finance text `search=` pre-narrows the query and a STRICT strong-finance
# gate (see is_strongly_finance) removes residual false positives (e.g. RL papers
# that merely use words like "option"/"policy"/"reward").
VENUE_WHITELIST: dict[str, str] = {
    "NeurIPS": "S4306420609",   # Neural Information Processing Systems
    "ICML":    "S4306419644",   # International Conference on Machine Learning
    "ICLR":    "S4306419637",   # International Conference on Learning Representations
    "KDD":     "S4306420424",   # Knowledge Discovery and Data Mining (ACM SIGKDD)
    "EMNLP":   "S4306418267",   # Empirical Methods in Natural Language Processing
    "ACL":     "S4306420508",   # Meeting of the Association for Computational Linguistics
    "AAAI":    "S4210191458",   # Proceedings of the AAAI Conference on Artificial Intelligence
}

# DBLP-sourced venues (abbr → DBLP conference stream key). ICAIF (the ACM
# International Conference on AI in Finance) is the flagship AI-finance venue but
# is NOT indexed by OpenAlex as a distinct source, so it is pulled from DBLP
# instead (see fetch_dblp_papers) and enriched best-effort via OpenAlex by DOI.
DBLP_VENUES: dict[str, str] = {
    "ICAIF": "conf/icaif",      # ACM International Conference on AI in Finance
}

DBLP_API = "https://dblp.org/search/publ/api"

# Finance text query used to pre-narrow general ML venues (which are mostly
# non-finance). The strong-finance gate below does the final filtering.
FINANCE_SEARCH = (
    "finance OR stock OR trading OR portfolio OR market OR returns "
    "OR volatility OR credit OR option"
)
# Finance-native venues are EXEMPT from the strict strong-finance gate; they use
# only the normal is_finance_relevant gate (most of their papers are on-topic).
FINANCE_NATIVE_VENUES: set[str] = set(DBLP_VENUES)

# Unambiguous finance phrases. Used ONLY for general ML venues to drop papers
# that pass the loose is_finance_relevant gate on ambiguous words ("option",
# "trade", "value", "return", "policy", "reward", "market" alone) but are not
# actually about finance (e.g. "Option Discovery using Deep Skill Chaining", an
# RL paper). Bare ambiguous words are deliberately EXCLUDED here.
_STRONG_FINANCE_TERMS = [
    "stock", "equity", "equities", "portfolio",
    "asset pricing", "asset-pricing",
    "financial market", "stock market",
    "trading strateg", "limit order", "order book", "bid-ask",
    "market microstructure", "high-frequency trading",
    "implied volatility", "volatility forecast", "option pricing",
    "return predict", "cross-section of returns", "cross-sectional returns",
    "factor model", "credit risk", "credit scoring", "default prediction",
    "exchange rate", "cryptocurrency", "bitcoin",
    "value-at-risk", "sharpe ratio", "deep hedging",
    "optimal execution", "market making", "backtest",
    "risk premia", "risk premium",
]


def is_strongly_finance(title: str, abstract: str) -> bool:
    """True iff title/abstract contains an unambiguous finance phrase.

    Stricter than is_finance_relevant: used for general ML venues to filter out
    non-finance papers that only match ambiguous ML/RL vocabulary.
    """
    combined = ((title or "") + " " + (abstract or "")).lower()
    return any(term in combined for term in _STRONG_FINANCE_TERMS)


# ---------------------------------------------------------------------------
# OpenAlex helpers
# ---------------------------------------------------------------------------

def iter_venue_works(client: httpx.Client, source_id: str, since_year: int,
                     per_venue_limit: int | None, pre_narrow: bool):
    """Yield OpenAlex work dicts for a venue, newest first, via cursor paging.

    Mirrors ingest_openalex_journals.iter_journal_works, but filters by
    primary_location.source.id and (for general ML venues) adds a finance text
    `search=` so we don't scan thousands of irrelevant papers.
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
        if pre_narrow:
            params["search"] = FINANCE_SEARCH
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
            if per_venue_limit and yielded >= per_venue_limit:
                return
        cursor = data.get("meta", {}).get("next_cursor")


# ---------------------------------------------------------------------------
# DBLP helpers (for venues without an OpenAlex source, e.g. ICAIF)
# ---------------------------------------------------------------------------

def _dblp_authors(info: dict) -> list[dict]:
    """Normalize DBLP authors into [{"name": ...}].

    DBLP returns authors.author as a list of {text,...} objects, a single such
    object, or bare strings — handle all shapes.
    """
    raw = (info.get("authors") or {}).get("author")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raw = [raw]
    names: list[str] = []
    for a in raw:
        if isinstance(a, dict):
            name = a.get("text")
        else:
            name = a
        if name:
            names.append(str(name).strip())
    return [{"name": n} for n in names]


def enrich_from_openalex_doi(client: httpx.Client, doi: str) -> dict:
    """Best-effort fetch of abstract + citation_count from OpenAlex by DOI."""
    try:
        r = client.get(f"{OPENALEX_API}/doi:{doi}",
                       params={"mailto": CONTACT_EMAIL},
                       timeout=30, headers={"User-Agent": UA})
        r.raise_for_status()
        w = r.json()
    except httpx.HTTPError:
        return {}
    return {
        "abstract":       _abstract_from_inverted(w.get("abstract_inverted_index")),
        "citation_count": w.get("cited_by_count"),
    }


def iter_dblp_hits(client: httpx.Client, stream: str):
    """Yield DBLP `info` dicts for a conference stream.

    DBLP caps a single response at ~100 hits regardless of the requested `h`, so
    page with the `f` (first-result) offset until all hits are consumed.
    """
    first, page = 0, 100
    while True:
        params = {"q": f"stream:{stream}:", "format": "json",
                  "h": str(page), "f": str(first)}
        data = None
        for attempt in range(4):
            try:
                r = client.get(DBLP_API, params=params, timeout=60,
                               headers={"User-Agent": UA})
                if r.status_code == 429:
                    time.sleep(2.0 * (attempt + 1))  # DBLP throttles bursts
                    continue
                r.raise_for_status()
                data = r.json()
                break
            except httpx.HTTPError as exc:
                log.warning("  DBLP request failed: %s", exc)
                time.sleep(2.0 * (attempt + 1))
        if data is None:
            return
        hd = ((data.get("result") or {}).get("hits") or {})
        hits = hd.get("hit") or []
        if not hits:
            return
        for h in hits:
            info = h.get("info")
            if info:
                yield info
        sent = int(hd.get("@sent") or len(hits))
        total = int(hd.get("@total") or 0)
        first += sent
        if sent == 0 or first >= total:
            return
        time.sleep(1.5)  # be polite to DBLP (it throttles rapid paging)


def dblp_info_to_paper(info: dict, venue_abbr: str, enrich: dict) -> dict | None:
    """Build a paper row (same shape as work_to_paper) from a DBLP hit.

    Applies the normal is_finance_relevant / classify_topics gate; returns None
    if not finance-relevant or no topics. `enrich` carries optional OpenAlex
    abstract + citation_count.
    """
    title = (info.get("title") or "").strip()
    if not title:
        return None
    abstract = enrich.get("abstract")

    if not is_finance_relevant(title, abstract or ""):
        return None
    topics = classify_topics(title, abstract or "")
    if not topics:
        return None

    doi = (info.get("doi") or "").replace("https://doi.org/", "").lower() or None
    year = int(info["year"]) if str(info.get("year", "")).isdigit() else None
    return {
        "id":              str(uuid.uuid4()),
        "source":          "dblp",
        "source_id":       info.get("key") or doi,
        "doi":             doi,
        "arxiv_id":        None,
        "title":           title,
        "authors":         _dblp_authors(info),
        "year":            year,
        "journal":         "ICAIF",
        "abstract":        abstract,
        "open_access_url": None,
        "citation_count":  enrich.get("citation_count"),
        "topics":          topics,
        "factor_signals":  [],
        "is_preprint":     False,
        "is_open_access":  False,
        "is_oos_paper":    detect_oos_paper(title, abstract or ""),
        "quality_score":   0.6,
        "curation_status": "candidate",
    }


def iter_dblp_papers(client: httpx.Client, stream: str, venue_abbr: str,
                     since_year: int, per_venue_limit: int | None):
    """Yield finance-relevant paper rows for a DBLP-sourced venue.

    Filters by year, enriches each kept candidate via OpenAlex (best-effort,
    with a small polite delay), and dedups by DOI within the venue.
    """
    yielded = 0
    seen_dois: set[str] = set()
    for info in iter_dblp_hits(client, stream):
        year = int(info["year"]) if str(info.get("year", "")).isdigit() else None
        if year is not None and year < since_year:
            continue
        title = (info.get("title") or "").strip()
        if not title:
            continue
        doi = (info.get("doi") or "").replace("https://doi.org/", "").lower() or None
        if doi and doi in seen_dois:
            continue

        enrich: dict = {}
        if doi:
            enrich = enrich_from_openalex_doi(client, doi)
            time.sleep(0.2)  # be polite to OpenAlex

        paper = dblp_info_to_paper(info, venue_abbr, enrich)
        if not paper:
            continue
        if doi:
            seen_dois.add(doi)
        yield paper
        yielded += 1
        if per_venue_limit and yielded >= per_venue_limit:
            return


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> None:
    if not args.dry_run and (not SUPABASE_URL or not SUPABASE_SERVICE_KEY):
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    all_venues = {**VENUE_WHITELIST, **DBLP_VENUES}
    if args.venue and args.venue not in all_venues:
        log.error("Unknown venue %r. Valid: %s", args.venue, sorted(all_venues))
        sys.exit(1)
    venues = ({args.venue: all_venues[args.venue]}
              if args.venue else all_venues)

    import datetime
    recent_from_year = datetime.date.today().year - args.recent_years
    log.info("Citation floor: %d (papers since %d exempt)",
             args.min_citations, recent_from_year)

    grand_seen = grand_kept = grand_added = 0
    with httpx.Client() as client:
        seen_dois = set() if args.dry_run else existing_dois(client)
        if not args.dry_run:
            log.info("Loaded %d existing DOIs for dedup", len(seen_dois))

        for abbr, source_key in venues.items():
            is_dblp = abbr in DBLP_VENUES
            seen = kept = 0
            sample: list[str] = []
            batch: list[dict] = []

            if is_dblp:
                # DBLP-sourced (e.g. ICAIF): finance-native, normal gate only,
                # no strong-finance gate. iter_dblp_papers already applies the
                # gate + enrichment and returns finished paper rows.
                paper_iter = iter_dblp_papers(client, source_key, abbr,
                                              args.since_year, args.per_venue_limit)
            else:
                # General ML venue: OpenAlex works, normal gate (inside
                # work_to_paper) PLUS the strong-finance gate below.
                pre_narrow = abbr not in FINANCE_NATIVE_VENUES
                paper_iter = (
                    work_to_paper(w, abbr, args.min_citations, recent_from_year)
                    for w in iter_venue_works(client, source_key, args.since_year,
                                              args.per_venue_limit, pre_narrow)
                )

            for paper in paper_iter:
                seen += 1
                if not paper:
                    continue
                # Strict strong-finance gate for general ML venues only; ICAIF
                # (finance-native, DBLP) is exempt.
                if not is_dblp and not is_strongly_finance(
                        paper["title"], paper.get("abstract") or ""):
                    continue
                doi = paper["doi"]
                if doi and doi in seen_dois:
                    continue
                if doi:
                    seen_dois.add(doi)
                kept += 1
                if len(sample) < 5:
                    sample.append(f"{paper['year']}  {paper['title'][:80]}")
                if args.dry_run:
                    continue
                batch.append(paper)
                if len(batch) >= 50:
                    grand_added += upsert_batch(client, batch)
                    batch = []
            if batch:
                grand_added += upsert_batch(client, batch)
            log.info("%-8s seen=%4d kept=%4d", abbr, seen, kept)
            for s in sample:
                log.info("    + %s", s)
            grand_seen += seen
            grand_kept += kept

    log.info("Done. seen=%d kept(relevant+new)=%d added=%d",
             grand_seen, grand_kept, grand_added)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest finance papers from AI/ML conference venues (OpenAlex).")
    p.add_argument("--venue", help="Single venue abbreviation (e.g. NeurIPS)")
    p.add_argument("--since-year", type=int, default=2015, help="Earliest publication year (default 2015)")
    p.add_argument("--min-citations", type=int, default=20,
                   help="Citation floor; older papers below it are dropped (default 20)")
    p.add_argument("--recent-years", type=int, default=2,
                   help="Papers from the last N years are exempt from the citation floor (default 2)")
    p.add_argument("--per-venue-limit", type=int, help="Cap works scanned per venue")
    p.add_argument("--dry-run", action="store_true", help="Preview kept counts, write nothing")
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
