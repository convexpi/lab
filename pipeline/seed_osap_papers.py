#!/usr/bin/env python3
"""
seed_osap_papers.py — Seed the literature DB with the canonical anomaly papers.

The Open Source Asset Pricing SignalDoc.csv lists, for each of ~212 equity
anomalies, the *defining* published paper as (Authors, Year, Journal) — e.g.
"Sloan 1996 AR" for accruals, "Jegadeesh and Titman 1993 JF" for momentum.
These are exactly the foundational journal papers that arXiv (a recent-preprint
server) does not have.

This script resolves each citation to a real published paper via Crossref
(author + journal ISSN + year, ranked by relevance and citation count),
enriches it with an abstract and open-access link from OpenAlex, upserts it into
the Supabase `papers` table, and links it to its anomaly in `anomaly_papers`
(is_primary = True).

All sources are free and fully open (Crossref + OpenAlex polite pools).

Usage:
    python pipeline/seed_osap_papers.py
    python pipeline/seed_osap_papers.py --limit 20
    python pipeline/seed_osap_papers.py --dry-run
    python pipeline/seed_osap_papers.py --acronym Accruals

Env vars:
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key
    CONTACT_EMAIL         used for Crossref/OpenAlex polite pool (default below)
    CONVEXPI_DATA_DIR     data root (default: /Users/smc77/convexpi-data)
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("CONVEXPI_DATA_DIR", "/Users/smc77/convexpi-data"))
SIGNALDOC = Path(os.environ.get(
    "OSAP_SIGNALDOC",
    str(Path.home() / ".convexpi" / "cache" / "osap_SignalDoc.csv"),
))

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
CONTACT_EMAIL        = os.environ.get("CONTACT_EMAIL", "shane.conway@gmail.com")

CROSSREF_API = "https://api.crossref.org/works"
OPENALEX_API = "https://api.openalex.org/works"
UA = f"ConvexPi-Lab/1.0 (https://convexpi.ai; mailto:{CONTACT_EMAIL})"

# ── OSAP journal abbreviation → (full name, ISSN for Crossref filter) ─────────
JOURNALS: dict[str, tuple[str, str | None]] = {
    "JF":       ("Journal of Finance", "0022-1082"),
    "JFE":      ("Journal of Financial Economics", "0304-405X"),
    "RFS":      ("Review of Financial Studies", "0893-9454"),
    "JFQA":     ("Journal of Financial and Quantitative Analysis", "0022-1090"),
    "AR":       ("The Accounting Review", "0001-4826"),
    "JAE":      ("Journal of Accounting and Economics", "0165-4101"),
    "JAR":      ("Journal of Accounting Research", "0021-8456"),
    "RAS":      ("Review of Accounting Studies", "1380-6653"),
    "CAR":      ("Contemporary Accounting Research", "0823-9150"),
    "BAR":      ("British Accounting Review", "0890-8389"),
    "MS":       ("Management Science", "0025-1909"),
    "JPE":      ("Journal of Political Economy", "0022-3808"),
    "QJE":      ("Quarterly Journal of Economics", "0033-5533"),
    "RED":      ("Review of Economic Dynamics", "1094-2025"),
    "FAJ":      ("Financial Analysts Journal", "0015-198X"),
    "ROF":      ("Review of Finance", "1572-3097"),
    "JFM":      ("Journal of Financial Markets", "1386-4181"),
    "RFQA":     ("Review of Quantitative Finance and Accounting", "0924-865X"),
    "JPM":      ("Journal of Portfolio Management", "0095-4918"),
    "JFR":      ("Journal of Financial Research", "0270-2592"),
    "JBFA":     ("Journal of Business Finance & Accounting", "0306-686X"),
    "JEmpFin":  ("Journal of Empirical Finance", "0927-5398"),
    "JOIM":     ("Journal of Investment Management", None),
    "Other":    (None, None),
    "WP":       (None, None),
    "Book":     (None, None),
}

# ── OSAP Cat.Economic → ConvexPi topic taxonomy ──────────────────────────────
TOPIC_MAP: dict[str, list[str]] = {
    "momentum":             ["momentum"],
    "valuation":            ["value"],
    "long term reversal":   ["reversal"],
    "short-term reversal":  ["reversal"],
    "profitability":        ["quality"],
    "profitability alt":    ["quality"],
    "accruals":             ["quality"],
    "earnings forecast":    ["quality"],
    "earnings growth":      ["quality"],
    "earnings event":       ["quality"],
    "composite accounting": ["quality"],
    "investment":           ["quality"],
    "investment alt":       ["quality"],
    "investment growth":    ["quality"],
    "asset composition":    ["quality"],
    "sales growth":         ["quality"],
    "R&D":                  ["quality"],
    "external financing":   ["quality"],
    "payout indicator":     ["quality"],
    "leverage":             ["quality"],
    "risk":                 ["low_volatility"],
    "volatility":           ["low_volatility"],
    "cash flow risk":       ["low_volatility"],
    "default risk":         ["low_volatility"],
    "optionrisk":           ["options"],
    "liquidity":            ["microstructure"],
    "volume":               ["microstructure"],
    "informed trading":     ["microstructure"],
    "short sale constraints": ["microstructure"],
    "size":                 ["size"],
    "lead lag":             ["reversal"],
    "recommendation":       ["quality"],
    "ownership":            ["quality"],
    "info proxy":           ["quality"],
}


# ---------------------------------------------------------------------------
# Citation parsing helpers
# ---------------------------------------------------------------------------

def first_author_surname(authors: str) -> str:
    """'Jegadeesh and Titman' -> 'Jegadeesh'; 'Ang et al.' -> 'Ang'."""
    a = authors.replace(" and ", ",").replace(";", ",").split(",")[0].strip()
    # Drop trailing "et al." which would otherwise become the surname
    a = a.replace("et al.", "").replace("et al", "").strip()
    return a.split()[-1].strip(".") if a else a


def _strip_accents(s: str) -> str:
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def surname_in_authors(surname: str, cr_authors: list[dict]) -> bool:
    s = _strip_accents(surname.lower())
    return any(
        s in _strip_accents((a.get("family", "") or "").lower())
        for a in cr_authors
    )


def _norm_journal(name: str | None) -> str:
    if not name:
        return ""
    n = name.lower().replace("&amp;", "and").replace("&", "and")
    for junk in ("the ", "  "):
        n = n.replace(junk, " ")
    return "".join(ch for ch in n if ch.isalnum() or ch == " ").strip()


def journal_matches(expected_name: str | None, cr_journal: str | None) -> bool:
    """Fuzzy: the distinctive words of the expected journal appear in the match.
    e.g. expected 'Journal of Finance' vs 'The Journal of Finance' -> True."""
    if not expected_name:
        return True  # no expectation (Other/WP/Book) — don't gate on journal
    exp = _norm_journal(expected_name)
    got = _norm_journal(cr_journal)
    if not got:
        return False
    # All expected tokens longer than 2 chars must be present in the match.
    exp_tokens = [t for t in exp.split() if len(t) > 2 and t != "and"]
    return all(t in got for t in exp_tokens)


# ---------------------------------------------------------------------------
# Crossref resolution
# ---------------------------------------------------------------------------

def crossref_search(client: httpx.Client, surname: str, topic: str,
                    year: int, issn: str | None) -> list[dict]:
    flt = [f"from-pub-date:{year-1}-01-01", f"until-pub-date:{year+1}-12-31"]
    params = {
        "query.author": surname,
        "rows": "8",
        "mailto": CONTACT_EMAIL,
    }
    if issn:
        # NB: Crossref returns nothing when query.bibliographic is combined with
        # both query.author and an ISSN filter. With a journal pinned, author +
        # year is already a strong key, so we omit the topic query and rank by
        # citation count instead.
        flt.append(f"issn:{issn}")
    else:
        # No journal to pin — lean on the topical query for precision.
        params["query.bibliographic"] = topic
    params["filter"] = ",".join(flt)
    try:
        r = client.get(CROSSREF_API, params=params, timeout=30, headers={"User-Agent": UA})
        r.raise_for_status()
        return r.json()["message"]["items"]
    except (httpx.HTTPError, KeyError) as exc:
        log.warning("  crossref search failed: %s", exc)
        return []


def _result_year(it: dict, fallback: int) -> int:
    for key in ("published", "published-print", "published-online", "issued"):
        dp = (it.get(key) or {}).get("date-parts") or [[None]]
        if dp and dp[0] and dp[0][0]:
            return dp[0][0]
    return fallback


_TOPIC_STOPWORDS = {
    "the", "and", "for", "with", "stock", "stocks", "return", "returns",
    "cross", "section", "expected", "effect", "anomaly", "based", "using",
    # Generic words that appear in many finance/accounting titles and would
    # otherwise produce spurious one-word title hits:
    "market", "markets", "price", "prices", "capital", "evidence", "model",
    "models", "analysis", "empirical", "study", "approach", "premium",
    "financial", "economic", "corporate", "firm", "firms",
}


def topic_keywords(topic: str) -> set[str]:
    return {
        w for w in "".join(c.lower() if c.isalnum() else " " for c in topic).split()
        if len(w) > 3 and w not in _TOPIC_STOPWORDS
    }


def _title_hits(it: dict, keywords: set[str]) -> int:
    title = (it.get("title") or [""])[0].lower()
    return sum(1 for kw in keywords if kw in title)


def pick_best(items: list[dict], surname: str, year: int,
              expected_journal: str | None, keywords: set[str]) -> dict | None:
    """A candidate must include the first-author surname and be published within
    ±1 year of the OSAP year.

    When OSAP names a journal (known ISSN), we require the match to be in that
    journal, then rank by how many anomaly keywords appear in the title (to
    disambiguate multiple same-author papers), tie-broken by citation count.

    When OSAP gives no journal (Other/WP/Book), we have no journal guard, so we
    fall back to a strict Crossref relevance-score threshold to avoid junk."""
    known_journal = expected_journal is not None
    candidates = []
    for it in items:
        if not surname_in_authors(surname, it.get("author", [])):
            continue
        if abs(_result_year(it, year) - year) > 1:
            continue
        cr_journal = (it.get("container-title") or [None])[0]
        if known_journal:
            if not journal_matches(expected_journal, cr_journal):
                continue
        else:
            if (it.get("score", 0) or 0) < 40.0:
                continue
        candidates.append(it)
    if not candidates:
        return None
    if known_journal:
        candidates.sort(
            key=lambda it: (_title_hits(it, keywords), it.get("is-referenced-by-count", 0)),
            reverse=True,
        )
    else:
        candidates.sort(
            key=lambda it: (it.get("score", 0) or 0, it.get("is-referenced-by-count", 0)),
            reverse=True,
        )
    return candidates[0]


# ---------------------------------------------------------------------------
# OpenAlex enrichment (abstract, OA url, citations)
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


def openalex_by_doi(client: httpx.Client, doi: str) -> dict:
    url = f"{OPENALEX_API}/https://doi.org/{doi}"
    try:
        r = client.get(url, params={"mailto": CONTACT_EMAIL}, timeout=30,
                       headers={"User-Agent": UA})
        if r.status_code != 200:
            return {}
        w = r.json()
        oa = w.get("open_access") or {}
        best = w.get("best_oa_location") or {}
        return {
            "abstract":        _abstract_from_inverted(w.get("abstract_inverted_index")),
            "citation_count":  w.get("cited_by_count"),
            "is_open_access":  oa.get("is_oa", False),
            "open_access_url": oa.get("oa_url") or best.get("pdf_url"),
            "openalex_id":     (w.get("id") or "").rsplit("/", 1)[-1] or None,
        }
    except httpx.HTTPError:
        return {}


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


def upsert_paper(client: httpx.Client, row: dict) -> str | None:
    """Upsert by DOI; returns the paper id."""
    # Does a paper with this DOI already exist?
    r = client.get(f"{SUPABASE_URL}/rest/v1/papers",
                   params={"select": "id", "doi": f"eq.{row['doi']}"},
                   headers=_headers(), timeout=30)
    existing = r.json() if r.status_code == 200 else []
    if existing:
        pid = existing[0]["id"]
        client.patch(f"{SUPABASE_URL}/rest/v1/papers",
                     params={"id": f"eq.{pid}"},
                     json={k: v for k, v in row.items() if k != "id"},
                     headers=_headers({"Prefer": "return=minimal"}), timeout=30)
        return pid

    resp = client.post(f"{SUPABASE_URL}/rest/v1/papers", json=row,
                       headers=_headers({"Prefer": "return=representation"}), timeout=30)
    if resp.status_code not in (200, 201):
        log.warning("  upsert failed %d: %s", resp.status_code, resp.text[:160])
        return None
    return resp.json()[0]["id"]


def link_anomaly(client: httpx.Client, anomaly_id: str, paper_id: str) -> None:
    payload = {
        "anomaly_id": anomaly_id,
        "paper_id":   paper_id,
        "is_primary": True,
        "added_by":   "osap_seed",
    }
    client.post(f"{SUPABASE_URL}/rest/v1/anomaly_papers", json=payload,
                headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
                timeout=30)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_predictors() -> list[dict]:
    if not SIGNALDOC.exists():
        log.error("SignalDoc not found at %s — run expand_anomalies.py first.", SIGNALDOC)
        sys.exit(1)
    with open(SIGNALDOC, newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("Cat.Signal", "").strip() == "Predictor"]


def build_topic_query(rec: dict) -> str:
    parts = [rec.get("LongDescription", ""), rec.get("Cat.Economic", "")]
    return " ".join(p for p in parts if p).strip()


def run(args: argparse.Namespace) -> None:
    if not args.dry_run and (not SUPABASE_URL or not SUPABASE_SERVICE_KEY):
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    preds = load_predictors()
    if args.acronym:
        preds = [r for r in preds if r["Acronym"].lower() == args.acronym.lower()]
    if args.limit:
        preds = preds[: args.limit]
    log.info("Resolving %d OSAP predictor papers", len(preds))

    matched = unmatched = 0
    unmatched_list: list[str] = []

    with httpx.Client() as client:
        for i, rec in enumerate(preds, 1):
            acro = rec["Acronym"]
            authors = rec.get("Authors", "").strip()
            try:
                year = int(rec.get("Year", "") or 0)
            except ValueError:
                year = 0
            jabbr = rec.get("Journal", "").strip()
            jname, issn = JOURNALS.get(jabbr, (None, None))
            surname = first_author_surname(authors)
            topic_q = build_topic_query(rec)

            if not surname or not year:
                log.warning("[%d/%d] %s — missing author/year, skipping", i, len(preds), acro)
                unmatched += 1; unmatched_list.append(acro); continue

            items = crossref_search(client, surname, topic_q, year, issn)
            # Fallback: if the ISSN search returned nothing (some journals have
            # spotty ISSN metadata in Crossref), retry with the topic query and
            # no ISSN. Precision is still protected because pick_best enforces
            # journal_matches() against the expected journal name.
            if not items:
                items = crossref_search(client, surname, topic_q, year, None)
            kws = topic_keywords(topic_q + " " + acro)
            best = pick_best(items, surname, year, jname, kws)
            time.sleep(0.4)  # polite pool

            if not best:
                log.warning("[%d/%d] %s — NO MATCH (%s %s %s)", i, len(preds),
                            acro, authors, year, jabbr)
                unmatched += 1; unmatched_list.append(acro); continue

            doi = (best.get("DOI") or "").lower()
            title = (best.get("title") or ["?"])[0]
            cr_journal = (best.get("container-title") or [None])[0]
            cr_authors = [
                {"name": f"{a.get('given','')} {a.get('family','')}".strip()}
                for a in best.get("author", [])
            ]
            pub_year = (best.get("issued", {}).get("date-parts", [[year]])[0] or [year])[0]

            enr = openalex_by_doi(client, doi) if doi else {}
            time.sleep(0.3)

            topics = TOPIC_MAP.get(rec.get("Cat.Economic", "").strip(), [])

            row = {
                "id":              str(uuid.uuid4()),
                "source":          "crossref",
                "source_id":       doi or f"osap:{acro}",
                "doi":             doi or None,
                "arxiv_id":        None,
                "title":           title,
                "authors":         cr_authors or [{"name": authors}],
                "year":            pub_year,
                "journal":         cr_journal or jname,
                "abstract":        enr.get("abstract"),
                "open_access_url": enr.get("open_access_url"),
                "citation_count":  enr.get("citation_count") or best.get("is-referenced-by-count"),
                "topics":          topics,
                "factor_signals":  [acro],
                "is_preprint":     False,
                "is_open_access":  bool(enr.get("is_open_access")),
                "is_oos_paper":    False,  # foundational papers report IS evidence
                "quality_score":   0.9,    # hand-curated canonical literature
                "curation_status": "approved",
            }

            log.info("[%d/%d] %s ✓ %s (%s, %s)", i, len(preds), acro,
                     title[:55], cr_journal or jname, pub_year)

            if args.dry_run:
                matched += 1
                continue

            pid = upsert_paper(client, row)
            if pid:
                link_anomaly(client, acro.lower(), pid)
                matched += 1
            else:
                unmatched += 1; unmatched_list.append(acro)

    log.info("Done. matched=%d unmatched=%d", matched, unmatched)
    if unmatched_list:
        log.info("Unmatched acronyms: %s", ", ".join(unmatched_list))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed canonical OSAP anomaly papers via Crossref + OpenAlex.")
    p.add_argument("--limit", type=int, help="Max predictors to process")
    p.add_argument("--acronym", help="Only this OSAP acronym (e.g. Accruals)")
    p.add_argument("--dry-run", action="store_true", help="Resolve and print, but don't write")
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
