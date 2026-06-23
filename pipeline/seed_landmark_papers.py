"""
seed_landmark_papers.py — ingest the genuinely-missing landmark papers.

The auto-discovery pipeline (arXiv q-fin, journal ISSN sweeps, citation-graph) never picked up many
of the field's foundational papers — CAPM, APT, the Fama-French factor papers, ARCH/GARCH, the
original idiosyncratic-volatility paper, etc. This script seeds a curated list so the library has
proper anchor pages for them. Each landmark is resolved via a Crossref bibliographic search
(verified by author surname + year), enriched with abstract/citations from OpenAlex, and upserted by
DOI as a hand-curated, `approved` row (protected from the relevance sweep). Re-runnable / idempotent.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/seed_landmark_papers.py --dry-run
    ...                                          python pipeline/seed_landmark_papers.py
"""
from __future__ import annotations
import argparse, os, sys, time, unicodedata, uuid
import httpx

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
MAIL = "research@convexpi.ai"
UA = "convexpi-lab/landmarks (mailto:research@convexpi.ai)"
CROSSREF = "https://api.crossref.org/works"
OPENALEX = "https://api.openalex.org/works"

# (title query, first-author surname, year, topics) — the genuinely-missing canon.
LANDMARKS = [
    ("Capital Asset Prices: A Theory of Market Equilibrium under Conditions of Risk", "Sharpe", 1964, ["meta"]),
    ("The Valuation of Risk Assets and the Selection of Risky Investments in Stock Portfolios and Capital Budgets", "Lintner", 1965, ["meta"]),
    ("The arbitrage theory of capital asset pricing", "Ross", 1976, ["meta"]),
    ("Portfolio Selection", "Markowitz", 1952, ["meta"]),
    ("Efficient capital markets: A review of theory and empirical work", "Fama", 1970, ["meta"]),
    ("Common risk factors in the returns on stocks and bonds", "Fama", 1993, ["value", "size"]),
    ("Multifactor explanations of asset pricing anomalies", "Fama", 1996, ["value", "size"]),
    ("A five-factor asset pricing model", "Fama", 2015, ["value", "size", "quality"]),
    ("On persistence in mutual fund performance", "Carhart", 1997, ["momentum"]),
    ("Digesting anomalies: An investment approach", "Hou", 2015, ["meta", "value", "quality"]),
    ("Investor psychology and security market under- and overreactions", "Daniel", 1998, ["momentum", "reversal"]),
    ("Do stock prices fully reflect information in accruals and cash flows?", "Sloan", 1996, ["quality"]),
    ("Contrarian investment, extrapolation, and risk", "Lakonishok", 1994, ["value"]),
    ("The cross-section of volatility and expected returns", "Ang", 2006, ["low_volatility"]),
    ("Investment performance of common stocks in relation to their price-earnings ratios", "Basu", 1977, ["value"]),
    ("Stock market prices do not follow random walks: Evidence from a simple specification test", "Lo", 1988, ["meta"]),
    ("Do stock prices move too much to be justified by subsequent changes in dividends?", "Shiller", 1981, ["meta"]),
    ("An intertemporal capital asset pricing model", "Merton", 1973, ["meta"]),
    ("On the pricing of corporate debt: the risk structure of interest rates", "Merton", 1974, ["meta"]),
    ("The equity premium: A puzzle", "Mehra", 1985, ["meta"]),
    ("The performance of mutual funds in the period 1945-1964", "Jensen", 1968, ["meta"]),
    ("The fundamental law of active management", "Grinold", 1989, ["meta"]),
    ("Global portfolio optimization", "Black", 1992, ["meta"]),
    ("Autoregressive conditional heteroscedasticity with estimates of the variance of United Kingdom inflation", "Engle", 1982, ["low_volatility"]),
    ("Generalized autoregressive conditional heteroskedasticity", "Bollerslev", 1986, ["low_volatility"]),
    ("Conditional heteroskedasticity in asset returns: A new approach", "Nelson", 1991, ["low_volatility"]),
    ("A simple positive semi-definite heteroskedasticity and autocorrelation consistent covariance matrix", "Newey", 1987, ["meta"]),
]


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).lower()


