"""
strategies.py — Pre-canned strategy library for the ConvexPi Lab.

Every strategy here is a drop-in for Backtest.run() and follows the same
point-in-time contract as the base Strategy class:

    on_day(day, features, prices, portfolio) → weights (n_stocks,)

Strategies are organized by factor category with references to the original
academic papers. Use them as baselines, teaching examples, or competition
benchmarks.

Quick start::

    from convexpi.lab import SyntheticMarket, Backtest
    from convexpi.lab.strategies import STRATEGIES, compare

    market = SyntheticMarket(seed=42)
    results = compare(STRATEGIES, market, split="test")
    print(results[["sharpe","annual_return","max_drawdown"]].sort_values("sharpe", ascending=False))

Available strategies
--------------------
Momentum
    CrossSectionalMomentum  — Jegadeesh & Titman (1993) 12-1 momentum
    ShortTermReversal       — Jegadeesh (1990) 1-week contrarian
    TimeSeriesMomentum      — Moskowitz, Ooi & Pedersen (2012) absolute momentum

Value
    ValueTilt               — Fama & French (1992) long high B/M, short low B/M

Quality
    QualityTilt             — Novy-Marx (2013) long high-ROE stocks
    BettingAgainstBeta      — Frazzini & Pedersen (2014) long low-vol, short high-vol

Size
    SizePremium             — Banz (1981) long small-cap, short large-cap

Multi-factor
    FamaFrench3             — SMB + HML composite (Fama & French 1993)
    MultiFactorRank         — rank-sum blend of configurable signals
    ICWeightedComposite     — rolling IC-weighted signal combination

Risk-based
    InverseVolatilityWeight — risk parity: weight by 1/realized vol
    MinimumVarianceScreen   — long lowest-vol quintile only

Conditional / macro-aware
    TrendFilter             — apply inner strategy only when market trend is up
    DualMomentum            — Antonacci (2012): cross-sectional + absolute momentum gate
    MacroCyclical           — tilt between momentum and value using yield curve signal
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from .backtest import Strategy, Backtest, BacktestResult, EqualWeight


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ls_weights(
    signal: np.ndarray,
    quintile_frac: float = 0.20,
    long_only: bool = False,
) -> np.ndarray:
    """Long top quintile, short bottom quintile (or long-only version)."""
    valid = ~np.isnan(signal)
    if valid.sum() < 10:
        return np.zeros(len(signal))
    lo = np.nanpercentile(signal, quintile_frac * 100)
    hi = np.nanpercentile(signal, (1 - quintile_frac) * 100)
    w = np.zeros(len(signal))
    w[signal >= hi] = 1.0
    if not long_only:
        w[signal <= lo] = -1.0
    total = np.abs(w).sum()
    return w / total if total > 0 else w


def _zscore(x: np.ndarray) -> np.ndarray:
    valid = ~np.isnan(x)
    if valid.sum() < 2:
        return np.zeros_like(x)
    mu, sigma = np.nanmean(x), np.nanstd(x)
    return np.where(valid, (x - mu) / (sigma + 1e-9), 0.0)


# ---------------------------------------------------------------------------
# ── MOMENTUM ────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class CrossSectionalMomentum(Strategy):
    """
    Cross-sectional 12-1 momentum: long past 12-month winners (skipping the
    most recent month), short past 12-month losers.

    Reference: Jegadeesh & Titman (1993). "Returns to Buying Winners and
    Selling Losers." Journal of Finance.

    The skip-1-month convention avoids short-term reversal contamination.
    Uses the ``mom_12m`` feature which already applies the skip.

    Parameters
    ----------
    quintile_frac : float
        Fraction of stocks in each long/short leg (default 0.20 = top/bottom quintile).
    signal : str
        Feature to sort on (default 'mom_12m'; try 'mom_3m' for intermediate horizon).
    """

    def __init__(self, quintile_frac: float = 0.20, signal: str = "mom_12m"):
        self.quintile_frac = quintile_frac
        self.signal = signal

    def on_day(self, day, features, prices, portfolio):
        sig = features.get(self.signal, np.zeros(len(prices)))
        return _ls_weights(sig, self.quintile_frac)


class ShortTermReversal(Strategy):
    """
    Short-term reversal: long past 1-week losers, short past 1-week winners.

    Reference: Jegadeesh (1990). "Evidence of Predictable Behavior of Security
    Returns." Journal of Finance.

    Mean-reversion at the weekly horizon; the mirror image of momentum.
    The ``reversal_1w`` feature is already sign-flipped so high values = losers.
    """

    def __init__(self, quintile_frac: float = 0.20):
        self.quintile_frac = quintile_frac

    def on_day(self, day, features, prices, portfolio):
        sig = features.get("reversal_1w", np.zeros(len(prices)))
        return _ls_weights(sig, self.quintile_frac)


class TimeSeriesMomentum(Strategy):
    """
    Time-series (absolute) momentum: long a stock if its trailing return is
    positive, short if negative. Size the position by signal magnitude.

    Reference: Moskowitz, Ooi & Pedersen (2012). "Time Series Momentum."
    Journal of Financial Economics.

    Unlike cross-sectional momentum this can be net long or net short overall,
    depending on broad market direction.

    Parameters
    ----------
    lookback : str
        Which feature to use as the trailing return signal ('mom_12m', 'mom_3m',
        or 'mom_1m'). Default 'mom_12m'.
    scale : float
        Each stock's weight = scale × sign(signal). Default 1/n_stocks.
    """

    def __init__(self, lookback: str = "mom_12m", scale: Optional[float] = None):
        self.lookback = lookback
        self.scale = scale

    def on_day(self, day, features, prices, portfolio):
        sig = features.get(self.lookback, np.zeros(len(prices)))
        valid = ~np.isnan(sig)
        n = valid.sum()
        if n == 0:
            return np.zeros(len(prices))
        scale = self.scale if self.scale is not None else (1.0 / n)
        w = np.where(valid, np.sign(sig) * scale, 0.0)
        total = np.abs(w).sum()
        return w / total if total > 0 else w


# ---------------------------------------------------------------------------
# ── VALUE ───────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class ValueTilt(Strategy):
    """
    Value: long high book-to-market (cheap) stocks, short low B/M (expensive).

    Reference: Fama & French (1992, 1993). "The Cross-Section of Expected
    Stock Returns." Journal of Finance.

    The ``val_bm`` feature is a cross-sectionally z-scored book-to-market ratio
    updated quarterly. High values = value stocks; low values = growth stocks.

    Parameters
    ----------
    quintile_frac : float
        Fraction of stocks in each leg (default 0.20).
    long_only : bool
        If True, only go long value stocks (no short growth leg).
    """

    def __init__(self, quintile_frac: float = 0.20, long_only: bool = False):
        self.quintile_frac = quintile_frac
        self.long_only = long_only

    def on_day(self, day, features, prices, portfolio):
        sig = features.get("val_bm", np.zeros(len(prices)))
        return _ls_weights(sig, self.quintile_frac, long_only=self.long_only)


# ---------------------------------------------------------------------------
# ── QUALITY ─────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class QualityTilt(Strategy):
    """
    Quality / profitability: long high-ROE stocks, optionally short low-ROE.

    Reference: Novy-Marx (2013). "The Other Side of Value: The Gross
    Profitability Premium." Journal of Financial Economics.

    ROE is a slow-moving annual signal (``qual_roe``), so this strategy has
    low turnover and relatively low transaction costs.

    Parameters
    ----------
    quintile_frac : float
        Fraction of stocks in each leg.
    long_only : bool
        Long-only quality screen (common in institutional mandates).
    """

    def __init__(self, quintile_frac: float = 0.20, long_only: bool = False):
        self.quintile_frac = quintile_frac
        self.long_only = long_only

    def on_day(self, day, features, prices, portfolio):
        sig = features.get("qual_roe", np.zeros(len(prices)))
        return _ls_weights(sig, self.quintile_frac, long_only=self.long_only)


class BettingAgainstBeta(Strategy):
    """
    Betting-against-beta (BAB): long low-volatility stocks, short high-volatility.

    Reference: Frazzini & Pedersen (2014). "Betting Against Beta."
    Journal of Financial Economics.

    The idea: constrained investors (who cannot lever up) overpay for
    high-beta/high-vol stocks. Going long the safe stocks and short the
    risky ones earns a premium.

    Implemented here using realized 1-month volatility (``vol_1m``) as a
    beta proxy. Low vol → long; high vol → short.

    Parameters
    ----------
    quintile_frac : float
        Fraction of stocks in each leg.
    """

    def __init__(self, quintile_frac: float = 0.20):
        self.quintile_frac = quintile_frac

    def on_day(self, day, features, prices, portfolio):
        vol = features.get("vol_1m", np.zeros(len(prices)))
        # Invert: low vol = high BAB signal
        sig = -vol
        return _ls_weights(sig, self.quintile_frac)


# ---------------------------------------------------------------------------
# ── SIZE ────────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class SizePremium(Strategy):
    """
    Size: long small-cap stocks, short large-cap stocks.

    Reference: Banz (1981). "The Relationship Between Return and Market Value
    of Common Stocks." Journal of Financial Economics.

    The size premium is one of the most-studied anomalies and has largely
    disappeared post-publication (see /anomalies). Included here as a
    cautionary tale.

    Uses ``size_cap`` (log market cap, cross-sectionally z-scored).
    Long low-size-cap (small), short high-size-cap (large).
    """

    def __init__(self, quintile_frac: float = 0.20):
        self.quintile_frac = quintile_frac

    def on_day(self, day, features, prices, portfolio):
        size = features.get("size_cap", np.zeros(len(prices)))
        sig = -size  # invert: small = high signal
        return _ls_weights(sig, self.quintile_frac)


# ---------------------------------------------------------------------------
# ── MULTI-FACTOR ─────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class FamaFrench3(Strategy):
    """
    Simplified Fama-French 3-factor tilt: combine value (HML) and size (SMB)
    into a composite long-short portfolio, market-neutral by construction.

    Reference: Fama & French (1993). "Common Risk Factors in the Returns on
    Stocks and Bonds." Journal of Financial Economics.

    Equal-weights the value tilt and size premium signals. Does not add a
    separate market factor (the market return is the benchmark).
    """

    def __init__(self, quintile_frac: float = 0.20, value_weight: float = 0.5):
        self.quintile_frac = quintile_frac
        self.value_weight = value_weight
        self._size_weight = 1 - value_weight

    def on_day(self, day, features, prices, portfolio):
        n = len(prices)
        val  = features.get("val_bm",  np.zeros(n))
        size = features.get("size_cap", np.zeros(n))
        small = -size  # long small
        composite = self.value_weight * _zscore(val) + self._size_weight * _zscore(small)
        return _ls_weights(composite, self.quintile_frac)


class MultiFactorRank(Strategy):
    """
    Rank-sum multi-factor composite: rank each signal cross-sectionally,
    sum the ranks, then sort on the composite rank.

    Rank-sum is more robust to outliers than score-weighting and treats
    each factor symmetrically regardless of its distribution.

    Reference: Asness, Frazzini & Pedersen (2019). "Quality Minus Junk."
    Review of Accounting Studies.

    Parameters
    ----------
    signals : list[str]
        Feature names to include (default: mom + value + quality).
    weights : list[float] | None
        Per-signal weights. None → equal weight.
    quintile_frac : float
        Fraction of stocks in each leg.
    invert : list[str]
        Signals where HIGH value → SHORT (e.g. 'vol_1m', 'size_cap').
    """

    def __init__(
        self,
        signals: Optional[list[str]] = None,
        weights: Optional[list[float]] = None,
        quintile_frac: float = 0.20,
        invert: Optional[list[str]] = None,
    ):
        self.signals  = signals or ["mom_12m", "val_bm", "qual_roe"]
        self.weights  = weights or [1.0] * len(self.signals)
        self.quintile_frac = quintile_frac
        self.invert   = set(invert or [])

    def on_day(self, day, features, prices, portfolio):
        n = len(prices)
        composite = np.zeros(n)
        for fname, w in zip(self.signals, self.weights):
            sig = features.get(fname, np.full(n, np.nan))
            z   = _zscore(sig)
            if fname in self.invert:
                z = -z
            composite += w * z
        total_w = sum(abs(w) for w in self.weights)
        composite /= (total_w + 1e-9)
        return _ls_weights(composite, self.quintile_frac)


class ICWeightedComposite(Strategy):
    """
    Rolling information-coefficient (IC) weighted signal combination.

    Each period's signal weights are proportional to the IC (rank correlation
    between last period's signal and this period's return) computed over a
    rolling window. Signals with higher recent predictive power get more weight.

    Reference: Qian, Hua & Sorensen (2007). "Quantitative Equity Portfolio
    Management." Chapman & Hall.

    Parameters
    ----------
    signals : list[str]
        Feature names to blend.
    ic_window : int
        Number of periods to estimate IC (default 60).
    quintile_frac : float
        Fraction of stocks in each leg.
    min_weight : float
        Minimum weight per signal (prevents zero-weighting). Default 0.05.
    """

    def __init__(
        self,
        signals: Optional[list[str]] = None,
        ic_window: int = 60,
        quintile_frac: float = 0.20,
        min_weight: float = 0.05,
    ):
        self.signals      = signals or ["mom_12m", "val_bm", "qual_roe"]
        self.ic_window    = ic_window
        self.quintile_frac = quintile_frac
        self.min_weight   = min_weight
        self._ic_history: dict[str, list[float]] = {s: [] for s in self.signals}
        self._last_signals: dict[str, np.ndarray] = {}
        self._last_prices: Optional[np.ndarray] = None

    def on_day(self, day, features, prices, portfolio):
        n = len(prices)

        # Update IC history from last period
        if self._last_prices is not None:
            realized = prices / self._last_prices - 1
            for fname in self.signals:
                prev = self._last_signals.get(fname)
                if prev is not None:
                    ic = float(_rank_corr(prev, realized))
                    self._ic_history[fname].append(ic)
                    if len(self._ic_history[fname]) > self.ic_window:
                        self._ic_history[fname].pop(0)

        # Compute weights from recent ICs
        ic_means = {}
        for fname in self.signals:
            hist = self._ic_history[fname]
            ic_means[fname] = float(np.mean(hist)) if hist else 0.0

        raw_w = {f: max(self.min_weight, ic_means[f]) for f in self.signals}
        total = sum(raw_w.values())
        norm_w = {f: v / total for f, v in raw_w.items()}

        composite = np.zeros(n)
        for fname, w in norm_w.items():
            sig = features.get(fname, np.full(n, np.nan))
            composite += w * _zscore(sig)

        self._last_signals = {f: features.get(f, np.full(n, np.nan)).copy()
                              for f in self.signals}
        self._last_prices = prices.copy()

        return _ls_weights(composite, self.quintile_frac)


def _rank_corr(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation ignoring NaNs."""
    valid = ~(np.isnan(x) | np.isnan(y))
    if valid.sum() < 5:
        return 0.0
    xv, yv = x[valid], y[valid]
    xr = xv.argsort().argsort().astype(float)
    yr = yv.argsort().argsort().astype(float)
    return float(np.corrcoef(xr, yr)[0, 1])


