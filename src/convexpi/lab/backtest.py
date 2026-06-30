"""
lab.py — Daily-data backtesting harness for the Lab.

Students write a Strategy subclass (one method), hand it to Backtest.run(),
and get a BacktestResult with Sharpe, max drawdown, turnover, and a printable
tearsheet. The same interface works on synthetic data (SyntheticMarket) and
real data (when the open-data bundle lands in Lab Mode 2).

Quick start:
    from synth import SyntheticMarket
    from lab import Backtest, Strategy
    import numpy as np

    market = SyntheticMarket(seed=42)
    prices   = market.prices("train")
    features = market.features("train")

    class MyMomentum(Strategy):
        def on_day(self, day, features, prices, portfolio):
            signal = features["mom_1m"]          # (n_stocks,) z-scored
            n = len(signal)
            weights = np.zeros(n)
            thresh = np.nanpercentile(signal, [20, 80])
            weights[signal > thresh[1]] =  1.0   # long top quintile
            weights[signal < thresh[0]] = -1.0   # short bottom quintile
            weights /= np.abs(weights).sum()      # normalize to $1 L/S
            return weights

    result = Backtest().run(MyMomentum(), prices, features)
    result.tearsheet()

Point-in-time discipline (no lookahead):
    on_day(day=t) receives features[t] and prices[t] — end-of-day data.
    The strategy's returned weights are applied to returns from day t to t+1.
    No future information enters on_day.

Strategy contract:
    - Return an array of shape (n_stocks,).
    - Positive = long, negative = short, zero = flat.
    - If |weights|.sum() > 1.0 the backtest normalizes it (warning printed).
    - Weights that remain 0 throughout earn the risk-free rate of 0.
    - Exceptions in on_day are caught; the previous weights are kept.
"""

from __future__ import annotations
import math
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Strategy base class
# ---------------------------------------------------------------------------

class Strategy:
    """
    Override on_day to implement your strategy.

    Parameters passed each rebalance day
    ─────────────────────────────────────
    day       : int         — day index within the split (0 = first day)
    features  : dict        — feature_name → np.ndarray(n_stocks,) today's cross-section
    prices    : np.ndarray  — (n_stocks,) today's closing prices
    portfolio : np.ndarray  — (n_stocks,) current portfolio weights before rebalancing

    Returns
    ───────
    np.ndarray (n_stocks,) target weights. Will be normalized if |sum| > 1.
    Return all zeros to hold cash.
    """

    def on_day(
        self,
        day: int,
        features: dict[str, np.ndarray],
        prices: np.ndarray,
        portfolio: np.ndarray,
    ) -> np.ndarray:
        return np.zeros(len(prices))


# ---------------------------------------------------------------------------
# Backtest result
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    """Performance metrics for one backtest run."""
    daily_returns: np.ndarray      # (n_days_active,) portfolio return each day
    weights: np.ndarray            # (n_days, n_stocks) weights over time
    tc_bps: float                  # one-way transaction cost used
    rebalance_every: int
    warmup_days: int

    # ---- derived metrics ----

    @property
    def annualized_return(self) -> float:
        r = self.daily_returns
        return float(np.prod(1 + r) ** (252 / len(r)) - 1) if len(r) > 0 else 0.0

    @property
    def annualized_vol(self) -> float:
        return float(self.daily_returns.std() * math.sqrt(252))

    @property
    def sharpe(self) -> float:
        vol = self.annualized_vol
        return float(self.annualized_return / vol) if vol > 1e-9 else 0.0

    @property
    def max_drawdown(self) -> float:
        """Maximum peak-to-trough drawdown (positive number)."""
        cum = np.cumprod(1 + self.daily_returns)
        peak = np.maximum.accumulate(cum)
        dd = (cum - peak) / np.maximum(peak, 1e-9)
        return float(-dd.min())

    @property
    def calmar(self) -> float:
        md = self.max_drawdown
        return float(self.annualized_return / md) if md > 1e-9 else 0.0

    @property
    def turnover_annual(self) -> float:
        """Average one-way daily turnover × 252 (annualized)."""
        if self.weights.shape[0] < 2:
            return 0.0
        daily_to = np.abs(np.diff(self.weights, axis=0)).sum(axis=1)
        return float(daily_to.mean() * 252)

    @property
    def hit_rate(self) -> float:
        """Fraction of days with positive portfolio return."""
        return float((self.daily_returns > 0).mean())

    @property
    def cumulative_returns(self) -> np.ndarray:
        return np.cumprod(1 + self.daily_returns) - 1

    def tearsheet(self, title: str = "Backtest") -> None:
        r = self.daily_returns
        print(f"\n{'─'*48}")
        print(f"  {title}")
        print(f"{'─'*48}")
        print(f"  Days traded       {len(r):>10,}")
        print(f"  Annualized return {self.annualized_return:>10.2%}")
        print(f"  Annualized vol    {self.annualized_vol:>10.2%}")
        print(f"  Sharpe ratio      {self.sharpe:>10.3f}")
        print(f"  Max drawdown      {self.max_drawdown:>10.2%}")
        print(f"  Calmar ratio      {self.calmar:>10.3f}")
        print(f"  Annual turnover   {self.turnover_annual:>10.1f}x")
        print(f"  Hit rate          {self.hit_rate:>10.1%}")
        print(f"  TC bps (1-way)    {self.tc_bps:>10.1f}")
        print(f"{'─'*48}\n")


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

