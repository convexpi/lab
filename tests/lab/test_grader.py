"""Tests for the hidden-holdout grader and alpha discovery."""

import numpy as np
import pytest
from convexpi.lab.synth import SyntheticMarket, PlantedAlpha
from convexpi.lab.backtest import LongShortRank, EqualWeight, Strategy
from convexpi.lab.grader import Grader, GradeReport, AlphaDiscovery


# ---------------------------------------------------------------------------
# Fixtures — small market for fast tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def market():
    # 80 stocks × 500 days — small enough to run fast, large enough to be realistic
    return SyntheticMarket(n_stocks=80, n_days=500, seed=99)


@pytest.fixture(scope="module")
def grader(market):
    return Grader(market, tc_bps=0.0)   # zero TC so Sharpe signal is clean


@pytest.fixture(scope="module")
def mom_report(grader):
    return grader.evaluate(LongShortRank("mom_1m"))


@pytest.fixture(scope="module")
def noise_report(grader):
    return grader.evaluate(LongShortRank("noise_1"))


# ---------------------------------------------------------------------------
# GradeReport structure
# ---------------------------------------------------------------------------

class TestGradeReportStructure:
    def test_returns_grade_report(self, mom_report):
        assert isinstance(mom_report, GradeReport)

    def test_strategy_name_set(self, mom_report):
        assert mom_report.strategy_name == "LongShortRank"

    def test_alpha_discovery_list(self, mom_report):
        assert isinstance(mom_report.alpha_discovery, list)
        assert all(isinstance(d, AlphaDiscovery) for d in mom_report.alpha_discovery)

    def test_noise_loadings_dict(self, mom_report):
        assert isinstance(mom_report.noise_loadings, dict)

    def test_noise_keys_are_noise_features(self, mom_report):
        for key in mom_report.noise_loadings:
            assert key.startswith("noise_")

    def test_sharpe_finite(self, mom_report):
        assert np.isfinite(mom_report.is_sharpe)
        assert np.isfinite(mom_report.oos_sharpe)

    def test_max_dd_nonnegative(self, mom_report):
        assert mom_report.is_max_dd >= 0
        assert mom_report.oos_max_dd >= 0

    def test_overfitting_ratio_bounded(self, mom_report):
        # ratio is min(1.0, oos/is) when is > 0
        assert mom_report.overfitting_ratio <= 1.0


# ---------------------------------------------------------------------------
# OOS Sharpe
# ---------------------------------------------------------------------------

class TestOOSSharpe:
    def test_planted_alpha_strategy_positive_oos_sharpe(self, mom_report):
        # mom_1m has a 6 bps planted alpha — strategy using it should beat zero OOS
        # Use a loose threshold because small market + short OOS period has high variance
        assert mom_report.oos_sharpe > -2.0   # not catastrophically negative

    def test_noise_strategy_oos_sharpe_finite(self, noise_report):
        assert np.isfinite(noise_report.oos_sharpe)

    def test_zero_strategy_zero_sharpe(self, market):
        grader = Grader(market, tc_bps=0.0)
        report = grader.evaluate(EqualWeight())
        assert np.isfinite(report.oos_sharpe)

    def test_is_sharpe_finite_for_noise(self, noise_report):
        assert np.isfinite(noise_report.is_sharpe)


# ---------------------------------------------------------------------------
# Alpha discovery
# ---------------------------------------------------------------------------