# ---------------------------------------------------------------------------
# ── RISK-BASED ───────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class InverseVolatilityWeight(Strategy):
    """
    Risk parity (stock level): weight each stock proportional to 1/volatility.

    Each stock contributes equally to portfolio volatility rather than being
    equally capital-weighted. Long-only by default.

    Reference: Qian (2005). "Risk Parity Portfolios." PanAgora Asset Mgmt.

    Parameters
    ----------
    vol_feature : str
        Feature containing realized volatility (default 'vol_1m').
    long_only : bool
        If False, also shorts the highest-vol stocks (BAB-style).
    quintile_frac : float
        Used only when long_only=False to define the short leg.
    """

    def __init__(
        self,
        vol_feature: str = "vol_1m",
        long_only: bool = True,
        quintile_frac: float = 0.20,
    ):
        self.vol_feature = vol_feature
        self.long_only = long_only
        self.quintile_frac = quintile_frac

    def on_day(self, day, features, prices, portfolio):
        vol = features.get(self.vol_feature, np.zeros(len(prices)))
        valid = ~np.isnan(vol) & (vol > 0)
        if valid.sum() < 2:
            return np.zeros(len(prices))
        w = np.zeros(len(prices))
        w[valid] = 1.0 / vol[valid]
        if not self.long_only:
            # Long the low-vol quintile, short the high-vol quintile
            w_ls = _ls_weights(-vol, self.quintile_frac)  # invert: low vol = long
            total = np.abs(w_ls).sum()
            return w_ls / total if total > 0 else w_ls
        total = w.sum()
        return w / total if total > 0 else w