class Backtest:
    """
    Walk-forward backtester with point-in-time feature delivery.

    Parameters
    ----------
    tc_bps : float
        One-way transaction cost in basis points (default 10).
    rebalance_every : int
        Rebalance every N days (default 1 = daily).
    warmup_days : int
        Skip this many days before starting (allows features to populate).
        Default 252 — gives 12-month momentum feature time to fill in.
    """

    def __init__(
        self,
        tc_bps: float = 10.0,
        rebalance_every: int = 1,
        warmup_days: int = 252,
    ):
        self.tc_bps = tc_bps
        self.rebalance_every = rebalance_every
        self.warmup_days = warmup_days

    def run(
        self,
        strategy: Strategy,
        prices: np.ndarray,
        features: dict[str, np.ndarray],
    ) -> BacktestResult:
        """
        Run the strategy walk-forward.

        Parameters
        ----------
        strategy : Strategy
            Strategy instance to evaluate.
        prices : np.ndarray
            Shape (n_days, n_stocks). prices[t] = closing price on day t.
        features : dict[str, np.ndarray]
            Each value shape (n_days, n_stocks). features[k][t] is observable
            at end of day t (no lookahead).
        """
        T, N = prices.shape
        warmup = min(self.warmup_days, T - 2)

        # Produce the weights trajectory by calling the strategy each rebalance day; scoring is
        # delegated to run_from_weights so every backtest — Python or another language — is scored
        # by the exact same code (one source of truth for OOS Sharpe, costs, turnover, etc.).
        weights_history = np.zeros((T, N))
        portfolio = np.zeros(N)
        for t in range(warmup, T - 1):
            step = t - warmup
            if step % self.rebalance_every == 0:
                features_t = {k: v[t] for k, v in features.items()}
                try:
                    new_w = strategy.on_day(t, features_t, prices[t], portfolio.copy())
                    new_w = np.nan_to_num(np.asarray(new_w, dtype=float))
                    abs_sum = np.abs(new_w).sum()
                    if abs_sum > 1.0:
                        new_w /= abs_sum
                except Exception as e:
                    print(f"[day {t}] strategy error: {e}")
                    new_w = portfolio.copy()
            else:
                new_w = portfolio.copy()
            portfolio = new_w
            weights_history[t + 1] = new_w

        return self.run_from_weights(weights_history, prices)

    def run_from_weights(self, weights: np.ndarray, prices: np.ndarray) -> BacktestResult:
        """Score a precomputed (T, N) weights trajectory — the language-agnostic scoring core.

        `weights[t+1]` are the target weights held to earn the day t→t+1 return; `weights[:warmup+1]`
        are zero (flat before the strategy starts). R/Julia strategies run their own on_day loop in
        a subprocess and hand back this matrix, which is then scored identically to Python."""
        T, N = prices.shape
        warmup = min(self.warmup_days, T - 2)
        weights = np.nan_to_num(np.asarray(weights, dtype=float))
        daily_returns = np.zeros(T - warmup - 1)
        for t in range(warmup, T - 1):
            w, prev = weights[t + 1], weights[t]
            tc = np.abs(w - prev).sum() * self.tc_bps / 10_000
            next_rets = prices[t + 1] / prices[t] - 1
            daily_returns[t - warmup] = float(np.dot(w, next_rets)) - tc
        return BacktestResult(
            daily_returns=daily_returns,
            weights=weights,
            tc_bps=self.tc_bps,
            rebalance_every=self.rebalance_every,
            warmup_days=warmup,
        )


# ---------------------------------------------------------------------------
# SimpleBacktest — beginner-friendly backtester using predict() pattern
# ---------------------------------------------------------------------------

