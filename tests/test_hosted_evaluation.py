import os
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deploy'))
os.environ.setdefault('NEXT_PUBLIC_SUPABASE_URL', 'https://example.invalid')
os.environ.setdefault('SUPABASE_SERVICE_KEY', 'dummy-key')
import evaluation
import forward_runner
from convexpi.lab import SyntheticMarket, Backtest
from sandbox import SandboxError


class EqualWeight:
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def on_day(self, day, features, prices, portfolio):
        assert prices.ndim == 1
        assert all(x.ndim == 1 for x in features.values())
        return np.ones_like(prices) / len(prices)


def test_forward_scores_exact_window_and_emits_annual_return(monkeypatch):
    counts = []
    original = evaluation.score_strategy
    def record(*args):
        result = original(*args)
        counts.append(len(result.daily_returns))
        return result
    monkeypatch.setattr(forward_runner, 'score_strategy', record)
    monkeypatch.setattr(forward_runner, 'StrategyProcess', lambda *a, **k: EqualWeight())
    result = forward_runner.evaluate_submission('test', '', 42)
    assert counts == [60]
    assert np.isfinite(result['oos_annual_return'])
    assert np.isfinite(result['oos_sharpe'])
    assert result['oos_sharpe'] != 0


def test_only_current_observations_cross_scoring_boundary():
    m = SyntheticMarket(n_stocks=20, n_days=30, seed=42)
    bt = Backtest(warmup_days=0)
    result = evaluation.score_strategy(EqualWeight(), m.prices('all'), m.features('all'), bt)
    assert len(result.daily_returns) == 29


def test_forged_metrics_are_not_accepted_as_weights():
    code = "class MyStrategy:\n    def on_day(self, *args):\n        return {'oos_sharpe':999}\n"
    with evaluation.StrategyProcess(code) as process:
        with pytest.raises((SandboxError, ValueError, TypeError)):
            process.on_day(0, {}, np.ones(2), np.zeros(2))


@pytest.mark.parametrize('language,code', [
    ('python', 'class MyStrategy:\n    def on_day(self, day, features, prices, portfolio):\n        return prices * 0 + 100\n'),
    ('r', 'on_day <- function(day, features, prices, portfolio) rep(100, length(prices))'),
    ('julia', 'function on_day(day, features, prices, portfolio)\n    fill(100., length(prices))\nend'),
])
def test_languages_only_return_normalized_decisions(language, code):
    with evaluation.StrategyProcess(code, language, timeout=60) as process:
        weights = process.on_day(0, {'signal': np.array([1., 2.])}, np.ones(2), np.zeros(2))
        np.testing.assert_allclose(weights, [.5, .5])