class MinimumVarianceScreen(Strategy):
    """
    Minimum variance (screen): long-only portfolio of the lowest-vol stocks.

    A simplified version of minimum variance optimization that avoids the
    need to estimate a full covariance matrix. Selects the lowest-vol
    quintile and equal-weights them.

    Reference: Clarke, de Silva & Thorley (2006). "Minimum-Variance Portfolios
    in the U.S. Equity Market." Journal of Portfolio Management.
    """

    def __init__(self, quintile_frac: float = 0.20, vol_feature: str = "vol_1m"):
        self.quintile_frac = quintile_frac
        self.vol_feature = vol_feature

    def on_day(self, day, features, prices, portfolio):
        vol = features.get(self.vol_feature, np.zeros(len(prices)))
        valid = ~np.isnan(vol)
        if valid.sum() < 5:
            return np.zeros(len(prices))
        threshold = np.nanpercentile(vol, self.quintile_frac * 100)
        w = np.where(valid & (vol <= threshold), 1.0, 0.0)
        total = w.sum()
        return w / total if total > 0 else w


# ---------------------------------------------------------------------------
# ── CONDITIONAL / MACRO-AWARE ────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TrendFilter(Strategy):
    """
    Market trend filter: apply an inner strategy only when the market trend
    is positive; otherwise hold cash (or go flat).

    Reference: Asness, Frazzini & Pedersen (2013). "Momentum in the Cross-
    Section of Future Stock Returns." (also Faber 2007 for trend timing.)

    Parameters
    ----------
    inner : Strategy
        The cross-sectional strategy to apply when trend is up.
    trend_signal : str
        Feature to use as a market trend indicator. If the feature is
        a macro/market-wide signal (same value repeated across stocks),
        the first stock's value is used. Default 'mom_12m'; with
        RealDataMarket use 'ff_mkt' or 'macro_yield_curve'.
    flat_on_down : bool
        If True, go flat (cash) when trend is negative. If False, reverse
        the inner strategy (inverse momentum).
    """

    def __init__(
        self,
        inner: Optional[Strategy] = None,
        trend_signal: str = "mom_12m",
        flat_on_down: bool = True,
    ):
        self.inner = inner or CrossSectionalMomentum()
        self.trend_signal = trend_signal
        self.flat_on_down = flat_on_down

    def on_day(self, day, features, prices, portfolio):
        sig = features.get(self.trend_signal, np.zeros(len(prices)))
        valid = sig[np.isfinite(sig)]
        trend = float(valid.mean()) if len(valid) > 0 else 0.0
        if trend > 0:
            return self.inner.on_day(day, features, prices, portfolio)
        if self.flat_on_down:
            return np.zeros(len(prices))
        # Invert the inner strategy
        return -self.inner.on_day(day, features, prices, portfolio)


