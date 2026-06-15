"""
anomalies.py — Factor anomaly stats from Kenneth French's data library.

Computes in-sample (pre-publication) vs. out-of-sample (post-publication)
Sharpe ratios for canonical equity factor anomalies, using only freely
available data (no CRSP, Compustat, or other licensed sources).

Factors covered:
    Market (Mkt-RF), Size (SMB), Value (HML), Momentum (Mom),
    Profitability (RMW), Investment (CMA)

Methodology:
    Pre-publication period  = full sample the original authors used
    Post-publication period = data from the publication year forward
    Sharpe ratio            = annualized mean / annualized std (daily data)
    Annual return           = 252 × mean daily return

Usage::

    from convexpi.lab.anomalies import compute_all

    stats = compute_all()               # fetches French data, returns list[dict]
    for s in stats:
        print(s["name"], s["is_sharpe"], s["oos_sharpe"], s["decay_pct"])
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

from .real_data import FrenchFactorData, _FRENCH_URLS, _cache_path

# ---------------------------------------------------------------------------
# Anomaly metadata catalogue
# ---------------------------------------------------------------------------

@dataclass
class AnomalySpec:
    id: str
    name: str
    factor: str          # column name in French data
    dataset: str         # which French dataset key to use
    paper: str           # original paper citation
    pub_year: int        # year of publication (first public disclosure)
    description: str
    data_start: int = 1927  # earliest available year in French data


_CATALOGUE: list[AnomalySpec] = [
    AnomalySpec(
        id="market",
        name="Market",
        factor="Mkt-RF",
        dataset="ff3_daily",
        paper="Sharpe (1964), Lintner (1965)",
        pub_year=1964,
        description=(
            "The equity risk premium — excess return of the market over the risk-free rate. "
            "The oldest and most fundamental factor, first formalized in the CAPM. "
            "Investors are compensated for bearing undiversifiable market risk."
        ),
        data_start=1926,
    ),
    AnomalySpec(
        id="size",
        name="Size (SMB)",
        factor="SMB",
        dataset="ff3_daily",
        paper="Banz (1981); Fama & French (1992)",
        pub_year=1981,
        description=(
            "Small-minus-big: small-cap stocks historically earned higher returns than large-caps. "
            "Documented by Banz (1981) using 1926–1975 data. The premium has largely disappeared "
            "after publication, consistent with the McLean-Pontiff (2016) decay hypothesis."
        ),
        data_start=1926,
    ),
    AnomalySpec(
        id="value",
        name="Value (HML)",
        factor="HML",
        dataset="ff3_daily",
        paper="Fama & French (1992, 1993)",
        pub_year=1992,
        description=(
            "High-minus-low book-to-market: value stocks (high B/M) outperformed growth stocks. "
            "Core to the Fama-French three-factor model. The premium has significantly weakened "
            "post-publication, particularly over 2007–2020, though debate continues about whether "
            "the anomaly is risk or mispricing."
        ),
        data_start=1926,
    ),
    AnomalySpec(
        id="momentum",
        name="Momentum (Mom)",
        factor="Mom",
        dataset="mom_daily",
        paper="Jegadeesh & Titman (1993)",
        pub_year=1993,
        description=(
            "Past 12-month winners continue to outperform past losers over the next 3–12 months. "
            "One of the most robust anomalies across asset classes and geographies, yet also the most "
            "crash-prone: the strategy lost ~50% during the 2009 reversal. The premium persists "
            "post-publication but at reduced magnitude."
        ),
        data_start=1927,
    ),
    AnomalySpec(
        id="profitability",
        name="Profitability (RMW)",
        factor="RMW",
        dataset="ff5_daily",
        paper="Fama & French (2015); Novy-Marx (2013)",
        pub_year=2015,
        description=(
            "Robust-minus-weak operating profitability: more profitable firms earn higher returns. "
            "The economic intuition aligns with both risk (profitable firms are harder to distress) "
            "and mispricing (investors underweight cash flow quality). Relatively recent publication; "
            "the post-publication sample is short."
        ),
        data_start=1963,
    ),
    AnomalySpec(
        id="investment",
        name="Investment (CMA)",
        factor="CMA",
        dataset="ff5_daily",
        paper="Fama & French (2015); Titman, Wei & Xie (2004)",
        pub_year=2015,
        description=(
            "Conservative-minus-aggressive investment: firms that invest conservatively "
            "outperform aggressive investors. Related to the q-factor model (Hou, Xue & Zhang 2015). "
            "The premium is theoretically motivated by the investment-value relationship in "
            "production-based asset pricing models."
        ),
        data_start=1963,
    ),
]


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def compute_all(include_monthly: bool = True) -> list[dict]:
    """
    Compute anomaly stats for all factors in the catalogue.

    Parameters
    ----------
    include_monthly : bool
        If True, include a monthly cumulative return series for sparklines.
        Requires the French monthly data (separate download from daily).

    Returns
    -------
    list[dict]
        One dict per anomaly. Keys: id, name, factor, paper, pub_year,
        description, is_period, oos_period, is_return, is_sharpe, is_vol,
        oos_return, oos_sharpe, oos_vol, decay_pct, status, monthly_returns.
    """
    # Load French daily data (uses cached files if available)
    ff3  = FrenchFactorData._load("ff3_daily")
    ff5  = FrenchFactorData._load("ff5_daily")
    mom  = FrenchFactorData._load("mom_daily")

    datasets = {"ff3_daily": ff3, "ff5_daily": ff5, "mom_daily": mom}

    # Load monthly data for sparklines (separate download)
    monthly_data: dict = {}
    if include_monthly:
        monthly_data = _load_monthly_factors()

    results = []
    for spec in _CATALOGUE:
        table = datasets[spec.dataset]
        r = compute_factor_stats(spec, table)
        if include_monthly and spec.factor in monthly_data:
            r["monthly_returns"] = _monthly_cumulative(
                spec.factor, monthly_data, spec.data_start
            )
        else:
            r["monthly_returns"] = []
        results.append(r)

    return results


def compute_factor_stats(spec: AnomalySpec, table: dict) -> dict:
    """Compute IS/OOS stats for one factor using daily data."""
    # Extract all daily returns sorted chronologically
    dates_vals: list[tuple[str, float]] = []
    col = spec.factor
    for date_key, row in table.items():
        if col in row:
            dates_vals.append((date_key, row[col]))
    dates_vals.sort(key=lambda x: x[0])

    pub_key = f"{spec.pub_year}0101"

    is_rets = np.array([v / 100 for d, v in dates_vals if d < pub_key])
    oos_rets = np.array([v / 100 for d, v in dates_vals if d >= pub_key])

    def stats(r: np.ndarray) -> tuple[float, float, float]:
        if len(r) < 20:
            return 0.0, 0.0, 0.0
        ann_ret = float(r.mean() * 252)
        ann_vol = float(r.std() * math.sqrt(252))
        sharpe  = ann_ret / ann_vol if ann_vol > 1e-9 else 0.0
        return round(ann_ret * 100, 2), round(sharpe, 3), round(ann_vol * 100, 2)

    is_ret, is_sh, is_vol   = stats(is_rets)
    oos_ret, oos_sh, oos_vol = stats(oos_rets)

    decay = 0.0
    if abs(is_sh) > 0.05:
        decay = round((is_sh - oos_sh) / abs(is_sh) * 100, 1)

    if oos_sh > 0.5:
        status = "alive"
    elif oos_sh > 0.2:
        status = "weakened"
    elif oos_sh > 0:
        status = "faded"
    else:
        status = "dead"

    is_start = str(spec.data_start)
    is_end   = str(spec.pub_year - 1)
    oos_start = str(spec.pub_year)
    oos_end   = dates_vals[-1][0][:4] if dates_vals else "?"

    return {
        "id":          spec.id,
        "name":        spec.name,
        "factor":      spec.factor,
        "paper":       spec.paper,
        "pub_year":    spec.pub_year,
        "description": spec.description,
        "is_period":   f"{is_start}–{is_end}",
        "oos_period":  f"{oos_start}–{oos_end}",
        "is_return":   is_ret,
        "is_sharpe":   is_sh,
        "is_vol":      is_vol,
        "oos_return":  oos_ret,
        "oos_sharpe":  oos_sh,
        "oos_vol":     oos_vol,
        "decay_pct":   decay,
        "status":      status,
    }


# ---------------------------------------------------------------------------
# Monthly data helpers (for sparklines)
# ---------------------------------------------------------------------------

_FRENCH_MONTHLY_URLS = {
    "ff3_monthly": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Research_Data_Factors_CSV.zip"
    ),
    "ff5_monthly": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Research_Data_5_Factors_2x3_CSV.zip"
    ),
    "mom_monthly": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Momentum_Factor_CSV.zip"
    ),
}


def _parse_french_monthly_csv(text: str) -> dict:
    """Parse French monthly CSV (6-digit YYYYMM dates) into {YYYYMM: {col: val}}."""
    rows: dict = {}
    lines = text.splitlines()
    header: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        parts = [p.strip() for p in stripped.split(",")]
        if parts[0].isdigit() and len(parts[0]) == 6:
            if not header:
                continue  # no header yet, skip
            row_data = {}
            for col, val in zip(header, parts[1:]):
                try:
                    row_data[col] = float(val)
                except ValueError:
                    pass
            rows[parts[0]] = row_data
        else:
            # Candidate header: non-blank columns after the first empty field
            cols = [c for c in parts if c]
            if cols:
                header = cols
    return rows


def _load_monthly_factors() -> dict[str, dict[str, float]]:
    """Load all monthly French factors into {factor_col: {YYYYMM: return_pct}}."""
    import io
    import zipfile
    import urllib.request

    result: dict[str, dict[str, float]] = {}
    for key, url in _FRENCH_MONTHLY_URLS.items():
        cached = _cache_path(f"french_{key}.csv")
        if cached.exists():
            raw = cached.read_text()
        else:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "convexpi/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    zip_bytes = resp.read()
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    csv_name = next(n for n in zf.namelist()
                                    if n.upper().endswith(".CSV"))
                    raw = zf.read(csv_name).decode("latin-1")
                cached.write_text(raw)
            except Exception:
                continue

        parsed = _parse_french_monthly_csv(raw)
        for date_key, row in parsed.items():
            for col, val in row.items():
                result.setdefault(col, {})[date_key] = val

    return result


def _monthly_cumulative(
    factor: str,
    monthly_data: dict,
    start_year: int,
) -> list[dict]:
    """
    Build a monthly cumulative return series for sparklines.
    Returns [{date, cum_ret}] where cum_ret is the fraction return
    since the series start (e.g. 0.5 = +50%).
    Limits to the last 40 years to keep the JSON small.
    """
    table = monthly_data.get(factor, {})
    if not table:
        return []

    cutoff = max(str(start_year), str(max(int(k[:4]) for k in table) - 40)) + "01"
    pairs = sorted(
        [(k, v / 100) for k, v in table.items() if k >= cutoff],
        key=lambda x: x[0],
    )
    if not pairs:
        return []

    cum = 1.0
    series = []
    for date_key, r in pairs:
        cum *= (1 + r)
        year, month = int(date_key[:4]), int(date_key[4:])
        series.append({
            "date":    f"{year}-{month:02d}",
            "cum_ret": round(cum - 1, 4),
        })
    return series
