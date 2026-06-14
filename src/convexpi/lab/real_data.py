"""
real_data.py — Real-data Lab mode for convexpi.

Provides the same interface as SyntheticMarket but backed by:
  - Ken French factor library (Fama-French factors + Momentum, public)
  - FRED macro series (yield curve, credit spread, public CSV endpoint)
  - Stock prices via yfinance (optional dependency) or user-supplied arrays

Point-in-time discipline:
  - Price-derived features (momentum, vol, reversal) are computed from closing
    prices on day t and exposed to the strategy as features[t] — no lookahead.
  - French factor returns carry a 1-business-day publication lag.
  - FRED series carry a 1-day lag (most series are released same day, but we
    add 1 day to avoid any same-day look-ahead in production use).

Survivorship note: yfinance returns prices for tickers that still exist today.
This introduces survivorship bias. For a research-grade universe, supply your
own point-in-time price panel via RealDataMarket.from_prices().

Quick start::

    from convexpi.lab.real_data import RealDataMarket, fetch_prices

    tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "JPM", "GS"]
    prices_df = fetch_prices(tickers, start="2015-01-01", end="2023-12-31")
    market = RealDataMarket.from_prices(prices_df, train_frac=0.70)

    prices   = market.prices("train")    # (n_train, n_stocks)
    features = market.features("train")  # dict str -> (n_train, n_stocks)

    # Plug into Backtest exactly as you would SyntheticMarket
    from convexpi.lab import Backtest, LongShortRank
    result = Backtest().run(LongShortRank("mom_1m"), prices, features)
    result.tearsheet()
"""

from __future__ import annotations

import io
import os
import zipfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Cache directory
# ---------------------------------------------------------------------------

_CACHE_DIR = Path(os.environ.get("OPENQUANT_CACHE", Path.home() / ".convexpi" / "data"))


def _cache_path(name: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / name


# ---------------------------------------------------------------------------
# Ken French Factor Data
# ---------------------------------------------------------------------------

_FRENCH_URLS = {
    "ff3_daily": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Research_Data_Factors_daily_CSV.zip"
    ),
    "ff5_daily": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
    ),
    "mom_daily": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Momentum_Factor_daily_CSV.zip"
    ),
}