class DualMomentum(Strategy):
    """
    Dual momentum: cross-sectional momentum gated by absolute momentum.

    Only takes cross-sectional positions in a stock if its absolute trailing
    return is positive (absolute momentum filter). This reduces the crash risk
    of pure cross-sectional momentum by avoiding stocks in absolute downtrends.

    Reference: Antonacci (2012). "Risk Premia Harvesting Through Dual Momentum."
    Portfolio Management Consultants.

    Parameters
    ----------
    cs_signal : str
        Cross-sectional ranking signal (default 'mom_12m').
    abs_signal : str
        Absolute momentum signal (default 'mom_12m'). A stock passes the
        absolute filter if its value is positive.
    quintile_frac : float
        Cross-sectional long/short fraction.
    """

    def __init__(
        self,
        cs_signal: str = "mom_12m",
        abs_signal: str = "mom_12m",
        quintile_frac: float = 0.20,
    ):
        self.cs_signal = cs_signal
        self.abs_signal = abs_signal
        self.quintile_frac = quintile_frac

    def on_day(self, day, features, prices, portfolio):
        cs  = features.get(self.cs_signal,  np.zeros(len(prices)))
        abs_mom = features.get(self.abs_signal, np.zeros(len(prices)))
        # Only rank stocks with positive absolute momentum
        filtered = np.where(abs_mom > 0, cs, np.nan)
        return _ls_weights(filtered, self.quintile_frac, long_only=True)


