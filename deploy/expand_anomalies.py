#!/usr/bin/env python3
"""
expand_anomalies.py — Download OSAP data and write an expanded anomaly-stats.json.

Replaces (and extends) compute_anomaly_stats.py by adding ~200 anomalies from the
Open Source Asset Pricing dataset (Chen & Zimmermann, Critical Finance Review 2022)
on top of the existing 6 Kenneth French factors.

Sources:
  - French Data Library  → 6 flagship factors (Market, Size, Value, Momentum,
                            Profitability, Investment) with rich hand-written descriptions
  - OSAP PredictorPortsFull.csv  → 212 long-short predictor return series (1926–2024)
  - OSAP SignalDoc.csv           → metadata (authors, year, journal, category, definition)

Output schema per anomaly:
  id, slug, name, long_description, description, source, osap_acronym,
  category, data_category, authors, paper, journal, journal_full, pub_year,
  original_sample, t_stat, is_period, oos_period,
  is_return, is_sharpe, is_vol, oos_return, oos_sharpe, oos_vol,
  decay_pct, status, monthly_returns

Usage:
  python deploy/expand_anomalies.py
  python deploy/expand_anomalies.py --out path/to/anomaly-stats.json
  python deploy/expand_anomalies.py --no-monthly       # skip sparklines (faster)
  python deploy/expand_anomalies.py --min-oos 24       # require ≥24 OOS months
  python deploy/expand_anomalies.py --source french    # French factors only
  python deploy/expand_anomalies.py --source osap      # OSAP factors only
  python deploy/expand_anomalies.py --source all       # both (default)

Env vars (optional):
  OSAP_CACHE_DIR  directory for cached OSAP CSV files (default: ~/.convexpi/cache)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Ensure the local src takes precedence over any installed convexpi packages
# ---------------------------------------------------------------------------
_src = str(Path(__file__).parent.parent / "src")
sys.path = [_src] + [p for p in sys.path if "convexpi" not in p and "aiinfinance" not in p]

from convexpi.lab.anomalies import compute_all as _compute_french   # existing 6 factors

# ---------------------------------------------------------------------------
# OSAP Google Drive file IDs (2025-10 release)
# ---------------------------------------------------------------------------
_OSAP_SIGNAL_DOC_ID  = "1Sev9s6cPFUGgxp1pFiej0lGzpsMqJCI2"
_OSAP_PORTS_FULL_ID  = "10sOryk_ddjkXagaajTKUk1nwJs2ZLRiI"

# ---------------------------------------------------------------------------
# Category mapping: OSAP Cat.Economic → simplified display category
# ---------------------------------------------------------------------------
_CAT_MAP: dict[str, str] = {
    "momentum":              "Momentum",
    "long term reversal":    "Reversal",
    "valuation":             "Value",
    "profitability":         "Quality",
    "accruals":              "Quality",
    "composite accounting":  "Quality",
    "asset composition":     "Quality",
    "investment":            "Investment",
    "investment alt":        "Investment",
    "risk":                  "Risk",
    "volatility":            "Risk",
    "liquidity":             "Liquidity",
    "volume":                "Liquidity",
    "external financing":    "Financing",
    "earnings forecast":     "Analyst",
    "R&D":                   "Growth",
    "sales growth":          "Growth",
    "short sale constraints":"Microstructure",
    "lead lag":              "Microstructure",
    "other":                 "Other",
}

# ---------------------------------------------------------------------------
# Journal abbreviation → full name
# ---------------------------------------------------------------------------
_JOURNAL_MAP: dict[str, str] = {
    "JF":    "Journal of Finance",
    "JFE":   "Journal of Financial Economics",
    "RFS":   "Review of Financial Studies",
    "AR":    "Accounting Review",
    "JAE":   "Journal of Accounting and Economics",
    "JAR":   "Journal of Accounting Research",
    "JFQA":  "Journal of Financial and Quantitative Analysis",
    "MS":    "Management Science",
    "JPE":   "Journal of Political Economy",
    "RAS":   "Review of Accounting Studies",
    "RFQA":  "Review of Quantitative Finance and Accounting",
    "JB":    "Journal of Business",
    "JBF":   "Journal of Banking and Finance",
    "FM":    "Financial Management",
    "JEM":   "Journal of Empirical Finance",
    "AER":   "American Economic Review",
    "QJE":   "Quarterly Journal of Economics",
    "RES":   "Review of Economic Studies",
    "JEF":   "Journal of Economic Finance",
    "FAJ":   "Financial Analysts Journal",
}

# ---------------------------------------------------------------------------
# OSAP signals that overlap with the French catalogue — skip in OSAP pass
# so we don't produce duplicate entries with weaker descriptions.
# ---------------------------------------------------------------------------
_FRENCH_ACRONYMS = {
    "MktRF", "Mkt-RF", "SMB", "HML", "Mom12m", "Mom",
    "RMW", "CMA", "RF", "UMD",
}


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def _gdrive_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"


def _cache_dir() -> Path:
    import os
    d = Path(os.environ.get("OSAP_CACHE_DIR", Path.home() / ".convexpi" / "cache"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _download_csv(file_id: str, filename: str) -> str:
    """Download a CSV from Google Drive, caching locally. Returns text content."""
    cached = _cache_dir() / filename
    if cached.exists():
        print(f"  Using cached {filename}")
        return cached.read_text(encoding="utf-8")

    url = _gdrive_url(file_id)
    print(f"  Downloading {filename} from OSAP…")
    req = urllib.request.Request(url, headers={"User-Agent": "convexpi/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            content = resp.read()
    except Exception as exc:
        raise RuntimeError(f"Failed to download {filename}: {exc}") from exc

    # Google Drive large files redirect through a confirmation page.
    # If we got HTML instead of CSV, try gdown as fallback.
    if content[:5] == b"<!DOC" or b"<html" in content[:100].lower():
        content = _download_via_gdown(file_id, filename)

    text = content.decode("utf-8", errors="replace")
    cached.write_text(text, encoding="utf-8")
    return text


def _download_via_gdown(file_id: str, filename: str) -> bytes:
    """Fallback: use gdown library if direct URL returns HTML."""
    try:
        import gdown
    except ImportError:
        raise RuntimeError(
            "Direct Google Drive download returned HTML (confirmation page). "
            "Install gdown (pip install gdown) to download large files: "
            f"  gdown {file_id} -O {filename}"
        )
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name
    gdown.download(id=file_id, output=tmp_path, quiet=False)
    with open(tmp_path, "rb") as f:
        data = f.read()
    os.unlink(tmp_path)
    return data


# ---------------------------------------------------------------------------
# Load OSAP signal documentation
# ---------------------------------------------------------------------------

def _load_signal_doc() -> dict[str, dict]:
    """Return {Acronym: row_dict} for all Predictor signals."""
    text = _download_csv(_OSAP_SIGNAL_DOC_ID, "osap_SignalDoc.csv")
    reader = csv.DictReader(io.StringIO(text))
    result: dict[str, dict] = {}
    for row in reader:
        if row.get("Cat.Signal") != "Predictor":
            continue
        acronym = row["Acronym"]
        result[acronym] = row
    return result


# ---------------------------------------------------------------------------
# Load OSAP monthly portfolio returns
# ---------------------------------------------------------------------------

def _load_port_returns() -> dict[str, dict[str, float]]:
    """
    Return {signal_acronym: {YYYY-MM: monthly_pct_return}}.
    Monthly pct returns from PredictorPortsFull.csv (values already in %).
    """
    text = _download_csv(_OSAP_PORTS_FULL_ID, "osap_PredictorPortsFull.csv")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        return {}

    # Signal columns = everything except 'date'
    signals = [k for k in rows[0].keys() if k != "date"]
    result: dict[str, dict[str, float]] = {s: {} for s in signals}

    for row in rows:
        # date format: 'YYYY-MM-DD'  → we use 'YYYY-MM'
        date_str = row["date"][:7]   # '2024-12'
        for sig in signals:
            val = row.get(sig, "").strip()
            if val and val != "NA":
                try:
                    result[sig][date_str] = float(val)
                except ValueError:
                    pass

    return result


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def _sharpe_stats(
    monthly_pcts: list[float],
) -> tuple[float, float, float]:
    """
    Annualized return (%), Sharpe ratio, volatility (%) from monthly % returns.
    Returns (0, 0, 0) if fewer than 12 months of data.
    """
    if len(monthly_pcts) < 12:
        return 0.0, 0.0, 0.0
    rets = np.array(monthly_pcts) / 100.0   # convert pct → decimal
    ann_ret  = float(rets.mean() * 12) * 100
    ann_vol  = float(rets.std() * math.sqrt(12)) * 100
    sharpe   = (ann_ret / ann_vol) if ann_vol > 1e-6 else 0.0
    return round(ann_ret, 2), round(sharpe, 3), round(ann_vol, 2)


def _classify_status(oos_sharpe: float, min_oos_months: int, actual_oos_months: int) -> str:
    if actual_oos_months < min_oos_months:
        return "insufficient"
    if oos_sharpe > 0.5:
        return "alive"
    if oos_sharpe > 0.2:
        return "weakened"
    if oos_sharpe > 0:
        return "faded"
    return "dead"


def _build_sparkline(monthly_pcts: dict[str, float], years: int = 40) -> list[dict]:
    """Monthly cumulative return series for the last `years` years."""
    if not monthly_pcts:
        return []
    all_dates = sorted(monthly_pcts.keys())
    if not all_dates:
        return []
    last_year = int(all_dates[-1][:4])
    cutoff = f"{last_year - years}-01"
    pairs = [(d, monthly_pcts[d] / 100.0) for d in all_dates if d >= cutoff]
    if not pairs:
        return []
    cum = 1.0
    series = []
    for date_str, r in pairs:
        cum *= (1 + r)
        series.append({"date": date_str, "cum_ret": round(cum - 1, 4)})
    return series


# ---------------------------------------------------------------------------
# OSAP anomaly computation
# ---------------------------------------------------------------------------

def compute_osap(
    include_monthly: bool = True,
    min_oos_months: int = 12,
    skip_acronyms: set[str] | None = None,
) -> list[dict]:
    """Compute IS/OOS stats for all OSAP predictors."""
    print("Loading OSAP signal documentation…")
    signal_doc = _load_signal_doc()

    print("Loading OSAP portfolio returns…")
    port_returns = _load_port_returns()

    skip = (skip_acronyms or set()) | _FRENCH_ACRONYMS
    results: list[dict] = []

    for acronym, meta in signal_doc.items():
        if acronym in skip:
            continue

        monthly = port_returns.get(acronym, {})
        if not monthly:
            continue

        pub_year_str = meta.get("Year", "").strip()
        if not pub_year_str or not pub_year_str.isdigit():
            continue
        pub_year = int(pub_year_str)
        pub_prefix = f"{pub_year}-"

        is_rets  = [v for d, v in monthly.items() if d < pub_prefix]
        oos_rets = [v for d, v in monthly.items() if d >= pub_prefix]

        if len(is_rets) < 24:   # need at least 2 years IS
            continue

        is_ret, is_sh, is_vol   = _sharpe_stats(is_rets)
        oos_ret, oos_sh, oos_vol = _sharpe_stats(oos_rets)
        decay = 0.0
        if abs(is_sh) > 0.05 and oos_rets:
            decay = round((is_sh - oos_sh) / abs(is_sh) * 100, 1)

        status = _classify_status(oos_sh, min_oos_months, len(oos_rets))

        all_dates = sorted(monthly.keys())
        is_start  = all_dates[0][:4] if all_dates else "?"
        oos_end   = all_dates[-1][:7] if all_dates else "?"

        cat_economic = meta.get("Cat.Economic", "other").strip().lower()
        category = _CAT_MAP.get(cat_economic, "Other")

        journal_abbr = meta.get("Journal", "").strip()
        journal_full = _JOURNAL_MAP.get(journal_abbr, journal_abbr)

        long_desc = meta.get("LongDescription", acronym).strip()
        authors   = meta.get("Authors", "").strip()
        sample_start = meta.get("SampleStartYear", "").strip()
        sample_end   = meta.get("SampleEndYear", "").strip()
        original_sample = f"{sample_start}–{sample_end}" if sample_start and sample_end else ""

        t_stat_str = meta.get("T-Stat", "").strip()
        try:
            t_stat = float(t_stat_str) if t_stat_str else None
        except ValueError:
            t_stat = None

        detailed_def = meta.get("Detailed Definition", "").strip()

        # Construct a citation-style paper reference
        paper = f"{authors} ({pub_year})"

        slug = acronym.lower().replace("_", "-")

        entry: dict = {
            "id":              slug,
            "slug":            slug,
            "osap_acronym":    acronym,
            "name":            long_desc,
            "long_description": long_desc,
            "description":     detailed_def or long_desc,
            "source":          "osap",
            "category":        category,
            "data_category":   meta.get("Cat.Data", "").strip(),
            "authors":         authors,
            "paper":           paper,
            "journal":         journal_abbr,
            "journal_full":    journal_full,
            "pub_year":        pub_year,
            "original_sample": original_sample,
            "t_stat":          t_stat,
            "is_period":       f"{is_start}–{pub_year - 1}",
            "oos_period":      f"{pub_year}–{oos_end[:4]}",
            "is_return":       is_ret,
            "is_sharpe":       is_sh,
            "is_vol":          is_vol,
            "oos_return":      oos_ret,
            "oos_sharpe":      oos_sh,
            "oos_vol":         oos_vol,
            "decay_pct":       decay,
            "status":          status,
            "monthly_returns": _build_sparkline(monthly) if include_monthly else [],
        }
        results.append(entry)

    # Sort: alive/weakened first, then by OOS Sharpe descending
    _order = {"alive": 0, "weakened": 1, "faded": 2, "dead": 3, "insufficient": 4}
    results.sort(key=lambda r: (_order.get(r["status"], 9), -r["oos_sharpe"]))
    return results


# ---------------------------------------------------------------------------
# French factors (re-stamp with new schema fields)
# ---------------------------------------------------------------------------

def _enrich_french(stats: list[dict]) -> list[dict]:
    """Add new schema fields to the existing French-based entries."""
    for s in stats:
        s.setdefault("slug",            s["id"])
        s.setdefault("osap_acronym",    None)
        s.setdefault("long_description", s["name"])
        s.setdefault("source",          "french")
        s.setdefault("category",        _french_category(s["id"]))
        s.setdefault("data_category",   "Price")
        s.setdefault("authors",         "")
        s.setdefault("journal",         "JF")
        s.setdefault("journal_full",    "Journal of Finance")
        s.setdefault("original_sample", "")
        s.setdefault("t_stat",          None)
    return stats


def _french_category(factor_id: str) -> str:
    return {
        "market":       "Risk",
        "size":         "Size",
        "value":        "Value",
        "momentum":     "Momentum",
        "profitability":"Quality",
        "investment":   "Investment",
    }.get(factor_id, "Other")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Build expanded anomaly-stats.json")
    p.add_argument(
        "--out",
        default=str(
            Path(__file__).parent.parent / "web" / "public" / "anomaly-stats.json"
        ),
        help="Output path for anomaly-stats.json",
    )
    p.add_argument(
        "--no-monthly", action="store_true",
        help="Skip monthly sparkline data (faster, smaller output)",
    )
    p.add_argument(
        "--min-oos", type=int, default=12,
        help="Minimum OOS months required to include an OSAP predictor (default: 12)",
    )
    p.add_argument(
        "--source", choices=["all", "french", "osap"], default="all",
        help="Which data sources to include (default: all)",
    )
    p.add_argument(
        "--clear-cache", action="store_true",
        help="Delete cached OSAP files and re-download",
    )
    args = p.parse_args()

    include_monthly = not args.no_monthly

    if args.clear_cache:
        for fname in ("osap_SignalDoc.csv", "osap_PredictorPortsFull.csv"):
            cached = _cache_dir() / fname
            if cached.exists():
                cached.unlink()
                print(f"Deleted cache: {cached}")

    all_anomalies: list[dict] = []

    # --- French factors ---
    if args.source in ("all", "french"):
        print("Computing French factor stats…")
        french = compute_french_with_fallback(include_monthly)
        french = _enrich_french(french)
        all_anomalies.extend(french)
        print(f"  {len(french)} French factors computed")

    # --- OSAP factors ---
    if args.source in ("all", "osap"):
        french_ids = {a["id"] for a in all_anomalies}
        print("Computing OSAP predictor stats…")
        osap = compute_osap(
            include_monthly=include_monthly,
            min_oos_months=args.min_oos,
            skip_acronyms=french_ids,
        )
        all_anomalies.extend(osap)
        print(f"  {len(osap)} OSAP predictors computed")

    payload = {
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "source":     "Kenneth French Data Library + Open Source Asset Pricing (Chen & Zimmermann 2022)",
        "anomalies":  all_anomalies,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWritten {len(all_anomalies)} anomalies → {out}")

    # Summary table
    alive     = sum(1 for a in all_anomalies if a["status"] == "alive")
    weakened  = sum(1 for a in all_anomalies if a["status"] == "weakened")
    faded     = sum(1 for a in all_anomalies if a["status"] == "faded")
    dead      = sum(1 for a in all_anomalies if a["status"] == "dead")
    insuf     = sum(1 for a in all_anomalies if a["status"] == "insufficient")
    print(f"\nStatus breakdown:")
    print(f"  ✓ alive       {alive:>4}")
    print(f"  ⚠ weakened    {weakened:>4}")
    print(f"  ↓ faded       {faded:>4}")
    print(f"  ✗ dead        {dead:>4}")
    print(f"  ~ insufficient {insuf:>3}")


def compute_french_with_fallback(include_monthly: bool) -> list[dict]:
    """Wrap the existing French compute_all, falling back gracefully."""
    try:
        return _compute_french(include_monthly=include_monthly)
    except Exception as exc:
        print(f"  Warning: French data fetch failed ({exc}); skipping French factors")
        return []


if __name__ == "__main__":
    main()
