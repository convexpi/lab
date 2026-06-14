"""Tests for the synthetic market generator."""

import numpy as np
import pytest
from convexpi.lab.synth import SyntheticMarket, PlantedAlpha, _cross_rank, _cs_zscore


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestCrossRank:
    def test_output_range(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        r = _cross_rank(x)
        assert r.min() >= -0.5
        assert r.max() <= 0.5

    def test_monotone(self):
        x = np.array([10.0, 20.0, 30.0])
        r = _cross_rank(x)
        assert r[0] < r[1] < r[2]

    def test_nan_maps_to_zero(self):
        x = np.array([1.0, np.nan, 3.0])
        r = _cross_rank(x)
        assert r[1] == 0.0

    def test_single_valid_returns_zeros(self):
        x = np.array([np.nan, 5.0, np.nan])
        r = _cross_rank(x)
        assert np.all(r == 0.0)

    def test_symmetric_for_two_values(self):
        x = np.array([1.0, 2.0])
        r = _cross_rank(x)
        assert r[0] == -0.5
        assert r[1] == 0.5


class TestCsZscore:
    def test_zero_mean(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        z = _cs_zscore(x)
        assert abs(z.mean()) < 1e-9

    def test_unit_std(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        z = _cs_zscore(x)
        assert abs(z.std() - 1.0) < 0.01

    def test_nan_passthrough(self):
        x = np.array([1.0, np.nan, 3.0])
        z = _cs_zscore(x)
        assert np.isnan(z[1])


# ---------------------------------------------------------------------------
# SyntheticMarket
# ---------------------------------------------------------------------------

N_STOCKS = 50
N_DAYS   = 300

@pytest.fixture(scope="module")
def market():
    return SyntheticMarket(n_stocks=N_STOCKS, n_days=N_DAYS, seed=42)


class TestSyntheticMarketShape:
    def test_prices_train_shape(self, market):
        p = market.prices("train")
        assert p.shape[1] == N_STOCKS
        assert p.shape[0] == market.train_end

    def test_prices_test_shape(self, market):
        p = market.prices("test")
        assert p.shape[1] == N_STOCKS
        assert p.shape[0] == N_DAYS - market.train_end

    def test_prices_all_shape(self, market):
        p = market.prices("all")
        assert p.shape == (N_DAYS, N_STOCKS)

    def test_train_test_no_overlap(self, market):
        train_end = market.train_end
        assert train_end < N_DAYS
        assert train_end > 0

    def test_features_train_shape(self, market):
        feats = market.features("train")
        for name, arr in feats.items():
            assert arr.shape == (market.train_end, N_STOCKS), f"Bad shape for {name}"

    def test_features_all_names_present(self, market):
        feats = market.features("train")
        for name in SyntheticMarket.FEATURE_NAMES:
            assert name in feats

    def test_alpha_returns_shape(self, market):
        ar = market.alpha_returns()
        assert ar.shape == (N_DAYS, N_STOCKS)

    def test_invalid_split_raises(self, market):
        with pytest.raises(ValueError):
            market.prices("invalid")


class TestSyntheticMarketPrices:
    def test_all_prices_positive(self, market):
        assert np.all(market.prices("all") > 0)

    def test_start_prices_in_range(self, market):
        first_row = market.prices("all")[0]
        assert np.all(first_row >= 15.0)
        assert np.all(first_row <= 160.0)

    def test_returns_finite(self, market):
        r = market.returns("train")
        assert np.all(np.isfinite(r))

    def test_train_test_prices_contiguous(self, market):
        train = market.prices("train")
        test  = market.prices("test")
        all_  = market.prices("all")
        np.testing.assert_array_equal(train, all_[:market.train_end])
        np.testing.assert_array_equal(test,  all_[market.train_end:])


class TestSyntheticMarketReproducibility:
    def test_same_seed_same_prices(self):
        m1 = SyntheticMarket(n_stocks=20, n_days=100, seed=7)
        m2 = SyntheticMarket(n_stocks=20, n_days=100, seed=7)
        np.testing.assert_array_equal(m1.prices("all"), m2.prices("all"))

    def test_different_seed_different_prices(self):
        m1 = SyntheticMarket(n_stocks=20, n_days=100, seed=7)
        m2 = SyntheticMarket(n_stocks=20, n_days=100, seed=8)
        assert not np.allclose(m1.prices("all"), m2.prices("all"))


class TestSyntheticMarketPlantedAlpha:
    def test_alpha_returns_nonzero_where_active(self):
        alpha = PlantedAlpha("mom_1m", strength_bps=10.0, halflife_days=20, start_day=0)
        m = SyntheticMarket(n_stocks=50, n_days=200, planted_alphas=[alpha], seed=0)
        ar = m.alpha_returns()
        # After warmup (day 1+), alpha returns should have non-trivial signal
        assert not np.all(ar[2:] == 0.0)

    def test_no_alpha_returns_zero(self):
        m = SyntheticMarket(n_stocks=20, n_days=100, planted_alphas=[], seed=0)
        ar = m.alpha_returns()
        assert np.all(ar == 0.0)

    def test_alpha_start_day_respected(self):
        alpha = PlantedAlpha("mom_1m", strength_bps=10.0, halflife_days=20, start_day=50)
        m = SyntheticMarket(n_stocks=50, n_days=200, planted_alphas=[alpha], seed=0)
        ar = m.alpha_returns()
        # Before start_day, alpha returns should be zero
        assert np.all(ar[:50] == 0.0)
        # After start_day, should be non-zero
        assert not np.all(ar[52:] == 0.0)

    def test_stronger_alpha_larger_alpha_returns(self):
        weak   = SyntheticMarket(n_stocks=50, n_days=200,
                                  planted_alphas=[PlantedAlpha("mom_1m", 1.0, 20)], seed=0)
        strong = SyntheticMarket(n_stocks=50, n_days=200,
                                  planted_alphas=[PlantedAlpha("mom_1m", 10.0, 20)], seed=0)
        # Stronger alpha → larger absolute returns
        assert np.abs(strong.alpha_returns()).mean() > np.abs(weak.alpha_returns()).mean()