class MacroCyclical(Strategy):
    """
    Macro-cyclical rotation: tilt toward momentum in risk-on environments
    and toward value/quality in risk-off environments, using the yield curve
    as a regime indicator.

    A positive yield curve (long rates > short rates) signals expansion →
    momentum outperforms. An inverted or flat yield curve signals contraction
    → value/quality is more defensive.

    Requires RealDataMarket features 'macro_yield_curve', 'mom_12m', 'val_bm',
    'qual_roe'. Falls back to equal-weight momentum+value if macro features
    are unavailable.

    Reference: Barberis & Shleifer (2003). "Style Investing." Journal of
    Financial Economics. Also Ilmanen (2011). "Expected Returns."
    """

    def __init__(self, quintile_frac: float = 0.20):
        self.quintile_frac = quintile_frac

    def on_day(self, day, features, prices, portfolio):
        n = len(prices)
        yc = features.get("macro_yield_curve", None)

        mom = features.get("mom_12m", np.zeros(n))
        val = features.get("val_bm",  np.zeros(n))
        qua = features.get("qual_roe", np.zeros(n))

        if yc is None:
            # Fallback: equal-weight momentum + value
            composite = 0.5 * _zscore(mom) + 0.5 * _zscore(val)
            return _ls_weights(composite, self.quintile_frac)

        # yc is broadcast (same value per stock); use the first element
        yield_curve = float(np.nanmean(yc))

        if yield_curve > 0.5:
            # Steepening yield curve → risk-on → momentum
            return _ls_weights(_zscore(mom), self.quintile_frac)
        elif yield_curve < -0.5:
            # Inverted → risk-off → quality/value blend
            composite = 0.5 * _zscore(val) + 0.5 * _zscore(qua)
            return _ls_weights(composite, self.quintile_frac)
        else:
            # Flat → diversify across all three
            composite = (_zscore(mom) + _zscore(val) + _zscore(qua)) / 3
            return _ls_weights(composite, self.quintile_frac)


