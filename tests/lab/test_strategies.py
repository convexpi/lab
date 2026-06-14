"""Tests for the pre-canned strategy library."""

import numpy as np
import pytest

from convexpi.lab.synth import SyntheticMarket
from convexpi.lab.backtest import Backtest
from convexpi.lab.strategies import (
    STRATEGIES,
    compare,
    CrossSectionalMomentum,
    ShortTermReversal,
    TimeSeriesMomentum,
    ValueTilt,
    QualityTilt,
    BettingAgainstBeta,
    SizePremium,
    FamaFrench3,
    MultiFactorRank,
    ICWeightedComposite,
    InverseVolatilityWeight,
    MinimumVarianceScreen,
    TrendFilter,
    DualMomentum,
    MacroCyclical,
    _ls_weights,
    _zscore,
    _rank_corr,
)


# ---------------------------------------------------------------------------
# Shared market fixture (small for speed)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def market():
    return SyntheticMarket(n_stocks=50, n_days=400, seed=7)


@pytest.fixture(scope="module")
def prices_features(market):
    return market.prices("train"), market.features("train")


# ---------------------------------------------------------------------------
# Helper math
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_zscore_mean_zero(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        z = _zscore(x)
        assert abs(z.mean()) < 1e-9

    def test_zscore_nan_becomes_zero(self):
        x = np.array([np.nan, 1.0, 2.0, 3.0])
        z = _zscore(x)
        assert z[0] == 0.0

    def test_ls_weights_sums_to_zero(self):
        rng = np.random.default_rng(0)
        sig = rng.standard_normal(100)
        w = _ls_weights(sig)
        assert abs(w.sum()) < 1e-9  # market-neutral

    def test_ls_weights_normalized(self):
        rng = np.random.default_rng(1)
        sig = rng.standard_normal(100)
        w = _ls_weights(sig)
        assert abs(np.abs(w).sum() - 1.0) < 1e-9

    def test_ls_long_only(self):
        rng = np.random.default_rng(2)
        sig = rng.standard_normal(100)
        w = _ls_weights(sig, long_only=True)
        assert (w >= 0).all()

    def test_ls_small_universe_returns_zeros(self):
        w = _ls_weights(np.array([1.0, 2.0, 3.0]))
        assert np.all(w == 0)

    def test_rank_corr_perfect_positive(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        assert abs(_rank_corr(x, x) - 1.0) < 1e-9

    def test_rank_corr_perfect_negative(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        assert abs(_rank_corr(x, -x) + 1.0) < 1e-9

    def test_rank_corr_nan_handling(self):
        x = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        rc = _rank_corr(x, y)
        assert np.isfinite(rc)


# ---------------------------------------------------------------------------
# Shape contract: every strategy must return (n_stocks,) weights
# ---------------------------------------------------------------------------

ALL_STRATEGIES = [
    ("CrossSectionalMomentum", CrossSectionalMomentum()),
    ("ShortTermReversal",      ShortTermReversal()),
    ("TimeSeriesMomentum",     TimeSeriesMomentum()),
    ("ValueTilt",              ValueTilt()),
    ("QualityTilt",            QualityTilt()),
    ("BettingAgainstBeta",     BettingAgainstBeta()),
    ("SizePremium",            SizePremium()),
    ("FamaFrench3",            FamaFrench3()),
    ("MultiFactorRank",        MultiFactorRank()),
    ("ICWeightedComposite",    ICWeightedComposite()),
    ("InverseVolatilityWeight",InverseVolatilityWeight()),
    ("MinimumVarianceScreen",  MinimumVarianceScreen()),
    ("TrendFilter",            TrendFilter()),
    ("DualMomentum",           DualMomentum()),
    ("MacroCyclical",          MacroCyclical()),
]


@pytest.mark.parametrize("name,strategy", ALL_STRATEGIES)
def test_on_day_returns_correct_shape(name, strategy, prices_features):
    prices, features = prices_features
    n = prices.shape[1]
    # Use day 260 to ensure all lookback windows are populated
    features_t = {k: v[260] for k, v in features.items()}
    w = strategy.on_day(260, features_t, prices[260], np.zeros(n))
    assert w.shape == (n,), f"{name}: expected ({n},), got {w.shape}"


@pytest.mark.parametrize("name,strategy", ALL_STRATEGIES)
def test_on_day_no_nan_or_inf(name, strategy, prices_features):
    prices, features = prices_features
    n = prices.shape[1]
    features_t = {k: v[260] for k, v in features.items()}
    w = strategy.on_day(260, features_t, prices[260], np.zeros(n))
    assert np.all(np.isfinite(w)), f"{name}: weights contain NaN or Inf"


@pytest.mark.parametrize("name,strategy", ALL_STRATEGIES)
def test_weights_normalized(name, strategy, prices_features):
    prices, features = prices_features
    n = prices.shape[1]
    features_t = {k: v[260] for k, v in features.items()}
    w = strategy.on_day(260, features_t, prices[260], np.zeros(n))
    total = np.abs(w).sum()
    assert total <= 1.0 + 1e-9, f"{name}: |weights|.sum() = {total:.4f} > 1"


# ---------------------------------------------------------------------------
# Backtest integration: strategies must run end-to-end
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,strategy", ALL_STRATEGIES)
def test_backtest_runs(name, strategy, market):
    bt = Backtest(warmup_days=60, tc_bps=10)
    result = bt.run(strategy, market.prices("train"), market.features("train"))
    assert len(result.daily_returns) > 0
    assert np.isfinite(result.sharpe)


# ---------------------------------------------------------------------------
# Strategy-specific behaviour tests
# ---------------------------------------------------------------------------

class TestMomentum:
    def test_cs_momentum_is_market_neutral(self, prices_features):
        prices, features = prices_features
        features_t = {k: v[260] for k, v in features.items()}
        w = CrossSectionalMomentum().on_day(260, features_t, prices[260], np.zeros(prices.shape[1]))
        assert abs(w.sum()) < 1e-9

    def test_ts_momentum_can_be_net_long(self, prices_features):
        prices, features = prices_features
        # Create a features dict where all mom_12m signals are positive
        n = prices.shape[1]
        fake_feat = {"mom_12m": np.ones(n)}
        w = TimeSeriesMomentum().on_day(260, fake_feat, prices[260], np.zeros(n))
        assert w.sum() > 0  # net long when all signals positive

    def test_ts_momentum_flat_on_nan(self, prices_features):
        prices, features = prices_features
        n = prices.shape[1]
        fake_feat = {"mom_12m": np.full(n, np.nan)}
        w = TimeSeriesMomentum().on_day(0, fake_feat, prices[0], np.zeros(n))
        assert np.all(w == 0)

    def test_dual_momentum_long_only(self, prices_features):
        prices, features = prices_features
        n = prices.shape[1]
        features_t = {k: v[260] for k, v in features.items()}
        w = DualMomentum().on_day(260, features_t, prices[260], np.zeros(n))
        assert (w >= -1e-12).all()  # long-only


class TestValue:
    def test_value_tilt_market_neutral(self, prices_features):
        prices, features = prices_features
        features_t = {k: v[260] for k, v in features.items()}
        w = ValueTilt().on_day(260, features_t, prices[260], np.zeros(prices.shape[1]))
        assert abs(w.sum()) < 1e-9

    def test_value_long_only_nonnegative(self, prices_features):
        prices, features = prices_features
        features_t = {k: v[260] for k, v in features.items()}
        w = ValueTilt(long_only=True).on_day(260, features_t, prices[260], np.zeros(prices.shape[1]))
        assert (w >= -1e-12).all()


class TestRiskBased:
    def test_inv_vol_long_only_sums_to_one(self, prices_features):
        prices, features = prices_features
        n = prices.shape[1]
        features_t = {k: v[260] for k, v in features.items()}
        w = InverseVolatilityWeight(long_only=True).on_day(260, features_t, prices[260], np.zeros(n))
        assert abs(w.sum() - 1.0) < 1e-9

    def test_min_variance_long_only(self, prices_features):
        prices, features = prices_features
        n = prices.shape[1]
        features_t = {k: v[260] for k, v in features.items()}
        w = MinimumVarianceScreen().on_day(260, features_t, prices[260], np.zeros(n))
        assert (w >= -1e-12).all()
        assert abs(w.sum() - 1.0) < 1e-9  # fully invested in selected stocks


class TestConditional:
    def test_trend_filter_flat_when_down(self, prices_features):
        prices, features = prices_features
        n = prices.shape[1]
        neg_feat = {"mom_12m": np.full(n, -1.0)}
        w = TrendFilter(flat_on_down=True).on_day(260, neg_feat, prices[260], np.zeros(n))
        assert np.all(w == 0)

    def test_trend_filter_active_when_up(self, prices_features):
        prices, features = prices_features
        n = prices.shape[1]
        pos_feat = {k: v[260] for k, v in features.items()}
        pos_feat["mom_12m"] = np.full(n, 1.0)  # all positive → trend up
        w = TrendFilter(flat_on_down=True).on_day(260, pos_feat, prices[260], np.zeros(n))
        assert np.abs(w).sum() > 0  # not flat

    def test_macro_cyclical_falls_back_without_macro(self, prices_features):
        prices, features = prices_features
        n = prices.shape[1]
        features_t = {k: v[260] for k, v in features.items()}
        # Remove macro feature if present
        features_t.pop("macro_yield_curve", None)
        w = MacroCyclical().on_day(260, features_t, prices[260], np.zeros(n))
        assert np.isfinite(w).all()
        assert np.abs(w).sum() > 0


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_all_registry_names_run(self, market):
        bt = Backtest(warmup_days=60)
        prices   = market.prices("train")
        features = market.features("train")
        for name, strategy in STRATEGIES.items():
            result = bt.run(strategy, prices, features)
            assert np.isfinite(result.sharpe), f"{name} produced non-finite Sharpe"

    def test_compare_returns_dataframe(self, market):
        pd = pytest.importorskip("pandas")
        subset = {k: STRATEGIES[k] for k in list(STRATEGIES)[:4]}
        df = compare(subset, market=market, split="train", warmup_days=60)
        assert set(df.columns) >= {"sharpe", "annual_return", "max_drawdown"}
        assert len(df) == 4

    def test_compare_requires_market(self):
        with pytest.raises(ValueError, match="market is required"):
            compare()
