"""
curate_relevance.py — Re-grade the papers corpus for *finance* relevance.

The original ingest gate (`is_finance_relevant`) is a single-term OR match, which is too loose:
famous non-finance papers pulled in by the citation-graph expansion (AlphaFold, "Why Should I
Trust You?", etc.) match one stray word ("value", "return") and then dominate the library because
they have enormous citation counts. This pass re-grades every paper with a stricter, signal-based
classifier and marks the off-topic ones `curation_status='rejected'` so the site (which only shows
`candidate`/`approved`) stops surfacing them.

    python pipeline/curate_relevance.py --dry-run     # report what would change, with samples
    python pipeline/curate_relevance.py               # apply: reject off-topic candidates

Env: SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) and SUPABASE_SERVICE_KEY.
Never touches `approved` rows; only flips `candidate` -> `rejected` (and can revive a previously
rejected row back to `candidate` if it now passes, with --revive).
"""
from __future__ import annotations
import argparse, json, os, re, sys, urllib.request, urllib.parse

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# --- Authoritative venues: presence of the journal name alone settles relevance --------------
# Pure finance journals — keep every paper.
FINANCE_JOURNALS = [
    "journal of finance", "review of financial studies", "journal of financial economics",
    "journal of financial and quantitative", "journal of financial markets",
    "journal of empirical finance", "journal of banking", "review of finance",
    "review of asset pricing", "review of corporate finance",
    "journal of portfolio management", "financial analysts journal", "quantitative finance",
    "journal of financial data science", "journal of asset management",
    "mathematical finance", "finance and stochastics", "journal of risk and financial",
    "journal of financial data", "financial management",
]
# Accounting journals — the accruals / earnings-quality / PEAD literature is core asset-pricing
# material in this course, so keep these wholesale too.
ACCOUNTING_JOURNALS = [
    "accounting review", "journal of accounting", "review of accounting",
    "accounting and economics", "contemporary accounting",
]
# AI-in-finance venues — finance by construction.
AI_FINANCE_VENUES = ["icaif", "ai in finance"]

# --- Finance signal vocabulary (used to gate econ journals / ML venues / un-journalled rows) -
# Generous on purpose: these are the ambiguous classes, and we would rather keep a borderline
# finance/econ paper than hide a canonical one like Black-Scholes or CoVaR.
FINANCE_SIGNAL = [
    "asset pricing", "asset-pricing", "stock", "equity", "equities", "portfolio",
    "expected return", "stock return", "excess return", "abnormal return", "asset return",
    "cross-section", "cross section", "risk premium", "risk-premium", "equity premium",
    "book-to-market", "book to market", "momentum", "factor model", "factor zoo",
    "anomal", "sharpe", "fama", "value premium", "illiquidity", "liquidity",
    "return predictab", "price predictab", "option", "derivative", "futures contract",
    "volatilit", "garch", "idiosyncratic", "implied vol", "volatility surface",
    "value at risk", "systemic risk", "tail risk", "downside risk",
    "trader", "acquir", "takeover", "merger", "overconfiden",
    "limit order", "bid-ask", "bid ask", "order flow", "microstructure",
    "trading strateg", "trading volume", "backtest", "hedge fund", "mutual fund",
    "arbitrage", "short sell", "short interest", "margin", "leverage",
    "yield curve", "credit spread", "credit risk", "default risk", "term structure",
    "exchange rate", "currency", "bond return", "corporate bond", "sovereign",
    "stock market", "financial market", "equity market", "capital market",
    "investor", "investment", "earnings", "accrual", "dividend", "valuation",
    "stock price", "share price", "securit", "firm value", "market value",
    "asset allocation", "factor investing", "smart beta", "risk factor",
    "behavioral finance", "market efficiency", "efficient market", "asset return",
    "financial econom", "banking", "monetary policy", "interest rate",
]

# --- Disqualifying domains (hard science / unrelated CS). Matched on WORD BOUNDARIES so that
#     "rna"/"dna" can't fire inside inteRNAtional / goveRNAnce, etc. ---------------------------
DISQUALIFY = [
    r"protein", r"molecul", r"genom", r"\brna\b", r"\bdna\b", r"amino acid", r"crystal structure",
    r"clinical", r"patient", r"\bdisease", r"\bcancer", r"\btumou?r", r"vaccine", r"epidemi",
    r"galax", r"cosmolog", r"astrophys", r"quantum chemistr", r"particle physics",
    r"graphene", r"\bbattery\b", r"solar cell", r"photonic", r"semiconductor device",
    r"\bneurons?\b", r"brain imag", r"\bmri\b", r"\beeg\b", r"\bfmri\b", r"personality trait",
    r"pedestrian", r"autonomous driving", r"self-driving", r"traffic flow",
    r"object detection", r"image classification", r"image segmentation", r"semantic segmentation",
    r"speech recognition", r"video understanding", r"point cloud",
    r"wireless network", r"\bantenna", r"5g network", r"wireless sensor",
    r"protein folding", r"drug discovery", r"molecular dynamics", r"climate model",
    r"crop yield", r"remote sensing", r"satellite imag",
]
_DISQ_RE = re.compile("|".join(DISQUALIFY))