def crossref_find(client, title, surname, year):
    try:
        r = client.get(CROSSREF, params={
            "query.bibliographic": title, "query.author": surname,
            "rows": 6, "mailto": MAIL,
        }, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        items = r.json()["message"]["items"]
    except (httpx.HTTPError, KeyError) as exc:
        print(f"   crossref error: {exc}")
        return None
    nsur = _norm(surname)
    best = None
    for it in items:
        authors = it.get("author") or []
        if not any(nsur in _norm(a.get("family", "")) for a in authors):
            continue
        yr = None
        for k in ("issued", "published-print", "published"):
            dp = (it.get(k) or {}).get("date-parts") or [[None]]
            if dp and dp[0] and dp[0][0]:
                yr = dp[0][0]; break
        if yr is None or abs(yr - year) > 2:
            continue
        best = (it, yr)
        break
    return best


def openalex_by_doi(client, doi):
    try:
        r = client.get(f"{OPENALEX}/https://doi.org/{doi}",
                       params={"mailto": MAIL}, headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200:
            return {}
        w = r.json()
        inv = w.get("abstract_inverted_index")
        abstract = None
        if inv:
            pos = sorted((i, word) for word, idxs in inv.items() for i in idxs)
            abstract = " ".join(w for _, w in pos) or None
        oa = w.get("open_access") or {}
        return {"abstract": abstract, "citation_count": w.get("cited_by_count"),
                "is_open_access": oa.get("is_oa", False), "open_access_url": oa.get("oa_url")}
    except httpx.HTTPError:
        return {}


def _headers(extra=None):
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


def upsert(client, row):
    r = client.get(f"{URL}/rest/v1/papers", params={"select": "id", "doi": f"eq.{row['doi']}"},
                   headers=_headers(), timeout=30)
    existing = r.json() if r.status_code == 200 else []
    if existing:
        pid = existing[0]["id"]
        client.patch(f"{URL}/rest/v1/papers", params={"id": f"eq.{pid}"},
                     json={k: v for k, v in row.items() if k != "id"},
                     headers=_headers({"Prefer": "return=minimal"}), timeout=30)
        return pid, "updated"
    resp = client.post(f"{URL}/rest/v1/papers", json=row,
                       headers=_headers({"Prefer": "return=representation"}), timeout=30)
    if resp.status_code not in (200, 201):
        print(f"   upsert failed {resp.status_code}: {resp.text[:160]}")
        return None, "error"
    return resp.json()[0]["id"], "inserted"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not URL or not KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")

    matched = missed = 0
    with httpx.Client(follow_redirects=True) as client:
        for i, (title, surname, year, topics) in enumerate(LANDMARKS, 1):
            found = crossref_find(client, title, surname, year)
            time.sleep(0.3)
            if not found:
                print(f"[{i:2}/{len(LANDMARKS)}] MISS  {surname} {year} — {title[:50]}")
                missed += 1
                continue
            it, yr = found
            doi = (it.get("DOI") or "").lower()
            cr_title = (it.get("title") or [title])[0]
            authors = [{"name": f"{a.get('given','').strip()} {a.get('family','').strip()}".strip()}
                       for a in (it.get("author") or [])] or [{"name": surname}]
            journal = (it.get("container-title") or [None])[0]
            enr = openalex_by_doi(client, doi) if doi else {}
            time.sleep(0.3)
            row = {
                "id": str(uuid.uuid4()), "source": "crossref",
                "source_id": doi or f"landmark:{surname}{year}", "doi": doi or None,
                "arxiv_id": None, "title": cr_title, "authors": authors, "year": yr,
                "journal": journal, "abstract": enr.get("abstract"),
                "open_access_url": enr.get("open_access_url"),
                "citation_count": enr.get("citation_count") or it.get("is-referenced-by-count"),
                "topics": topics, "factor_signals": [], "is_preprint": False,
                "is_open_access": bool(enr.get("is_open_access")), "is_oos_paper": False,
                "quality_score": 0.95, "curation_status": "approved",
            }
            cites = row["citation_count"]
            print(f"[{i:2}/{len(LANDMARKS)}] OK    {surname} {yr} cit={cites} — {cr_title[:48]}")
            matched += 1
            if not args.dry_run:
                upsert(client, row)
    print(f"\nmatched={matched} missed={missed}" + ("  (dry run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