# ---------------------------------------------------------------------------
# Registry and comparison utility
# ---------------------------------------------------------------------------

STRATEGIES: dict[str, Strategy] = {
    # Baselines (from backtest.py)
    "equal_weight":          EqualWeight(),
    # Momentum
    "momentum_12_1":         CrossSectionalMomentum(),
    "momentum_3m":           CrossSectionalMomentum(signal="mom_3m"),
    "momentum_1m":           CrossSectionalMomentum(signal="mom_1m"),
    "reversal_1w":           ShortTermReversal(),
    "ts_momentum":           TimeSeriesMomentum(),
    # Value
    "value_bm":              ValueTilt(),
    "value_bm_long_only":    ValueTilt(long_only=True),
    # Quality
    "quality_roe":           QualityTilt(),
    "betting_against_beta":  BettingAgainstBeta(),
    # Size
    "size_premium":          SizePremium(),
    # Multi-factor
    "fama_french_3":         FamaFrench3(),
    "multi_factor_rank":     MultiFactorRank(),
    "ic_weighted":           ICWeightedComposite(),
    # Risk-based
    "inv_vol":               InverseVolatilityWeight(),
    "min_variance":          MinimumVarianceScreen(),
    # Conditional
    "trend_filter":          TrendFilter(),
    "dual_momentum":         DualMomentum(),
    "macro_cyclical":        MacroCyclical(),
}


