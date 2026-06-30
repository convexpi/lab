"""
grader.py — Hidden-holdout evaluator for the Lab.

Runs a submitted strategy on data it never saw and compares in-sample vs.
out-of-sample performance. Detects which planted alphas the student discovered
and which noise features they (incorrectly) relied on.

This is the anti-overfitting core of the platform. A student who curve-fit
their strategy to the training data will see a sharp Sharpe drop here. The
"All That Glitters" lesson (Quantopian's own finding that in-sample Sharpe
has no power to predict out-of-sample) becomes concrete and personal.

Quick start:
    from synth import SyntheticMarket
    from lab import Backtest, LongShortRank
    from grader import Grader

    market = SyntheticMarket(seed=42)
    strategy = LongShortRank(signal="mom_1m")
    report = Grader(market).evaluate(strategy)
    report.print()

Grade interpretation:
    overfitting_ratio = oos_sharpe / is_sharpe (capped at 1.0)
    > 0.70 : robust — out-of-sample holds up
    0.40–0.70 : moderate overfitting
    < 0.40 : severe overfitting — the strategy found noise

Alpha discovery:
    For each planted alpha, the grader checks whether the strategy's OOS
    portfolio weights correlate with the true alpha signal cross-section.
    A Pearson correlation > 0.10 with p < 0.05 is counted as "discovered."
"""

from __future__ import annotations
import math
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from .synth import SyntheticMarket, PlantedAlpha, _cross_rank
from .backtest import Strategy, Backtest, BacktestResult


# ---------------------------------------------------------------------------
# Grade report
# ---------------------------------------------------------------------------

@dataclass
class AlphaDiscovery:
    feature: str
    planted_strength_bps: float
    correlation: float           # portfolio weight vs. alpha signal cross-section
    discovered: bool             # correlation > threshold with statistical significance
    oos_contribution: float      # signal Information Ratio in OOS (IC/vol(IC)*sqrt(252))

@dataclass
class GradeReport:
    strategy_name: str
    is_sharpe: float             # in-sample Sharpe (self-reported, untrusted)
    oos_sharpe: float            # out-of-sample Sharpe (graded, trusted)
    is_max_dd: float
    oos_max_dd: float
    overfitting_ratio: float     # oos_sharpe / is_sharpe, capped at 1.0
    alpha_discovery: list[AlphaDiscovery]
    noise_loadings: dict[str, float]    # feature -> avg |weight correlation| for noise features
    is_result: BacktestResult
    oos_result: BacktestResult

    def print(self) -> None:
        w = 52
        print(f"\n{'═'*w}")
        print(f"  GRADE REPORT  —  {self.strategy_name}")
        print(f"{'═'*w}")
        print(f"  {'':30}{'In-sample':>10}{'OOS':>10}")
        print(f"  {'Sharpe ratio':30}{self.is_sharpe:>10.3f}{self.oos_sharpe:>10.3f}")
        print(f"  {'Max drawdown':30}{self.is_max_dd:>10.2%}{self.oos_max_dd:>10.2%}")
        print(f"  {'Annual return':30}"
              f"{self.is_result.annualized_return:>10.2%}"
              f"{self.oos_result.annualized_return:>10.2%}")
        print(f"  {'Annual turnover':30}"
              f"{self.is_result.turnover_annual:>10.1f}x"
              f"{self.oos_result.turnover_annual:>10.1f}x")
        print()

        ratio = self.overfitting_ratio
        if ratio > 0.70:
            verdict, style = "ROBUST", "✓"
        elif ratio > 0.40:
            verdict, style = "MODERATE OVERFITTING", "~"
        else:
            verdict, style = "SEVERE OVERFITTING", "✗"
        print(f"  Overfitting ratio  {ratio:>6.2f}   {style} {verdict}")
        print(f"  (OOS Sharpe / IS Sharpe — target > 0.70)")
        print()

        print(f"  Alpha discovery:")
        for disc in self.alpha_discovery:
            mark = "✓" if disc.discovered else "✗"
            print(f"    {mark} {disc.feature:<18}"
                  f"  planted={disc.planted_strength_bps:.1f}bps"
                  f"  corr={disc.correlation:+.3f}"
                  f"  signal IR={disc.oos_contribution:+.3f}")
        if not self.alpha_discovery:
            print("    (no planted alphas in this market)")

        if self.noise_loadings:
            print()
            print(f"  Noise feature loadings (should be near zero):")
            for fname, load in sorted(self.noise_loadings.items(),
                                      key=lambda kv: -abs(kv[1])):
                flag = "  ← relying on noise!" if abs(load) > 0.05 else ""
                print(f"    {fname:<18}  |corr|={abs(load):.3f}{flag}")

        print(f"{'═'*w}\n")