# Short, ambiguous finance tokens that must match as whole words: "alpha" (not alphaFOLD/alphabet),
# "covar" (CoVaR, not covariance), "capm", "var" (value-at-risk, not variance/various).
_SIGNAL_RE = re.compile(r"\b(alpha|covar|capm)\b")


def _has(words, text):
    hits = [w for w in words if w in text]
    m = _SIGNAL_RE.search(text)
    if m:
        hits.append(m.group(1))
    return hits


def grade(p) -> tuple[bool, str]:
    """Return (is_finance, reason). Journal class decides first; keyword signal gates the rest."""
    title = (p.get("title") or "").lower()
    abstract = (p.get("abstract") or "").lower()
    journal = (p.get("journal") or "").lower()
    source = (p.get("source") or "").lower()
    text = " " + title + " " + abstract + " "

    # 1. Authoritative venues settle it.
    if any(v in journal for v in FINANCE_JOURNALS):
        return True, "finance journal"
    if any(v in journal for v in ACCOUNTING_JOURNALS):
        return True, "accounting journal"
    if any(v in journal for v in AI_FINANCE_VENUES):
        return True, "AI-in-finance venue"

    # 2. arXiv q-fin: ingested from finance categories — keep unless the title is clearly off-topic.
    if source == "arxiv":
        if _DISQ_RE.search(title) and not _has(FINANCE_SIGNAL, " " + title + " "):
            return False, "arxiv but off-topic title"
        return True, "arxiv q-fin"

    # 3. Everything else (econ journals, ML venues, citation-graph, un-journalled): require a
    #    finance signal and no disqualifying domain.
    sig = _has(FINANCE_SIGNAL, text)
    disq = _DISQ_RE.search(text)
    if disq and not _has(FINANCE_SIGNAL, " " + title + " "):
        return False, f"off-topic ({disq.group(0)}), no finance title signal"
    if sig:
        return True, f"finance signal ({sig[0].strip()})"
    return False, "no finance signal"


def fetch_all():
    rows, page = [], 1000
    fields = "id,title,abstract,journal,source,topics,citation_count,curation_status"
    for frm in range(0, 100000, page):
        q = f"papers?select={fields}&order=citation_count.desc.nullslast&limit={page}&offset={frm}"
        req = urllib.request.Request(f"{URL}/rest/v1/{q}",
            headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"})
        with urllib.request.urlopen(req) as r:
            batch = json.loads(r.read().decode())
        rows.extend(batch)
        if len(batch) < page:
            break
    return rows


def patch_status(ids, status):
    # PostgREST: PATCH with id=in.(...) in chunks
    for i in range(0, len(ids), 200):
        chunk = ids[i:i+200]
        inlist = "(" + ",".join(chunk) + ")"
        url = f"{URL}/rest/v1/papers?id=in.{urllib.parse.quote(inlist)}"
        body = json.dumps({"curation_status": status}).encode()
        req = urllib.request.Request(url, data=body, method="PATCH",
            headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                     "Content-Type": "application/json", "Prefer": "return=minimal"})
        urllib.request.urlopen(req).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revive", action="store_true",
                    help="also flip rejected->candidate for rows that now pass")
    args = ap.parse_args()
    if not URL or not KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")

    rows = fetch_all()
    print(f"Graded {len(rows)} papers.\n")

    to_reject, to_revive, kept = [], [], 0
    sample_reject, sample_protected = [], []
    for p in rows:
        ok, reason = grade(p)
        cs = p.get("curation_status")
        if ok:
            kept += 1
            if cs == "rejected" and args.revive:
                to_revive.append(p["id"])
        else:
            if cs in ("candidate",):           # only demote candidates; never touch approved
                to_reject.append(p["id"])
                if len(sample_reject) < 25:
                    sample_reject.append((p.get("citation_count") or 0, p["title"][:78], reason))
            elif cs == "approved":
                sample_protected.append((p.get("citation_count") or 0, p["title"][:70], reason))

    print(f"Would KEEP (finance):         {kept}")
    print(f"Would REJECT (candidate->rejected): {len(to_reject)}")
    if args.revive:
        print(f"Would REVIVE (rejected->candidate): {len(to_revive)}")
    print("\n--- Top would-be rejects by citation count (sanity check) ---")
    for c, t, why in sorted(sample_reject, reverse=True):
        print(f"  {c:>7}  {t}   [{why}]")
    if sample_protected:
        print("\n--- 'approved' rows that FAIL the new gate (left untouched, review manually) ---")
        for c, t, why in sorted(sample_protected, reverse=True)[:15]:
            print(f"  {c:>7}  {t}   [{why}]")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return
    if to_reject:
        patch_status(to_reject, "rejected")
        print(f"\nRejected {len(to_reject)} off-topic papers.")
    if args.revive and to_revive:
        patch_status(to_revive, "candidate")
        print(f"Revived {len(to_revive)} papers.")


if __name__ == "__main__":
    main()
