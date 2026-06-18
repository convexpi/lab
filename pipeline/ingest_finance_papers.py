#!/usr/bin/env python3
"""
ingest_finance_papers.py — Ingest arXiv q-fin papers into the ConvexPi literature DB.

Fetches papers from arXiv by category + keyword query, enriches metadata via
Semantic Scholar, and upserts into the Supabase `papers` table.

Adapted from the DoOperator pipeline (causal/scripts/ingest_arxiv_categories.py).
Key changes: q-fin topic taxonomy, Supabase REST client instead of asyncpg.

Usage:
    python pipeline/ingest_finance_papers.py
    python pipeline/ingest_finance_papers.py --topic momentum
    python pipeline/ingest_finance_papers.py --topic factor_zoo --limit 500
    python pipeline/ingest_finance_papers.py --arxiv-id 2309.12345
    python pipeline/ingest_finance_papers.py --dry-run

Env vars (required for DB writes):
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key (bypasses RLS)

Optional:
    S2_API_KEY            Semantic Scholar API key (increases rate limits)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
S2_API_KEY = os.environ.get("S2_API_KEY", "")

ARXIV_API = "https://export.arxiv.org/api/query"
S2_API = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,authors,year,externalIds,publicationVenue,citationCount,abstract,isOpenAccess,openAccessPdf"

NS = "http://www.w3.org/2005/Atom"

# ---------------------------------------------------------------------------
# Topic taxonomy — q-fin equivalent of the dooperator stat.ME / cs.LG taxonomy
# ---------------------------------------------------------------------------

TOPIC_QUERIES: dict[str, list[tuple[str, list[str]]]] = {
    "momentum": [
        ("cat:q-fin.PM AND all:momentum equity cross-sectional", ["momentum"]),
        ("cat:q-fin.ST AND ti:momentum return predictability", ["momentum"]),
        ("cat:q-fin.PM AND all:trend following time-series momentum", ["momentum"]),
    ],
    "value": [
        ("cat:q-fin.PM AND all:value factor book-to-market equity", ["value"]),
        ("cat:q-fin.PM AND all:value premium growth stock", ["value"]),
    ],
    "quality": [
        ("cat:q-fin.PM AND all:quality factor profitability return", ["quality"]),
        ("cat:q-fin.PM AND all:gross profitability operating accruals", ["quality"]),
        ("cat:q-fin.PM AND all:investment asset growth anomaly", ["quality", "investment"]),
    ],
    "low_volatility": [
        ("cat:q-fin.PM AND all:low volatility anomaly beta", ["low_volatility", "risk"]),
        ("cat:q-fin.PM AND all:idiosyncratic volatility expected return", ["low_volatility"]),
    ],
    "short_term_reversal": [
        ("cat:q-fin.ST AND all:short-term reversal microstructure", ["reversal"]),
        ("cat:q-fin.ST AND all:price reversal bid-ask bounce", ["reversal"]),
    ],
    "size": [
        ("cat:q-fin.PM AND all:size effect small cap equity premium", ["size"]),
    ],
    "factor_zoo": [
        ("cat:econ.GN AND all:factor zoo multiple testing p-hacking", ["meta"]),
        ("cat:econ.GN AND all:anomaly replication out-of-sample decay", ["meta"]),
        ("cat:q-fin.PM AND all:cross-sectional return predictability replication", ["meta"]),
        ("cat:econ.GN AND all:data mining spurious factor alpha", ["meta"]),
        ("cat:econ.GN AND all:McLean Pontiff publication anomaly decay", ["meta"]),
    ],
    "market_microstructure": [
        ("cat:q-fin.TR AND all:limit order book market maker", ["microstructure"]),
        ("cat:q-fin.TR AND all:adverse selection inventory risk spread", ["microstructure"]),
        ("cat:q-fin.TR AND all:high frequency trading execution", ["microstructure"]),
    ],
    "machine_learning_finance": [
        ("cat:q-fin.PM AND all:machine learning stock return prediction", ["ml_finance"]),
        ("cat:q-fin.PM AND all:neural network equity return factor", ["ml_finance"]),
        ("cat:q-fin.ST AND all:deep learning financial forecasting", ["ml_finance"]),
    ],
    "options": [
        ("cat:q-fin.PR AND all:option pricing anomaly volatility risk premium", ["options"]),
        ("cat:q-fin.PM AND all:option implied information equity return", ["options"]),
    ],
}

# ---------------------------------------------------------------------------
# Keyword classifier — topics inferred from title + abstract text
# ---------------------------------------------------------------------------

_KEYWORD_MAP: list[tuple[list[str], list[str]]] = [
    (["momentum", "winner", "loser", "trend following"],             ["momentum"]),
    (["value", "book-to-market", "book to market", "HML"],           ["value"]),
    (["profitab", "quality", "gross profit", "accrual", "RMW"],      ["quality"]),
    (["size", "small cap", "SMB", "market cap"],                     ["size"]),
    (["volatil", "beta", "low-risk", "low risk", "BAB"],             ["low_volatility"]),
    (["reversal", "short-term", "microstructure"],                   ["reversal"]),
    (["factor zoo", "p-hack", "multiple testing", "data mine",
      "publication bias", "replication", "out-of-sample"],           ["meta"]),
    (["limit order", "market mak", "bid-ask", "adverse select",
      "inventory", "high frequency", "HFT"],                        ["microstructure"]),
    (["machine learn", "neural net", "deep learn", "random forest",
      "gradient boost", "XGBoost", "LSTM"],                         ["ml_finance"]),
    (["option", "volatility surface", "VIX", "implied vol"],         ["options"]),
]


def classify_topics(title: str, abstract: str) -> list[str]:
    combined = (title + " " + abstract).lower()
    tags: set[str] = set()
    for keywords, topic_tags in _KEYWORD_MAP:
        if any(kw.lower() in combined for kw in keywords):
            tags.update(topic_tags)
    return sorted(tags)


# ---------------------------------------------------------------------------
# Detect whether a paper presents OOS / post-publication evidence
# ---------------------------------------------------------------------------

_OOS_PHRASES = [
    "out-of-sample", "out of sample", "post-publication",
    "post publication", "holdout", "live trading",
    "forward test", "real-time", "replication failure",
    "anomaly decay", "publication effect",
]


def detect_oos_paper(title: str, abstract: str) -> bool:
    combined = (title + " " + abstract).lower()
    return any(phrase in combined for phrase in _OOS_PHRASES)


# ---------------------------------------------------------------------------
# arXiv API helpers
# ---------------------------------------------------------------------------

async def fetch_arxiv_papers(
    client: httpx.AsyncClient,
    search_query: str,
    limit: int = 200,
) -> list[dict]:
    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": limit,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    try:
        resp = await client.get(ARXIV_API, params=params, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("arXiv request failed: %s", exc)
        return []

    root = ET.fromstring(resp.text)
    papers = []
    for entry in root.findall(f"{{{NS}}}entry"):
        def t(tag: str) -> str:
            el = entry.find(f"{{{NS}}}{tag}")
            return el.text.strip() if el is not None and el.text else ""

        raw_id = t("id")  # e.g. http://arxiv.org/abs/2309.12345v1
        arxiv_id = re.sub(r"v\d+$", "", raw_id.split("/abs/")[-1])

        authors = [
            a.find(f"{{{NS}}}name").text.strip()
            for a in entry.findall(f"{{{NS}}}author")
            if a.find(f"{{{NS}}}name") is not None
        ]

        papers.append({
            "source":     "arxiv",
            "source_id":  arxiv_id,
            "arxiv_id":   arxiv_id,
            "title":      t("title").replace("\n", " ").strip(),
            "abstract":   t("summary").replace("\n", " ").strip(),
            "authors":    [{"name": a} for a in authors],
            "year":       int(t("published")[:4]) if t("published") else None,
            "arxiv_url":  f"https://arxiv.org/abs/{arxiv_id}",
            "topics":     [],  # filled by caller
        })
    return papers


async def fetch_arxiv_by_id(client: httpx.AsyncClient, arxiv_id: str) -> dict | None:
    papers = await fetch_arxiv_papers(client, f"id:{arxiv_id}", limit=1)
    return papers[0] if papers else None


# ---------------------------------------------------------------------------
# Semantic Scholar enrichment (DOI, citation count, OA URL)
# ---------------------------------------------------------------------------

async def enrich_from_s2(
    client: httpx.AsyncClient,
    arxiv_id: str,
) -> dict:
    headers = {"x-api-key": S2_API_KEY} if S2_API_KEY else {}
    url = f"{S2_API}/paper/arXiv:{arxiv_id}?fields={S2_FIELDS}"
    try:
        resp = await client.get(url, headers=headers, timeout=20)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        data = resp.json()
        oa_pdf = (data.get("openAccessPdf") or {}).get("url")
        doi = (data.get("externalIds") or {}).get("DOI")
        venue = data.get("publicationVenue") or {}
        return {
            "doi":             doi,
            "citation_count":  data.get("citationCount"),
            "is_open_access":  data.get("isOpenAccess", False),
            "open_access_url": oa_pdf,
            "journal":         venue.get("name") or data.get("venue"),
        }
    except httpx.HTTPError:
        return {}


# ---------------------------------------------------------------------------
# Supabase upsert
# ---------------------------------------------------------------------------

def _supabase_headers() -> dict[str, str]:
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=ignore-duplicates,return=minimal",
    }


async def upsert_papers_supabase(
    papers: list[dict],
    dry_run: bool,
) -> int:
    if dry_run:
        for p in papers:
            log.info(
                "[DRY RUN] %s (%s) → topics: %s  oos: %s",
                p["title"][:70], p.get("year"), p["topics"], p.get("is_oos_paper"),
            )
        return len(papers)

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for DB writes.")
        sys.exit(1)

    url = f"{SUPABASE_URL}/rest/v1/papers"
    headers = _supabase_headers()

    added = 0
    # Upsert in batches of 50 (Supabase REST has a row limit per request)
    for i in range(0, len(papers), 50):
        batch = papers[i : i + 50]
        rows = []
        for p in batch:
            quality = 0.5 if p.get("abstract") else 0.2
            if (p.get("citation_count") or 0) > 100:
                quality = min(quality + 0.2, 0.9)
            if p.get("is_oos_paper"):
                quality = min(quality + 0.1, 0.95)

            rows.append({
                "id":              str(p.get("id") or uuid.uuid4()),
                "source":          p["source"],
                "source_id":       p["source_id"],
                "doi":             p.get("doi"),
                "arxiv_id":        p.get("arxiv_id"),
                "title":           p["title"],
                "authors":         p.get("authors", []),
                "year":            p.get("year"),
                "journal":         p.get("journal"),
                "abstract":        p.get("abstract"),
                "open_access_url": p.get("open_access_url"),
                "citation_count":  p.get("citation_count"),
                "topics":          p.get("topics", []),
                "factor_signals":  p.get("factor_signals", []),
                "is_preprint":     p.get("source") == "arxiv",
                "is_open_access":  bool(p.get("is_open_access")),
                "is_oos_paper":    bool(p.get("is_oos_paper")),
                "quality_score":   round(quality, 2),
                "curation_status": "candidate",
            })

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=rows, headers=headers, timeout=30)
            if resp.status_code not in (200, 201):
                log.warning("Supabase upsert returned %d: %s", resp.status_code, resp.text[:200])
            else:
                added += len(rows)
                log.info("Upserted batch of %d papers", len(rows))

    return added


# ---------------------------------------------------------------------------
# Main ingestion logic
# ---------------------------------------------------------------------------

async def ingest_topic(
    client: httpx.AsyncClient,
    topic: str,
    queries: list[tuple[str, list[str]]],
    limit_per_query: int,
    dry_run: bool,
    s2_enrich: bool = True,
) -> int:
    total = 0
    for query, base_topics in queries:
        log.info("Fetching: %s", query)
        papers = await fetch_arxiv_papers(client, query, limit=limit_per_query)
        log.info("  → %d papers from arXiv", len(papers))

        enriched = []
        for p in papers:
            # Classifier may add more topics beyond the query's base_topics
            classifier_topics = classify_topics(p["title"], p.get("abstract", ""))
            p["topics"] = sorted(set(base_topics) | set(classifier_topics))
            p["is_oos_paper"] = detect_oos_paper(p["title"], p.get("abstract", ""))

            # Enrich from Semantic Scholar (DOI, citation count, OA URL)
            if s2_enrich and p.get("arxiv_id"):
                s2 = await enrich_from_s2(client, p["arxiv_id"])
                p.update({k: v for k, v in s2.items() if v is not None})
                await asyncio.sleep(0.1)  # S2 rate limit

            enriched.append(p)

        count = await upsert_papers_supabase(enriched, dry_run=dry_run)
        total += count
        log.info("  → upserted %d new papers for topic %r", count, topic)

    return total


async def main(args: argparse.Namespace) -> None:
    if args.arxiv_id:
        async with httpx.AsyncClient() as client:
            p = await fetch_arxiv_by_id(client, args.arxiv_id)
        if not p:
            log.error("Paper not found: %s", args.arxiv_id)
            sys.exit(1)
        p["topics"] = classify_topics(p["title"], p.get("abstract", ""))
        p["is_oos_paper"] = detect_oos_paper(p["title"], p.get("abstract", ""))
        await upsert_papers_supabase([p], dry_run=args.dry_run)
        return

    topics_to_run = (
        {args.topic: TOPIC_QUERIES[args.topic]} if args.topic
        else TOPIC_QUERIES
    )
    if args.topic and args.topic not in TOPIC_QUERIES:
        log.error("Unknown topic: %r. Valid: %s", args.topic, sorted(TOPIC_QUERIES))
        sys.exit(1)

    limit = args.limit
    grand_total = 0
    async with httpx.AsyncClient() as client:
        for topic, queries in topics_to_run.items():
            log.info("=== Topic: %s ===", topic)
            n = await ingest_topic(
                client, topic, queries,
                limit_per_query=limit,
                dry_run=args.dry_run,
                s2_enrich=not args.no_s2,
            )
            grand_total += n

    log.info("Done. Total papers upserted: %d", grand_total)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Ingest q-fin arXiv papers into ConvexPi literature DB")
    p.add_argument("--topic",     help="Single topic to ingest (default: all)")
    p.add_argument("--arxiv-id",  help="Ingest a single paper by arXiv ID")
    p.add_argument("--limit",     type=int, default=200, help="Papers per arXiv query (default: 200)")
    p.add_argument("--dry-run",   action="store_true", help="Print what would be inserted without writing")
    p.add_argument("--no-s2",     action="store_true", help="Skip Semantic Scholar enrichment (faster)")
    args = p.parse_args()
    asyncio.run(main(args))
