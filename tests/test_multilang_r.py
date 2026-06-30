"""Conformance: an R strategy is scored identically to its Python twin.

This is the guarantee behind the multi-language grader — R/Julia produce only the weights; Python's
engine scores them, so the same logic written in another language earns the same OOS result.
"""
import shutil

import numpy as np
import pytest

from convexpi.lab import Backtest, Strategy, SyntheticMarket
from convexpi.lab.multilang import run_language_weights

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="R (Rscript) not installed")


def test_r_strategy_matches_python():
    market = SyntheticMarket(n_stocks=30, n_days=350, seed=42)
    prices = market.prices("train")
    features = market.features("train")
    feat = next(iter(features))   # a feature name present in this market

    # Python strategy: weight each stock proportional to a feature (continuous → precision-robust).
    class PyStrat(Strategy):
        def on_day(self, day, features, prices, portfolio):
            sig = np.nan_to_num(features[feat])
            s = np.abs(sig).sum()
            return sig / s if s > 0 else sig

    py = Backtest(warmup_days=252).run(PyStrat(), prices, features)

    # The same strategy written in R.
    r_code = f"""
on_day <- function(day, features, prices, portfolio) {{
  sig <- features[["{feat}"]]
  sig[!is.finite(sig)] <- 0
  s <- sum(abs(sig))
  if (s > 0) sig / s else sig
}}
"""
    weights_r = run_language_weights("r", r_code, prices, features, warmup_days=252, rebalance_every=1)
    r = Backtest(warmup_days=252).run_from_weights(weights_r, prices)

    # Same weight trajectory and therefore the same daily returns (to round-trip precision).
    assert np.allclose(py.weights, weights_r, atol=1e-8)
    assert np.allclose(py.daily_returns, r.daily_returns, atol=1e-8)


def test_r_grader_matches_python_grader():
    """Full Grader path: an R strategy earns the same IS/OOS Sharpe + overfitting ratio as Python."""
    from convexpi.lab import Grader

    market = SyntheticMarket(n_stocks=40, n_days=400, seed=42)
    feat = next(iter(market.features("train")))

    class PyStrat(Strategy):
        def on_day(self, day, features, prices, portfolio):
            sig = np.nan_to_num(features[feat])
            s = np.abs(sig).sum()
            return sig / s if s > 0 else sig

    grader = Grader(market)
    py = grader.evaluate(PyStrat())

    r_code = f'''
on_day <- function(day, features, prices, portfolio) {{
  sig <- features[["{feat}"]]; sig[!is.finite(sig)] <- 0
  s <- sum(abs(sig)); if (s > 0) sig / s else sig
}}
'''
    r = grader.evaluate_language("r", r_code, name="PyStrat")

    assert abs(py.is_sharpe - r.is_sharpe) < 1e-6
    assert abs(py.oos_sharpe - r.oos_sharpe) < 1e-6
    assert abs(py.overfitting_ratio - r.overfitting_ratio) < 1e-6
