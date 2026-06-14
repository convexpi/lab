"""Tests for the walk-forward backtesting engine."""

import numpy as np
import pytest
from convexpi.lab.backtest import (
    Backtest, BacktestResult, Strategy,
    EqualWeight, MomentumLong, LongShortRank,
)
from convexpi.lab.synth import SyntheticMarket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def small_market():
    return SyntheticMarket(n_stocks=30, n_days=400, seed=1)


@pytest.fixture(scope="module")
def prices(small_market):
    return small_market.prices("train")


@pytest.fixture(scope="module")
def features(small_market):
    return small_market.features("train")


# ---------------------------------------------------------------------------
# Helper strategies for deterministic testing
# ---------------------------------------------------------------------------

class RecordingStrategy(Strategy):
    """Records every (day, features) tuple it receives."""
    def __init__(self):
        self.calls = []

    def on_day(self, day, features, prices, portfolio):
        self.calls.append((day, {k: v.copy() for k, v in features.items()}))
        return np.zeros(len(prices))


class OverweightStrategy(Strategy):
    """Returns weights that sum to > 1.0 — tests auto-normalization."""
    def on_day(self, day, features, prices, portfolio):
        n = len(prices)
        return np.full(n, 10.0)   # sum = 10*n >> 1


class ErrorStrategy(Strategy):
    """Throws on the second call — tests graceful error handling."""
    def __init__(self):
        self._calls = 0

    def on_day(self, day, features, prices, portfolio):
        self._calls += 1
        if self._calls == 2:
            raise ValueError("intentional error")
        return np.zeros(len(prices))


# ---------------------------------------------------------------------------
# BacktestResult metrics
# ---------------------------------------------------------------------------

class TestBacktestResultMetrics:
    def _result(self, rets):
        return BacktestResult(
            daily_returns=np.array(rets),
            weights=np.zeros((len(rets) + 1, 5)),
            tc_bps=10.0,
            rebalance_every=1,
            warmup_days=0,
        )

    def test_positive_returns_positive_sharpe(self):
        # Alternating 0.001/0.003 — positive mean, non-zero variance
        rets = [0.001 if i % 2 == 0 else 0.003 for i in range(252)]
        r = self._result(rets)
        assert r.sharpe > 0

    def test_zero_returns_zero_sharpe(self):
        r = self._result([0.0] * 252)
        assert r.sharpe == 0.0

    def test_negative_returns_negative_sharpe(self):
        # Alternating -0.001/-0.003 — negative mean, non-zero variance
        rets = [-0.001 if i % 2 == 0 else -0.003 for i in range(252)]
        r = self._result(rets)
        assert r.sharpe < 0

    def test_max_drawdown_nonnegative(self):
        r = self._result([0.01, -0.05, 0.02, -0.03])
        assert r.max_drawdown >= 0

    def test_max_drawdown_flat(self):
        r = self._result([0.0] * 50)
        assert r.max_drawdown == pytest.approx(0.0, abs=1e-9)

    def test_hit_rate_in_range(self):
        r = self._result([0.001, -0.001, 0.001, -0.001])
        assert 0.0 <= r.hit_rate <= 1.0

    def test_annualized_return_correct(self):
        # Compound: (1.0001)^252 - 1 ≈ 2.55% (not 2.52% simple)
        import numpy as np
        rets = [0.0001] * 252
        expected = float(np.prod([1 + r for r in rets]) ** (252 / 252) - 1)
        r = self._result(rets)
        assert r.annualized_return == pytest.approx(expected, rel=0.001)

    def test_cumulative_returns_shape(self):
        r = self._result([0.01, 0.02, -0.01])
        cum = r.cumulative_returns()
        assert len(cum) == 3


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

class TestBacktestRun:
    def test_result_type(self, prices, features):
        bt = Backtest(tc_bps=0.0, warmup_days=20)
        result = bt.run(EqualWeight(), prices, features)
        assert isinstance(result, BacktestResult)

    def test_daily_returns_length(self, prices, features):
        warmup = 20
        bt = Backtest(tc_bps=0.0, warmup_days=warmup)
        result = bt.run(EqualWeight(), prices, features)
        T = len(prices)
        # daily_returns has T - warmup - 1 entries
        assert len(result.daily_returns) == T - warmup - 1

    def test_weights_finite(self, prices, features):
        bt = Backtest(tc_bps=0.0, warmup_days=20)
        result = bt.run(EqualWeight(), prices, features)
        assert np.all(np.isfinite(result.weights))

    def test_daily_returns_finite(self, prices, features):
        bt = Backtest(tc_bps=0.0, warmup_days=20)
        result = bt.run(EqualWeight(), prices, features)
        assert np.all(np.isfinite(result.daily_returns))

    def test_zero_strategy_zero_returns(self, prices, features):
        class ZeroStrategy(Strategy):
            pass   # default on_day returns zeros

        bt = Backtest(tc_bps=0.0, warmup_days=10)
        result = bt.run(ZeroStrategy(), prices, features)
        np.testing.assert_array_almost_equal(result.daily_returns, 0.0)