class SimpleBacktest:
    """
    Beginner-friendly backtester for strategies that implement::

        def predict(self, features: np.ndarray) -> np.ndarray:
            # features shape: (n_assets, n_features)
            # return: score array shape (n_assets,), higher = more bullish

    The backtester ranks scores, goes long the top top_k and short
    the bottom top_k, applies transaction costs, and records daily P&L.

    Parameters
    ----------
    market : SyntheticMarket
    strategy : object with predict(features) method
    top_k : int
        Number of stocks in each leg (long and short).
    transaction_cost_bps : float
        One-way transaction cost in basis points.
    """

    def __init__(self, market, strategy, top_k: int = 20, transaction_cost_bps: float = 10.0):
        self.market = market
        self.strategy = strategy
        self.top_k = top_k
        self.tc_bps = transaction_cost_bps / 10000.0

    def run(self, split: str = "train") -> BacktestResult:
        prices = self.market.prices(split)            # (T, N)
        feats = self.market.features_array(split)    # (T, N, F)
        T, N = prices.shape

        daily_returns = np.zeros(T - 1)
        weights_hist = np.zeros((T, N))
        prev_w = np.zeros(N)

        for t in range(1, T):
            scores = self.strategy.predict(feats[t - 1])  # (N,)
            order = np.argsort(scores)
            w = np.zeros(N)
            w[order[-self.top_k:]] = 1.0 / self.top_k
            w[order[:self.top_k]] = -1.0 / self.top_k

            turnover = np.abs(w - prev_w).sum()
            tc = turnover * self.tc_bps
            ret = prices[t] / prices[t - 1] - 1
            daily_returns[t - 1] = float((w * ret).sum()) - tc

            weights_hist[t] = w
            prev_w = w

        return BacktestResult(
            daily_returns=daily_returns,
            weights=weights_hist,
            tc_bps=self.tc_bps * 10000,
            rebalance_every=1,
            warmup_days=0,
        )


# ---------------------------------------------------------------------------
# Example strategies (students can copy, modify, or compete against these)
# ---------------------------------------------------------------------------

class EqualWeight(Strategy):
    """Simplest possible baseline: equal-weight long-only portfolio."""

    def on_day(self, day, features, prices, portfolio):
        n = len(prices)
        return np.full(n, 1.0 / n)


class MomentumLong(Strategy):
    """
    Long-only momentum: buy top quintile by 1-month momentum.
    The simplest non-trivial strategy — a useful baseline.
    """

    def __init__(self, signal: str = "mom_1m", top_pct: float = 0.20):
        self.signal = signal
        self.top_pct = top_pct

    def on_day(self, day, features, prices, portfolio):
        sig = features.get(self.signal, np.zeros(len(prices)))
        thresh = np.nanpercentile(sig, (1 - self.top_pct) * 100)
        w = np.where(sig >= thresh, 1.0, 0.0)
        total = w.sum()
        return w / total if total > 0 else np.zeros(len(prices))


class LongShortRank(Strategy):
    """
    Long top quintile, short bottom quintile of a chosen signal.
    The canonical factor strategy — what most academic papers do.
    Mission 1: try to find the signal(s) that work on this market.
    """

    def __init__(self, signal: str = "mom_1m", quintile_frac: float = 0.20):
        self.signal = signal
        self.quintile_frac = quintile_frac

    def on_day(self, day, features, prices, portfolio):
        sig = features.get(self.signal, np.zeros(len(prices)))
        valid = ~np.isnan(sig)
        if valid.sum() < 10:
            return np.zeros(len(prices))
        lo = np.nanpercentile(sig, self.quintile_frac * 100)
        hi = np.nanpercentile(sig, (1 - self.quintile_frac) * 100)
        w = np.zeros(len(sig))
        w[sig >= hi] =  1.0
        w[sig <= lo] = -1.0
        total = np.abs(w).sum()
        return w / total if total > 0 else w


class CombinedSignal(Strategy):
    """
    Weighted combination of multiple signals.
    Demonstrates multi-factor portfolio construction.
    """

    def __init__(
        self,
        signals: dict[str, float],   # {feature_name: weight}
        quintile_frac: float = 0.20,
    ):
        self.signals = signals
        self.quintile_frac = quintile_frac

    def on_day(self, day, features, prices, portfolio):
        n = len(prices)
        composite = np.zeros(n)
        total_w = sum(abs(v) for v in self.signals.values())
        for fname, w in self.signals.items():
            sig = features.get(fname, np.zeros(n))
            composite += (w / total_w) * np.nan_to_num(sig)
        # Rank-sort composite
        lo = np.nanpercentile(composite, self.quintile_frac * 100)
        hi = np.nanpercentile(composite, (1 - self.quintile_frac) * 100)
        port = np.zeros(n)
        port[composite >= hi] =  1.0
        port[composite <= lo] = -1.0
        total = np.abs(port).sum()
        return port / total if total > 0 else port
