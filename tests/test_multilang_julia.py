"""Conformance: a Julia strategy is scored identically to its Python twin (see test_multilang_r)."""
import shutil

import numpy as np
import pytest

from convexpi.lab import Backtest, Grader, Strategy, SyntheticMarket
from convexpi.lab.multilang import run_language_weights

pytestmark = pytest.mark.skipif(shutil.which("julia") is None, reason="Julia not installed")


def test_julia_strategy_matches_python():
    market = SyntheticMarket(n_stocks=30, n_days=350, seed=42)
    prices, features = market.prices("train"), market.features("train")
    feat = next(iter(features))

    class PyStrat(Strategy):
        def on_day(self, day, features, prices, portfolio):
            sig = np.nan_to_num(features[feat])
            s = np.abs(sig).sum()
            return sig / s if s > 0 else sig

    py = Backtest(warmup_days=252).run(PyStrat(), prices, features)

    jl_code = f'''
function on_day(day, features, prices, portfolio)
    sig = copy(features["{feat}"])
    sig[.!isfinite.(sig)] .= 0.0
    s = sum(abs.(sig))
    return s > 0 ? sig ./ s : sig
end
'''
    weights = run_language_weights("julia", jl_code, prices, features, warmup_days=252, rebalance_every=1)
    jl = Backtest(warmup_days=252).run_from_weights(weights, prices)

    assert np.allclose(py.weights, weights, atol=1e-8)
    assert np.allclose(py.daily_returns, jl.daily_returns, atol=1e-8)


def test_julia_grader_matches_python_grader():
    market = SyntheticMarket(n_stocks=40, n_days=400, seed=42)
    feat = next(iter(market.features("train")))

    class PyStrat(Strategy):
        def on_day(self, day, features, prices, portfolio):
            sig = np.nan_to_num(features[feat])
            s = np.abs(sig).sum()
            return sig / s if s > 0 else sig

    grader = Grader(market)
    py = grader.evaluate(PyStrat())
    jl_code = f'''
function on_day(day, features, prices, portfolio)
    sig = copy(features["{feat}"]); sig[.!isfinite.(sig)] .= 0.0
    s = sum(abs.(sig)); return s > 0 ? sig ./ s : sig
end
'''
    jl = grader.evaluate_language("julia", jl_code, name="PyStrat")
    assert abs(py.oos_sharpe - jl.oos_sharpe) < 1e-6
    assert abs(py.overfitting_ratio - jl.overfitting_ratio) < 1e-6