def compare(
    strategies: dict[str, Strategy] | None = None,
    market=None,
    split: str = "test",
    warmup_days: int = 252,
    tc_bps: float = 10.0,
) -> "pandas.DataFrame":  # type: ignore[name-defined]
    """
    Run multiple strategies on the same market split and return a comparison table.

    Parameters
    ----------
    strategies : dict[str, Strategy] | None
        Mapping of name → strategy. None → use STRATEGIES registry.
    market : SyntheticMarket | RealDataMarket
        Market to evaluate on. Required.
    split : str
        'train' | 'test' | 'all' (default 'test').
    warmup_days : int
        Warmup passed to Backtest (default 252).
    tc_bps : float
        One-way transaction costs in basis points (default 10).

    Returns
    -------
    pd.DataFrame
        Columns: sharpe, annual_return, annual_vol, max_drawdown, calmar,
                 annual_turnover, hit_rate. Indexed by strategy name.

    Example
    -------
    >>> from convexpi.lab import SyntheticMarket
    >>> from convexpi.lab.strategies import compare
    >>> market = SyntheticMarket(seed=42)
    >>> df = compare(market=market)
    >>> print(df.sort_values("sharpe", ascending=False).head())
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("compare() requires pandas: pip install pandas")

    if market is None:
        raise ValueError("market is required")

    strats = strategies if strategies is not None else STRATEGIES
    prices   = market.prices(split)
    features = market.features(split)
    bt = Backtest(tc_bps=tc_bps, warmup_days=warmup_days)

    rows = {}
    for name, strategy in strats.items():
        # Reset any stateful strategies
        if hasattr(strategy, "_ic_history"):
            strategy._ic_history = {s: [] for s in strategy.signals}
            strategy._last_signals = {}
            strategy._last_prices = None

        try:
            result: BacktestResult = bt.run(strategy, prices, features)
            rows[name] = {
                "sharpe":          round(result.sharpe, 3),
                "annual_return":   round(result.annualized_return * 100, 2),
                "annual_vol":      round(result.annualized_vol * 100, 2),
                "max_drawdown":    round(result.max_drawdown * 100, 2),
                "calmar":          round(result.calmar, 3),
                "annual_turnover": round(result.turnover_annual, 1),
                "hit_rate":        round(result.hit_rate * 100, 1),
            }
        except Exception as e:
            rows[name] = {col: float("nan") for col in
                         ["sharpe","annual_return","annual_vol",
                          "max_drawdown","calmar","annual_turnover","hit_rate"]}

    df = pd.DataFrame(rows).T
    df.index.name = "strategy"
    return df