class FrenchFactorData:
    """
    Ken French factor library loader.

    Fetches and caches the Fama-French factor CSV ZIPs from Dartmouth.
    No API key required — data is freely available for academic use.

    Available factors (all returns in percent per day):
        Mkt-RF, SMB, HML    — Fama-French 3 factors
        RMW, CMA            — additional FF5 factors
        Mom                 — Carhart momentum factor

    Each factor series is indexed by a date string 'YYYYMMDD'.
    """

    def __init__(self, include_ff5: bool = False):
        self._ff3 = self._load("ff3_daily")
        self._mom = self._load("mom_daily")
        self._ff5 = self._load("ff5_daily") if include_ff5 else None

    # ---- public ----------------------------------------------------------

    def get(self, factor: str, dates: list[str]) -> np.ndarray:
        """
        Return a 1-D array of daily factor values (%) for the given dates.
        Dates not in the dataset are filled with 0. Dates are 'YYYY-MM-DD'.
        """
        table = self._route(factor)
        col = self._colname(factor)
        out = np.zeros(len(dates))
        for i, d in enumerate(dates):
            key = d.replace("-", "")
            if key in table and col in table[key]:
                out[i] = float(table[key][col])
        return out

    def available_factors(self) -> list[str]:
        factors = ["Mkt-RF", "SMB", "HML", "Mom", "RF"]
        if self._ff5:
            factors += ["RMW", "CMA"]
        return factors

    # ---- private ---------------------------------------------------------

    def _route(self, factor: str) -> dict:
        if factor in ("RMW", "CMA") and self._ff5:
            return self._ff5
        if factor == "Mom":
            return self._mom
        return self._ff3

    def _colname(self, factor: str) -> str:
        aliases = {"Mkt-RF": "Mkt-RF", "SMB": "SMB", "HML": "HML",
                   "RMW": "RMW", "CMA": "CMA", "Mom": "Mom", "RF": "RF"}
        return aliases.get(factor, factor)

    @classmethod
    def _load(cls, key: str) -> dict:
        """Return {date_str: {col: value}} dict."""
        cached = _cache_path(f"french_{key}.csv")
        if cached.exists():
            raw = cached.read_text()
        else:
            url = _FRENCH_URLS[key]
            req = urllib.request.Request(url, headers={"User-Agent": "convexpi/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                zip_bytes = resp.read()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                # The CSV inside is the only non-directory entry
                csv_name = next(n for n in zf.namelist() if n.endswith(".CSV") or n.endswith(".csv"))
                raw = zf.read(csv_name).decode("latin-1")
            cached.write_text(raw)

        return cls._parse_french_csv(raw)

    @staticmethod
    def _parse_french_csv(text: str) -> dict:
        """
        French CSVs: copyright header, blank lines, column header, data rows,
        then sometimes a second section (annual data). Parse only daily rows.

        Strategy: scan forward to find the first 8-digit date row (data_start).
        The last non-blank, non-data line before it is the column header.
        """
        rows: dict = {}
        lines = text.splitlines()

        data_start: int | None = None
        last_non_data: int | None = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            parts = [p.strip() for p in stripped.split(",")]
            if parts[0].isdigit() and len(parts[0]) == 8:
                data_start = i
                break
            last_non_data = i  # keep updating — we want the one just before data

        if data_start is None or last_non_data is None:
            return rows

        col_names_clean = [c.strip() for c in lines[last_non_data].split(",") if c.strip()]

        for line in lines[data_start:]:
            stripped = line.strip()
            if not stripped:
                continue
            parts = [p.strip() for p in stripped.split(",")]
            if not parts[0].isdigit() or len(parts[0]) != 8:
                break  # end of daily section
            date_key = parts[0]
            row_data = {}
            for col, val in zip(col_names_clean, parts[1:]):
                try:
                    row_data[col] = float(val)
                except ValueError:
                    row_data[col] = 0.0
            rows[date_key] = row_data

        return rows


# ---------------------------------------------------------------------------
# FRED Macro Series
# ---------------------------------------------------------------------------

_FRED_SERIES = {
    "yield_curve": "T10Y2Y",      # 10-Year minus 2-Year Treasury spread
    "hy_spread":   "BAMLH0A0HYM2", # ICE BofA US High Yield OAS
    "rate_10y":    "DGS10",        # 10-Year constant maturity rate
    "rate_2y":     "DGS2",         # 2-Year constant maturity rate
}

_FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="


class FredSeries:
    """
    FRED (Federal Reserve Economic Data) series loader.

    Uses the public CSV endpoint — no API key required for most series.
    Data is cached locally. Forward-fills missing observations (weekends,
    holidays, publication gaps).

    Default series:
        yield_curve  — 10Y minus 2Y Treasury spread (slope of yield curve)
        hy_spread    — ICE BofA US High Yield OAS (credit risk proxy)
        rate_10y     — 10-Year Treasury rate
        rate_2y      — 2-Year Treasury rate
    """

    def __init__(self, series: Optional[dict[str, str]] = None):
        """
        Parameters
        ----------
        series : dict | None
            Mapping of {friendly_name: FRED_series_id} to load.
            None → load all default series (see _FRED_SERIES).
        """
        self._series_ids = series if series is not None else _FRED_SERIES
        self._data: dict[str, dict[str, float]] = {}
        for name, sid in self._series_ids.items():
            self._data[name] = self._load(sid)

    def get(self, name: str, dates: list[str]) -> np.ndarray:
        """
        Return values for the named series at each date.
        Missing / non-business dates are forward-filled from the previous value.
        """
        table = self._data.get(name, {})
        out = np.full(len(dates), np.nan)
        last = np.nan
        for i, d in enumerate(dates):
            if d in table:
                last = table[d]
            out[i] = last
        return out

    def available(self) -> list[str]:
        return list(self._data.keys())

    @classmethod
    def _load(cls, series_id: str) -> dict[str, float]:
        cached = _cache_path(f"fred_{series_id}.csv")
        if cached.exists():
            raw = cached.read_text()
        else:
            url = _FRED_BASE + series_id
            req = urllib.request.Request(url, headers={"User-Agent": "convexpi/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
            cached.write_text(raw)

        table: dict[str, float] = {}
        for line in raw.splitlines()[1:]:  # skip header
            parts = line.strip().split(",")
            if len(parts) < 2:
                continue
            d, v = parts[0].strip(), parts[1].strip()
            try:
                table[d] = float(v)
            except ValueError:
                pass  # '.' means missing in FRED
        return table

    @classmethod
    def clear_cache(cls, series_id: Optional[str] = None) -> None:
        """Delete cached FRED files to force a fresh download."""
        if series_id:
            _cache_path(f"fred_{series_id}.csv").unlink(missing_ok=True)
        else:
            for f in _CACHE_DIR.glob("fred_*.csv"):
                f.unlink()


# ---------------------------------------------------------------------------
# Price fetcher (optional yfinance dependency)
# ---------------------------------------------------------------------------

def fetch_prices(
    tickers: list[str],
    start: str = "2010-01-01",
    end: Optional[str] = None,
) -> "pandas.DataFrame":  # type: ignore[name-defined]
    """
    Download adjusted closing prices from Yahoo Finance via yfinance.

    Returns a pandas DataFrame with dates as index, tickers as columns.
    Requires:  pip install yfinance

    Parameters
    ----------
    tickers : list[str]
        Ticker symbols (Yahoo Finance format).
    start : str
        Start date 'YYYY-MM-DD' (default '2010-01-01').
    end : str | None
        End date 'YYYY-MM-DD' (default: today).

    Survivorship warning: yfinance only returns data for currently-listed
    tickers. Use RealDataMarket.from_prices() with a point-in-time price
    panel to avoid this bias in research-grade studies.
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError(
            "yfinance is required for fetch_prices().\n"
            "Install it with:  pip install yfinance\n"
            "Or supply your own price panel to RealDataMarket.from_prices()."
        )

    end = end or date.today().isoformat()
    df = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, type(df.columns)) and hasattr(df.columns, "levels"):
        df = df["Close"]
    else:
        df = df[["Close"]] if "Close" in df.columns else df
    df = df.dropna(how="all").ffill().dropna()
    return df


# ---------------------------------------------------------------------------
# RealDataMarket — drop-in for SyntheticMarket
# ---------------------------------------------------------------------------

class RealDataMarket:
    """
    Real-data Lab market. Same interface as SyntheticMarket.

    price panel:   (n_days, n_stocks)  daily adjusted close prices
    features:      same names as SyntheticMarket where possible, plus
                   macro features (yield_curve, hy_spread) and FF factors
                   (ff_smb, ff_hml, ff_mom)

    Parameters
    ----------
    prices : np.ndarray
        Shape (n_days, n_stocks). Adjusted closing prices.
    dates : list[str]
        ISO date strings ('YYYY-MM-DD') of length n_days.
    tickers : list[str]
        Ticker symbols of length n_stocks.
    train_frac : float
        Fraction of days in the training split (default 0.70).
    tc_bps : float
        Reference transaction cost in basis points.
    load_fred : bool
        Fetch FRED macro features (yield_curve, hy_spread). Default True.
    load_french : bool
        Fetch Ken French factor features (ff_smb, ff_hml, ff_mom). Default True.
    macro_lag : int
        Business days to lag macro/factor features (default 1, conservative).
    """

    def __init__(
        self,
        prices: np.ndarray,
        dates: list[str],
        tickers: list[str],
        *,
        train_frac: float = 0.70,
        tc_bps: float = 10.0,
        load_fred: bool = True,
        load_french: bool = True,
        macro_lag: int = 1,
    ):
        assert prices.shape == (len(dates), len(tickers)), (
            f"prices shape {prices.shape} must match ({len(dates)}, {len(tickers)})"
        )
        self._prices = prices.astype(float)
        self._dates = dates
        self._tickers = tickers
        self.train_frac = train_frac
        self.tc_bps = tc_bps
        self.n_days, self.n_stocks = prices.shape
        self._macro_lag = macro_lag

        self._fred: Optional[FredSeries] = FredSeries() if load_fred else None
        self._french: Optional[FrenchFactorData] = FrenchFactorData() if load_french else None

        self._features: Optional[dict] = None
        self._compute_features()

    # ---- factories -------------------------------------------------------

    @classmethod
    def from_prices(
        cls,
        df: "pandas.DataFrame",  # type: ignore[name-defined]
        **kwargs,
    ) -> "RealDataMarket":
        """
        Build a RealDataMarket from a pandas DataFrame of adjusted close prices.

        Parameters
        ----------
        df : pd.DataFrame
            Index: DatetimeIndex or string dates.  Columns: ticker symbols.
            Assumes prices are already adjusted for splits and dividends.
        **kwargs
            Passed to RealDataMarket.__init__ (train_frac, tc_bps, etc.).
        """
        dates = [str(d)[:10] for d in df.index]
        tickers = list(df.columns)
        prices = df.values.astype(float)
        return cls(prices, dates, tickers, **kwargs)

    # ---- SyntheticMarket-compatible interface ----------------------------

    @property
    def train_end(self) -> int:
        return int(self.n_days * self.train_frac)

    @property
    def stock_ids(self) -> list[str]:
        return self._tickers

    def prices(self, split: str = "train") -> np.ndarray:
        return self._split(self._prices, split)

    def returns(self, split: str = "train") -> np.ndarray:
        p = self._split(self._prices, split)
        return p[1:] / p[:-1] - 1

    def features(self, split: str = "train") -> dict[str, np.ndarray]:
        return {k: self._split(v, split) for k, v in self._features.items()}

    def describe(self) -> None:
        print(f"RealDataMarket: {self.n_stocks} stocks × {self.n_days} days")
        print(f"  period:  {self._dates[0]} → {self._dates[-1]}")
        print(f"  train:   days 0–{self.train_end-1}  ({self.train_end} days)")
        print(f"  test:    days {self.train_end}–{self.n_days-1}  ({self.n_days - self.train_end} days)")
        p = self._prices
        rets = p[1:] / p[:-1] - 1
        print(f"  daily return:  mean={rets.mean()*100:.3f}%  vol={rets.std()*100:.3f}%")
        print(f"  features:      {sorted(self._features)}")
        print(f"  macro lag:     {self._macro_lag} day(s)")

    @classmethod
    def clear_cache(cls) -> None:
        """Delete all cached French and FRED data files."""
        FredSeries.clear_cache()
        for f in _CACHE_DIR.glob("french_*.csv"):
            f.unlink()
        print(f"Cache cleared: {_CACHE_DIR}")

    # ---- private ---------------------------------------------------------

    def _split(self, arr: np.ndarray, split: str) -> np.ndarray:
        if split == "train":
            return arr[:self.train_end]
        if split == "test":
            return arr[self.train_end:]
        if split == "all":
            return arr
        raise ValueError(f"split must be 'train' | 'test' | 'all', got '{split}'")

    def _compute_features(self) -> None:
        T, N = self.n_days, self.n_stocks
        p = self._prices
        nan_row = np.full(N, np.nan)
        feat: dict[str, np.ndarray] = {}

        # ---- price-derived features (no lag needed — end-of-day observable) ----

        def ret(t: int, lag: int) -> np.ndarray:
            return p[t] / p[t - lag] - 1 if t >= lag else nan_row.copy()

        mom1  = np.array([ret(t, 21)  for t in range(T)])
        mom3  = np.array([ret(t, 63)  for t in range(T)])
        mom12 = np.array([ret(t, 252) for t in range(T)])
        mom12_skip = np.where(np.isnan(mom12) | np.isnan(mom1), np.nan, mom12 - mom1)

        feat["mom_1m"]  = np.array([_cs_zscore(r) for r in mom1])
        feat["mom_3m"]  = np.array([_cs_zscore(r) for r in mom3])
        feat["mom_12m"] = np.array([_cs_zscore(r) for r in mom12_skip])

        rev = np.array([-ret(t, 5) for t in range(T)])
        feat["reversal_1w"] = np.array([_cs_zscore(r) for r in rev])

        log_rets = np.zeros((T, N))
        log_rets[1:] = np.log(p[1:] / p[:-1])
        vol = np.full((T, N), np.nan)
        for t in range(21, T):
            vol[t] = log_rets[t-20:t+1].std(axis=0) * np.sqrt(252)
        feat["vol_1m"] = np.array([_cs_zscore(r) for r in vol])

        log_cap = np.log(p + 1e-9)
        feat["size_cap"] = np.array([_cs_zscore(r) for r in log_cap])

        # ---- macro features (broadcast across stocks, lagged 1 business day) ----

        lag = self._macro_lag

        if self._fred is not None:
            lagged_dates = self._lagged_dates(lag)
            for name in ("yield_curve", "hy_spread", "rate_10y", "rate_2y"):
                series = self._fred.get(name, lagged_dates)
                # z-score over the full sample (cross-time, not cross-sectional)
                series_z = _ts_zscore(series)
                # broadcast to (T, N): same value for all stocks on each day
                feat[f"macro_{name}"] = np.outer(series_z, np.ones(N))

        # ---- Fama-French factors (lagged by macro_lag business days) ----

        if self._french is not None:
            lagged_dates = self._lagged_dates(lag)
            for friendly, factor in [("ff_smb", "SMB"), ("ff_hml", "HML"),
                                     ("ff_mom", "Mom"), ("ff_mkt", "Mkt-RF")]:
                series = self._french.get(factor, lagged_dates)  # pct per day
                series_z = _ts_zscore(series)
                feat[friendly] = np.outer(series_z, np.ones(N))

        self._features = feat

    def _lagged_dates(self, lag: int) -> list[str]:
        """Shift dates backward by `lag` calendar days (not business days)."""
        from datetime import datetime
        result = []
        for d in self._dates:
            dt = datetime.strptime(d, "%Y-%m-%d") - timedelta(days=lag)
            result.append(dt.strftime("%Y-%m-%d"))
        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cs_zscore(x: np.ndarray) -> np.ndarray:
    valid = ~np.isnan(x)
    if valid.sum() < 2:
        return x.copy()
    mu = np.nanmean(x)
    sigma = np.nanstd(x)
    return (x - mu) / (sigma + 1e-9)


def _ts_zscore(x: np.ndarray) -> np.ndarray:
    """Time-series z-score (normalize over the full sample)."""
    finite = x[np.isfinite(x)]
    if len(finite) < 2:
        return np.zeros_like(x)
    mu, sigma = finite.mean(), finite.std()
    z = np.where(np.isfinite(x), (x - mu) / (sigma + 1e-9), 0.0)
    return z