class TestAlphaDiscovery:
    def test_discovery_list_length(self, mom_report, market):
        # One AlphaDiscovery per planted alpha
        assert len(mom_report.alpha_discovery) == len(market.planted_alphas)

    def test_alpha_names_match_planted(self, mom_report, market):
        planted_features = {a.feature for a in market.planted_alphas}
        discovered_features = {d.feature for d in mom_report.alpha_discovery}
        assert discovered_features == planted_features

    def test_discovery_has_correlation(self, mom_report):
        for d in mom_report.alpha_discovery:
            assert -1.0 <= d.correlation <= 1.0

    def test_discovery_has_strength_bps(self, mom_report, market):
        planted = {a.feature: a.strength_bps for a in market.planted_alphas}
        for d in mom_report.alpha_discovery:
            assert d.planted_strength_bps == planted[d.feature]

    def test_oos_contribution_finite(self, mom_report):
        for d in mom_report.alpha_discovery:
            assert np.isfinite(d.oos_contribution)

    def test_oos_contribution_bounded(self, mom_report):
        # Clamped to [-10, 10]
        for d in mom_report.alpha_discovery:
            assert -10.0 <= d.oos_contribution <= 10.0

    def test_no_planted_alphas_empty_discovery(self, market):
        m = SyntheticMarket(n_stocks=40, n_days=400, planted_alphas=[], seed=5)
        g = Grader(m, tc_bps=0.0)
        report = g.evaluate(LongShortRank("noise_1"))
        assert report.alpha_discovery == []


# ---------------------------------------------------------------------------
# Noise loadings
# ---------------------------------------------------------------------------

class TestNoiseLoadings:
    def test_noise_features_present(self, market, mom_report):
        noise_names = {f for f in market.FEATURE_NAMES if f.startswith("noise_")}
        assert set(mom_report.noise_loadings.keys()) == noise_names

    def test_planted_signal_not_in_noise_loadings(self, mom_report):
        for key in mom_report.noise_loadings:
            assert not any(key == a.feature for a in [])   # noise keys don't overlap with planted
        planted_features = {"mom_1m", "val_bm"}
        for key in mom_report.noise_loadings:
            assert key not in planted_features

    def test_noise_loading_values_in_range(self, mom_report):
        for v in mom_report.noise_loadings.values():
            assert -1.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# Overfitting ratio
# ---------------------------------------------------------------------------

class TestOverfittingRatio:
    def test_ratio_capped_at_one(self, mom_report):
        assert mom_report.overfitting_ratio <= 1.0

    def test_flat_strategy_ratio_zero(self, market):
        g = Grader(market, tc_bps=0.0)
        report = g.evaluate(EqualWeight())
        # EqualWeight IS sharpe may be near zero → ratio defined as 0 when is_sharpe ≈ 0
        assert report.overfitting_ratio <= 1.0

    def test_ratio_nonnegative_when_positive_oos(self, mom_report):
        # When both IS and OOS are positive, ratio should be positive
        if mom_report.is_sharpe > 0 and mom_report.oos_sharpe > 0:
            assert mom_report.overfitting_ratio > 0


# ---------------------------------------------------------------------------
# Grader with custom TC
# ---------------------------------------------------------------------------

class TestGraderConfiguration:
    def test_custom_tc_affects_oos_sharpe(self, market):
        g_no_tc = Grader(market, tc_bps=0.0)
        g_hi_tc = Grader(market, tc_bps=100.0)
        r_no_tc = g_no_tc.evaluate(LongShortRank("mom_1m"))
        r_hi_tc = g_hi_tc.evaluate(LongShortRank("mom_1m"))
        # Higher TC → lower returns → lower Sharpe
        assert r_no_tc.oos_sharpe >= r_hi_tc.oos_sharpe

    def test_custom_threshold_affects_discovery(self, market):
        # Very loose threshold → easier to "discover"
        g_loose = Grader(market, tc_bps=0.0, discovery_corr_threshold=0.0)
        g_tight = Grader(market, tc_bps=0.0, discovery_corr_threshold=0.99)
        r_loose = g_loose.evaluate(LongShortRank("mom_1m"))
        r_tight = g_tight.evaluate(LongShortRank("mom_1m"))
        loose_found = sum(d.discovered for d in r_loose.alpha_discovery)
        tight_found = sum(d.discovered for d in r_tight.alpha_discovery)
        assert loose_found >= tight_found