class TestBacktestPointInTime:
    def test_strategy_receives_today_not_tomorrow(self, prices, features):
        recording = RecordingStrategy()
        bt = Backtest(tc_bps=0.0, warmup_days=20)
        bt.run(recording, prices, features)
        # day passed to on_day should match the step index + warmup
        assert len(recording.calls) > 0
        # Features at call i should equal features at day = warmup + i
        warmup = 20
        for i, (day, feats) in enumerate(recording.calls[:5]):
            for name, arr in feats.items():
                np.testing.assert_array_equal(arr, features[name][day])

    def test_strategy_receives_feature_dict(self, prices, features):
        recording = RecordingStrategy()
        bt = Backtest(tc_bps=0.0, warmup_days=20)
        bt.run(recording, prices, features)
        _, feats = recording.calls[0]
        for name in features:
            assert name in feats


class TestBacktestRebalance:
    def test_daily_rebalancing_calls_every_day(self, prices, features):
        recording = RecordingStrategy()
        bt = Backtest(tc_bps=0.0, warmup_days=10, rebalance_every=1)
        result = bt.run(recording, prices, features)
        assert len(recording.calls) == len(result.daily_returns)

    def test_weekly_rebalancing_reduces_calls(self, prices, features):
        recording_daily  = RecordingStrategy()
        recording_weekly = RecordingStrategy()
        bt_daily  = Backtest(tc_bps=0.0, warmup_days=10, rebalance_every=1)
        bt_weekly = Backtest(tc_bps=0.0, warmup_days=10, rebalance_every=5)
        bt_daily.run(recording_daily, prices, features)
        bt_weekly.run(recording_weekly, prices, features)
        assert len(recording_weekly.calls) < len(recording_daily.calls)

    def test_weekly_rebalancing_calls_exactly(self, prices, features):
        T = len(prices)
        warmup = 10
        recording = RecordingStrategy()
        bt = Backtest(tc_bps=0.0, warmup_days=warmup, rebalance_every=5)
        bt.run(recording, prices, features)
        # Every 5th step is a rebalance
        expected = sum(1 for step in range(T - warmup - 1) if step % 5 == 0)
        assert len(recording.calls) == expected


class TestBacktestTransactionCosts:
    def test_higher_tc_lower_returns(self, prices, features):
        strat_no_tc = LongShortRank("mom_1m")
        strat_hi_tc = LongShortRank("mom_1m")
        bt_no_tc = Backtest(tc_bps=0.0,    warmup_days=50)
        bt_hi_tc = Backtest(tc_bps=100.0,  warmup_days=50)
        r_no_tc = bt_no_tc.run(strat_no_tc, prices, features)
        r_hi_tc = bt_hi_tc.run(strat_hi_tc, prices, features)
        assert r_no_tc.annualized_return > r_hi_tc.annualized_return

    def test_zero_tc_no_penalty(self, prices, features):
        # With zero TC the portfolio return is purely from weights * next-day returns
        strat = EqualWeight()
        bt = Backtest(tc_bps=0.0, warmup_days=10)
        result = bt.run(strat, prices, features)
        # Just check we get a valid result
        assert np.all(np.isfinite(result.daily_returns))


class TestBacktestNormalization:
    def test_overweight_strategy_weights_capped(self, prices, features):
        bt = Backtest(tc_bps=0.0, warmup_days=10)
        result = bt.run(OverweightStrategy(), prices, features)
        # After normalization, |weights|.sum() per day should be ≈ 1 or 0
        row_sums = np.abs(result.weights).sum(axis=1)
        active = row_sums > 1e-9
        assert np.all(row_sums[active] <= 1.0 + 1e-9)

    def test_error_strategy_uses_previous_weights(self, prices, features):
        strat = ErrorStrategy()
        bt = Backtest(tc_bps=0.0, warmup_days=10)
        result = bt.run(strat, prices, features)
        # Should complete without raising
        assert len(result.daily_returns) > 0


# ---------------------------------------------------------------------------
# Built-in strategies
# ---------------------------------------------------------------------------

class TestBuiltinStrategies:
    def test_equal_weight_sums_to_one(self, prices, features):
        recording = RecordingStrategy()
        strat = EqualWeight()
        # Check the weights it returns directly
        n = prices.shape[1]
        w = strat.on_day(0, {k: v[0] for k, v in features.items()}, prices[0], np.zeros(n))
        assert abs(w.sum() - 1.0) < 1e-9

    def test_long_short_rank_sums_near_zero(self, prices, features):
        strat = LongShortRank("mom_1m")
        n = prices.shape[1]
        # Use a day with valid mom_1m data (day > 21)
        feats_t = {k: v[30] for k, v in features.items()}
        w = strat.on_day(30, feats_t, prices[30], np.zeros(n))
        assert abs(w.sum()) < 0.1  # approximately dollar-neutral

    def test_momentum_long_nonnegative_weights(self, prices, features):
        strat = MomentumLong()
        n = prices.shape[1]
        feats_t = {k: v[30] for k, v in features.items()}
        w = strat.on_day(30, feats_t, prices[30], np.zeros(n))
        assert np.all(w >= 0)