# ---------------------------------------------------------------------------
# Grader
# ---------------------------------------------------------------------------

class Grader:
    """
    Evaluates a strategy against the hidden holdout and scores alpha discovery.

    Parameters
    ----------
    market : SyntheticMarket
        The synthetic market (has both train and test splits).
    tc_bps : float
        Transaction cost to use for evaluation (overrides market default).
    discovery_corr_threshold : float
        Minimum weight-signal Pearson correlation to count as "discovered."
    """

    def __init__(
        self,
        market: SyntheticMarket,
        tc_bps: Optional[float] = None,
        discovery_corr_threshold: float = 0.08,
    ):
        self.market = market
        self.tc_bps = tc_bps if tc_bps is not None else market.tc_bps
        self.threshold = discovery_corr_threshold
        # Weekly rebalancing is the realistic default for daily factor strategies.
        # Daily rebalancing at 10 bps TC eats most long-short alpha (~6% annual drag).
        self._backtest = Backtest(tc_bps=self.tc_bps, rebalance_every=5)

    def evaluate(self, strategy: Strategy) -> GradeReport:
        """Run a Python strategy on both splits and return a full grade report."""
        m = self.market
        is_result  = self._backtest.run(strategy, m.prices("train"), m.features("train"))
        oos_result = self._backtest.run(strategy, m.prices("test"), m.features("test"))
        return self._report_from_results(type(strategy).__name__, is_result, oos_result)

    def evaluate_language(self, language: str, code: str, name: str = "Strategy",
                          timeout: int = 60) -> GradeReport:
        """Grade a non-Python (R/Julia) strategy. The foreign code produces only the weights (via
        its harness); scoring runs through the same run_from_weights path as Python, so identical
        logic in any language earns the same OOS result."""
        from .multilang import run_language_weights
        m, bt = self.market, self._backtest

        def _result(split: str):
            prices, feats = m.prices(split), m.features(split)
            weights = run_language_weights(language, code, prices, feats,
                                           warmup_days=bt.warmup_days,
                                           rebalance_every=bt.rebalance_every, timeout=timeout)
            return bt.run_from_weights(weights, prices)

        return self._report_from_results(name, _result("train"), _result("test"))

    def _report_from_results(self, name: str, is_result, oos_result) -> GradeReport:
        """Build a GradeReport from in/out-of-sample results — shared across all languages."""
        m = self.market
        oos_features = m.features("test")
        is_s, oos_s = is_result.sharpe, oos_result.sharpe
        ratio = 0.0 if abs(is_s) < 1e-6 else (min(1.0, oos_s / is_s) if is_s > 0 else 0.0)
        alpha_discovery = self._check_alpha_discovery(oos_result, oos_features)
        noise_features = [f for f in m.FEATURE_NAMES if f.startswith("noise_")]
        noise_loadings = self._compute_noise_loadings(oos_result, oos_features, noise_features)
        return GradeReport(
            strategy_name=name,
            is_sharpe=is_s,
            oos_sharpe=oos_s,
            is_max_dd=is_result.max_drawdown,
            oos_max_dd=oos_result.max_drawdown,
            overfitting_ratio=ratio,
            alpha_discovery=alpha_discovery,
            noise_loadings=noise_loadings,
            is_result=is_result,
            oos_result=oos_result,
        )

    # ------------------------------------------------------------------
    # Alpha discovery detection
    # ------------------------------------------------------------------

    def _weight_signal_corr(
        self,
        weights: np.ndarray,
        signal: np.ndarray,
        warmup: int,
    ) -> float:
        """
        Average cross-sectional Pearson correlation between portfolio weights
        and the alpha signal, computed day by day in the OOS period.
        """
        T = min(len(weights), len(signal))
        corrs = []
        for t in range(warmup, T):
            w_t = weights[t]
            s_t = signal[t]
            valid = ~np.isnan(s_t)
            if valid.sum() < 10:
                continue
            w_v = w_t[valid]
            s_v = s_t[valid]
            if w_v.std() < 1e-9 or s_v.std() < 1e-9:
                continue
            corr = float(np.corrcoef(w_v, s_v)[0, 1])
            if np.isfinite(corr):
                corrs.append(corr)
        return float(np.mean(corrs)) if corrs else 0.0

    def _signal_sharpe_contribution(
        self,
        oos_result: BacktestResult,
        oos_features: dict[str, np.ndarray],
        alpha: PlantedAlpha,
    ) -> float:
        """
        Information Ratio (IR) of the planted signal in the OOS period:
        IR = mean_IC / std_IC * sqrt(252), where IC is the daily cross-sectional
        Pearson correlation between the signal and next-day returns.

        This measures whether the signal actually predicted OOS returns,
        independent of the student's implementation. Positive = signal worked.
        """
        m = self.market
        feat = oos_features.get(alpha.feature)
        if feat is None:
            return 0.0

        oos_prices = m.prices("test")
        T = len(oos_prices)
        warmup = oos_result.warmup_days
        if T - warmup - 1 < 30:
            return 0.0

        ics: list[float] = []
        for t in range(warmup, T - 1):
            sig_t  = feat[t]
            ret_t1 = oos_prices[t + 1] / oos_prices[t] - 1
            valid  = ~np.isnan(sig_t) & ~np.isnan(ret_t1) & np.isfinite(ret_t1)
            if valid.sum() < 10:
                continue
            s, r = sig_t[valid], ret_t1[valid]
            if s.std() < 1e-9 or r.std() < 1e-9:
                continue
            ic = float(np.corrcoef(s, r)[0, 1])
            if np.isfinite(ic):
                ics.append(ic)

        if len(ics) < 10:
            return 0.0
        avg_ic = float(np.mean(ics))
        ic_vol = float(np.std(ics))
        if ic_vol < 1e-9:
            return 0.0
        return float(np.clip(avg_ic / ic_vol * math.sqrt(252), -10.0, 10.0))

    def _check_alpha_discovery(
        self, oos_result: BacktestResult, oos_features: dict
    ) -> list[AlphaDiscovery]:
        m = self.market
        if not m.planted_alphas:
            return []

        warmup = oos_result.warmup_days
        discoveries = []

        for alpha in m.planted_alphas:
            feat = oos_features.get(alpha.feature)
            if feat is None:
                continue

            corr = self._weight_signal_corr(oos_result.weights, feat, warmup)
            # Two-tailed t-test: n_days is the number of active trading days
            # (daily_returns already has warmup stripped out by the backtester)
            n_days = max(len(oos_result.daily_returns), 1)
            t_stat = corr * math.sqrt(n_days) / math.sqrt(max(1 - corr**2, 1e-9))
            discovered = abs(t_stat) > 1.96 and corr > self.threshold

            contribution = self._signal_sharpe_contribution(oos_result, oos_features, alpha)

            discoveries.append(AlphaDiscovery(
                feature=alpha.feature,
                planted_strength_bps=alpha.strength_bps,
                correlation=corr,
                discovered=discovered,
                oos_contribution=contribution,
            ))

        return discoveries

    def _compute_noise_loadings(
        self,
        oos_result: BacktestResult,
        oos_features: dict,
        noise_feature_names: list[str],
    ) -> dict[str, float]:
        warmup = oos_result.warmup_days
        return {
            fname: self._weight_signal_corr(oos_result.weights,
                                             oos_features[fname], warmup)
            for fname in noise_feature_names
            if fname in oos_features
        }

    def compare(self, strategies: dict[str, Strategy]) -> None:
        """Grade multiple strategies and print a comparison table."""
        print(f"\n{'Strategy':<22}{'IS Sharpe':>12}{'OOS Sharpe':>12}"
              f"{'OvFit Ratio':>13}{'Alphas Found':>14}")
        print("─" * 73)
        for name, strat in strategies.items():
            r = self.evaluate(strat)
            found = sum(1 for d in r.alpha_discovery if d.discovered)
            total = len(r.alpha_discovery)
            print(f"  {name:<20}{r.is_sharpe:>12.3f}{r.oos_sharpe:>12.3f}"
                  f"{r.overfitting_ratio:>13.2f}{found:>8}/{total:<5}")
        print()


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from convexpi.lab.synth import SyntheticMarket
    from convexpi.lab.backtest import EqualWeight, MomentumLong, LongShortRank, CombinedSignal

    print("Generating synthetic market (200 stocks, 5 years)...")
    market = SyntheticMarket(n_stocks=200, n_days=1260, seed=42)
    market.describe()

    grader = Grader(market)

    strategies = {
        "EqualWeight":       EqualWeight(),
        "Momentum(mom_1m)":  LongShortRank("mom_1m"),
        "Momentum(mom_3m)":  LongShortRank("mom_3m"),
        "Value(val_bm)":     LongShortRank("val_bm"),
        "Noise(noise_1)":    LongShortRank("noise_1"),
        "MomValue":          CombinedSignal({"mom_1m": 1.0, "val_bm": 1.0}),
    }

    print("\nGrading all strategies against hidden holdout...")
    grader.compare(strategies)

    print("Detailed report for the best planted-signal strategy:")
    grader.evaluate(strategies["Momentum(mom_1m)"]).print()
