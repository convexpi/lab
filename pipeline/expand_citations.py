#!/usr/bin/env python3
"""
expand_citations.py — Grow the ConvexPi literature corpus by citation-graph
snowballing from high-quality seed papers, via the Semantic Scholar (S2)
Academic Graph API.

Complements the three breadth/recency sources:
  - ingest_finance_papers.py  → recent arXiv q-fin preprints
  - ingest_openalex_journals.py → published top-journal factor research
  - seed_osap_papers.py        → canonical anomaly-defining papers

This source works the *citation graph* instead of search/journal queries: from a
set of known-good seed papers it pulls each seed's references (what it builds on)
and citations (what builds on it), keeps the finance-relevant ones not already in
the DB, scores them by citation count + recency, and upserts the top candidates.

Pipeline per seed DOI:
  1. GET the S2 paper record with references.* and citations.* expanded.
  2. For each referenced / citing paper: require a DOI, apply the finance gate
     + topic classifier (both reused from ingest_finance_papers), dedup by DOI.
  3. Score = citation_count + recency bonus; keep top --per-seed-limit per seed.
  4. Across all seeds, keep the top --max-new and upsert into Supabase `papers`
     (source='semanticscholar', dedup by DOI).

Seeds:
  - A built-in list of ~10 canonical finance/ML DOIs (used in --dry-run, so the
    script runs with no DB and no Supabase env).
  - In real mode, additionally pull seed DOIs from Supabase `papers` where
    is_oos_paper=true OR quality_score>=0.7 (and a DOI is present).

Usage:
    python pipeline/expand_citations.py --dry-run --per-seed-limit 25   # preview
    python pipeline/expand_citations.py                                 # full run
    python pipeline/expand_citations.py --min-citations 10 --max-new 300

Env vars (required for DB writes only — NOT used in --dry-run):
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key

Optional:
    S2_API_KEY            Semantic Scholar API key (increases rate limits)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

# Reuse the relevance gate, topic classifier, and OOS detector.
sys.path.insert(0, str(Path(__file__).parent))
from ingest_finance_papers import (  # noqa: E402
    is_finance_relevant, classify_topics, detect_oos_paper,
)
# Reuse the Supabase REST helpers (headers / dedup / batched upsert).
from ingest_openalex_journals import (  # noqa: E402
    _headers, existing_dois, upsert_batch,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
S2_API_KEY           = os.environ.get("S2_API_KEY", "")

S2_API = "https://api.semanticscholar.org/graph/v1"

# Per-neighbour fields requested for references and citations.
_NEIGHBOUR_FIELDS = "title,year,abstract,externalIds,citationCount,authors"
S2_PAPER_FIELDS = (
    "title,year,abstract,authors,externalIds,citationCount,"
    + ",".join(f"references.{f}" for f in _NEIGHBOUR_FIELDS.split(","))
    + ","
    + ",".join(f"citations.{f}" for f in _NEIGHBOUR_FIELDS.split(","))
)

# Unauthenticated S2 allows ~1 req / few seconds; a key lifts this substantially.
SEED_DELAY = 3.0 if not S2_API_KEY else 0.5

# Canonical finance / ML-in-finance seed DOIs. Used directly in --dry-run, and
# unioned with DB-derived seeds in real mode. The graph call tolerates 404s, so
# any DOI S2 hasn't indexed is simply skipped with a warning.
SEED_DOIS: list[str] = [
    "10.1093/rfs/hhaa009",     # Gu, Kelly, Xiu — Empirical Asset Pricing via Machine Learning
    "10.1111/jofi.13238",      # Jensen, Kelly, Pedersen — Is There a Replication Crisis in Finance?
    "10.1093/rfs/hhw049",      # Harvey, Liu, Zhu — ...and the Cross-Section of Expected Returns
    "10.1111/jofi.12365",      # McLean, Pontiff — Does Academic Research Destroy Return Predictability?
    "10.1093/rfs/hhx019",      # Hou, Xue, Zhang — Replicating Anomalies
    "10.1257/jel.20191020",    # Harvey — replication / multiple testing in finance
    "10.1016/0304-405X(93)90023-5",  # Fama, French — Common risk factors (3-factor)
    "10.1016/j.jfineco.2014.10.010", # Fama, French — Five-factor asset pricing model
    "10.1145/3490354.3494366", # FinRL — deep RL framework for quantitative trading
    "10.1111/jofi.12852",      # Kelly, Pruitt, Su — Characteristics are covariances (IPCA)
    "10.1093/rfs/hhy032",      # Feng, Giglio, Xiu — Taming the Factor Zoo (ML factor selection)
]


# ---------------------------------------------------------------------------
# Semantic Scholar graph call
# ---------------------------------------------------------------------------

def fetch_paper_graph(client: httpx.Client, doi: str, max_retries: int = 4) -> dict | None:
    """Fetch an S2 paper record with references + citations expanded.

    Returns the parsed JSON dict, or None on 404 / persistent failure.
    Mirrors enrich_from_s2's 404 / 429 / backoff handling.
    """
    headers = {"x-api-key": S2_API_KEY} if S2_API_KEY else {}
    url = f"{S2_API}/paper/DOI:{doi}?fields={S2_PAPER_FIELDS}"
    for attempt in range(max_retries):
        try:
            resp = client.get(url, headers=headers, timeout=30)
            if resp.status_code == 404:
                log.warning("  S2 404 (not indexed): %s", doi)
                return None
            if resp.status_code == 429:
                wait = SEED_DELAY * (2 ** attempt)
                log.debug("  S2 rate limited, sleeping %.1fs", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            if attempt == max_retries - 1:
                log.warning("  S2 request failed for %s: %s", doi, exc)
                return None
            time.sleep(SEED_DELAY * (2 ** attempt))
    return None


# ---------------------------------------------------------------------------
# Candidate selection + row build
# ---------------------------------------------------------------------------

def _score(citation_count: int, year: int | None) -> float:
    """Rank candidates by citations with a mild recency bonus.

    Newer papers haven't had time to accrue citations, so add a bounded bonus
    for recent work to avoid an all-classics bias.
    """
    import datetime
    base = float(citation_count or 0)
    if year:
        age = max(datetime.date.today().year - year, 0)
        base += max(0, 30 - 3 * age)  # up to +30 for current-year work
    return base


def neighbour_to_paper(n: dict, min_citations: int) -> dict | None:
    """Turn an S2 reference/citation neighbour into a `papers` row, or None.

    Drops anything without a DOI, below the citation floor, failing the finance
    gate, or yielding no topic. Shape mirrors work_to_paper's output.
    """
    title = n.get("title")
    if not title:
        return None
    doi = (n.get("externalIds") or {}).get("DOI")
    if not doi:
        return None
    doi = doi.lower()

    abstract = n.get("abstract") or ""
    cites = n.get("citationCount") or 0
    year = n.get("year")
    if cites < min_citations:
        return None

    if not is_finance_relevant(title, abstract):
        return None
    topics = classify_topics(title, abstract)
    if not topics:
        return None

    authors = [
        {"name": a.get("name", "")}
        for a in (n.get("authors") or [])
        if a.get("name")
    ]
    return {
        "id":              str(uuid.uuid4()),
        "source":          "semanticscholar",
        "source_id":       n.get("paperId") or doi,
        "doi":             doi,
        "arxiv_id":        (n.get("externalIds") or {}).get("ArXiv"),
        "title":           title,
        "authors":         authors,
        "year":            year,
        "journal":         None,
        "abstract":        abstract or None,
        "open_access_url": None,
        "citation_count":  cites,
        "topics":          topics,
        "factor_signals":  [],
        "is_preprint":     False,
        "is_open_access":  False,   # unknown from neighbour fields
        "is_oos_paper":    detect_oos_paper(title, abstract),
        "quality_score":   0.5,
        "curation_status": "candidate",
        "_score":          _score(cites, year),
    }


# ---------------------------------------------------------------------------
# Seed sourcing
# ---------------------------------------------------------------------------

def seeds_from_supabase(client: httpx.Client) -> list[str]:
    """Pull high-quality seed DOIs from Supabase (real mode only)."""
    dois: list[str] = []
    r = client.get(
        f"{SUPABASE_URL}/rest/v1/papers",
        params={
            "select": "doi",
            "doi": "not.is.null",
            "or": "(is_oos_paper.eq.true,quality_score.gte.0.7)",
            "limit": "1000",
        },
        headers=_headers(), timeout=30,
    )
    if r.status_code == 200:
        dois = [(row["doi"] or "").lower() for row in r.json() if row.get("doi")]
    else:
        log.warning("Could not load DB seeds (%d): %s", r.status_code, r.text[:160])
    return dois


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> None:
    if not args.dry_run and (not SUPABASE_URL or not SUPABASE_SERVICE_KEY):
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set (or use --dry-run).")
        sys.exit(1)

    with httpx.Client() as client:
        # ---- Assemble seeds -------------------------------------------------
        seeds = list(dict.fromkeys(d.lower() for d in SEED_DOIS))  # dedup, keep order
        seen_dois: set[str] = set()
        if not args.dry_run:
            seen_dois = existing_dois(client)
            log.info("Loaded %d existing DOIs for dedup", len(seen_dois))
            db_seeds = seeds_from_supabase(client)
            log.info("Loaded %d seed DOIs from Supabase", len(db_seeds))
            for d in db_seeds:
                if d not in seeds:
                    seeds.append(d)
        log.info("Snowballing from %d seed papers (delay %.1fs/seed)", len(seeds), SEED_DELAY)

        # Seed DOIs themselves are not candidates.
        seen_dois.update(seeds)

        # ---- Walk the citation graph ---------------------------------------
        candidates: dict[str, dict] = {}   # doi -> row (best-scoring kept)
        failed: list[str] = []
        total_neighbours = 0

        for i, doi in enumerate(seeds, 1):
            data = fetch_paper_graph(client, doi)
            if data is None:
                failed.append(doi)
                time.sleep(SEED_DELAY)
                continue

            refs = data.get("references") or []
            cits = data.get("citations") or []
            neighbours = refs + cits
            total_neighbours += len(neighbours)
            log.info("[%d/%d] %s — %r: %d refs + %d cites",
                     i, len(seeds), doi, (data.get("title") or "")[:60],
                     len(refs), len(cits))

            kept: list[dict] = []
            for n in neighbours:
                paper = neighbour_to_paper(n, args.min_citations)
                if not paper:
                    continue
                d = paper["doi"]
                if d in seen_dois:
                    continue
                # Within a seed, keep the higher-scoring duplicate.
                prev = candidates.get(d)
                if prev is None or paper["_score"] > prev["_score"]:
                    candidates[d] = paper
                kept.append(paper)

            # Per-seed cap: only the top-scoring NEW neighbours from this seed
            # are promoted into seen_dois (so weaker dupes can still appear via
            # a different, stronger seed before the global cut).
            kept.sort(key=lambda p: p["_score"], reverse=True)
            for paper in kept[: args.per_seed_limit]:
                seen_dois.add(paper["doi"])
            log.info("    → %d relevant new candidates (capped at %d)",
                     min(len(kept), args.per_seed_limit), args.per_seed_limit)

            time.sleep(SEED_DELAY)

        # ---- Global ranking + cap ------------------------------------------
        ranked = sorted(candidates.values(), key=lambda p: p["_score"], reverse=True)
        if args.max_new:
            ranked = ranked[: args.max_new]

        log.info("=" * 60)
        log.info("Discovered %d relevant new candidate papers (from %d neighbours)",
                 len(ranked), total_neighbours)
        if failed:
            log.info("Seed DOIs that failed to resolve on S2 (%d): %s",
                     len(failed), ", ".join(failed))

        # ---- Sample / upsert ------------------------------------------------
        sample = ranked[: min(20, len(ranked))]
        log.info("Top %d candidates:", len(sample))
        for p in sample:
            log.info("  [%6.0f] (%s) %-70s cites=%-5s topics=%s",
                     p["_score"], p.get("year"), p["title"][:70],
                     p.get("citation_count"), p["topics"])

        if args.dry_run:
            log.info("[DRY RUN] No Supabase writes. %d candidates would be upserted.",
                     len(ranked))
            return

        # Strip internal scoring field before write.
        rows = [{k: v for k, v in p.items() if k != "_score"} for p in ranked]
        added = 0
        for j in range(0, len(rows), 50):
            added += upsert_batch(client, rows[j : j + 50])
        log.info("Done. Upserted %d new papers.", added)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Grow the literature corpus by citation-graph snowballing (Semantic Scholar).")
    p.add_argument("--per-seed-limit", type=int, default=40,
                   help="Max new candidates kept per seed paper (default 40)")
    p.add_argument("--min-citations", type=int, default=5,
                   help="Citation floor for a neighbour to be kept (default 5)")
    p.add_argument("--max-new", type=int,
                   help="Overall cap on new candidates upserted (default: no cap)")
    p.add_argument("--dry-run", action="store_true",
                   help="Use built-in seeds, write nothing, touch no Supabase env")
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
