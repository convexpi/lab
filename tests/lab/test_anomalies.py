"""Tests for anomaly stats computation (offline — uses synthetic factor data)."""

import math
import pytest
import numpy as np

from convexpi.lab.anomalies import (
    AnomalySpec,
    compute_factor_stats,
    _CATALOGUE,
)


# ---------------------------------------------------------------------------
# Synthetic French-format table builder
# ---------------------------------------------------------------------------

def _make_table(
    factor: str,
    years: range,
    mean_pct: float = 0.04,
    vol_pct: float = 0.8,
    seed: int = 0,
) -> dict:
    """Generate a synthetic daily French-format table {YYYYMMDD: {factor: value}}."""
    rng = np.random.default_rng(seed)
    table: dict = {}
    for year in years:
        for month in range(1, 13):
            days = 21  # ~21 trading days per month
            for day_idx in range(1, days + 1):
                date_key = f"{year}{month:02d}{day_idx:02d}"
                val = float(rng.normal(mean_pct, vol_pct))
                table[date_key] = {factor: val}
    return table


# ---------------------------------------------------------------------------
# AnomalySpec tests
# ---------------------------------------------------------------------------

class TestAnomalySpec:
    def test_catalogue_non_empty(self):
        assert len(_CATALOGUE) >= 4

    def test_each_spec_has_required_fields(self):
        for spec in _CATALOGUE:
            assert spec.id
            assert spec.name
            assert spec.factor
            assert spec.pub_year > 1900
            assert spec.description

    def test_pub_years_sensible(self):
        for spec in _CATALOGUE:
            assert 1960 <= spec.pub_year <= 2025

    def test_data_start_before_pub_year(self):
        for spec in _CATALOGUE:
            assert spec.data_start < spec.pub_year


# ---------------------------------------------------------------------------
# compute_factor_stats tests
# ---------------------------------------------------------------------------

class TestComputeFactorStats:
    def _simple_spec(self, factor="SMB", pub_year=1981) -> AnomalySpec:
        return AnomalySpec(
            id="test",
            name="Test",
            factor=factor,
            dataset="ff3_daily",
            paper="Test (1900)",
            pub_year=pub_year,
            description="test factor",
            data_start=1970,
        )

    def test_returns_required_keys(self):
        spec = self._simple_spec()
        table = _make_table("SMB", range(1970, 1985))
        result = compute_factor_stats(spec, table)
        required = {
            "id", "name", "factor", "paper", "pub_year", "description",
            "is_period", "oos_period",
            "is_return", "is_sharpe", "is_vol",
            "oos_return", "oos_sharpe", "oos_vol",
            "decay_pct", "status",
        }
        assert required.issubset(result.keys())

    def test_is_period_ends_before_pub_year(self):
        spec = self._simple_spec(pub_year=1981)
        table = _make_table("SMB", range(1970, 1990))
        result = compute_factor_stats(spec, table)
        is_end = int(result["is_period"].split("–")[1])
        assert is_end < spec.pub_year

    def test_oos_period_starts_at_pub_year(self):
        spec = self._simple_spec(pub_year=1981)
        table = _make_table("SMB", range(1970, 1990))
        result = compute_factor_stats(spec, table)
        oos_start = int(result["oos_period"].split("–")[0])
        assert oos_start == spec.pub_year

    def test_positive_mean_gives_positive_sharpe(self):
        spec = self._simple_spec()
        # large positive mean, tiny vol → clearly positive Sharpe
        table = _make_table("SMB", range(1970, 1985), mean_pct=0.5, vol_pct=0.01)
        result = compute_factor_stats(spec, table)
        assert result["is_sharpe"] > 0

    def test_negative_mean_gives_negative_sharpe(self):
        spec = self._simple_spec()
        table = _make_table("SMB", range(1970, 1985), mean_pct=-0.5, vol_pct=0.01)
        result = compute_factor_stats(spec, table)
        assert result["is_sharpe"] < 0

    def test_status_alive_high_oos_sharpe(self):
        """High OOS mean → status 'alive'."""
        spec = self._simple_spec(pub_year=1975)
        is_table = _make_table("SMB", range(1970, 1975), mean_pct=0.5, vol_pct=0.01)
        oos_table = _make_table("SMB", range(1975, 1990), mean_pct=0.5, vol_pct=0.01)
        table = {**is_table, **oos_table}
        result = compute_factor_stats(spec, table)
        assert result["status"] == "alive"

    def test_status_dead_negative_oos_sharpe(self):
        """Negative OOS return → status 'dead'."""
        spec = self._simple_spec(pub_year=1975)
        is_table = _make_table("SMB", range(1970, 1975), mean_pct=0.3, vol_pct=0.01)
        oos_table = _make_table("SMB", range(1975, 1990), mean_pct=-0.3, vol_pct=0.01)
        table = {**is_table, **oos_table}
        result = compute_factor_stats(spec, table)
        assert result["status"] == "dead"

    def test_sharpe_magnitude(self):
        """Annualized Sharpe formula: mean_pct*252 / (vol_pct*sqrt(252)).
        Use tiny vol so the sample converges quickly over just 5 years."""
        spec = self._simple_spec(pub_year=1975)
        # vol=0.001 → signal-to-noise is huge → sample mean ≈ 0.04
        table = _make_table("SMB", range(1970, 1975), mean_pct=0.04, vol_pct=0.001)
        result = compute_factor_stats(spec, table)
        expected = (0.04 * 252) / (0.001 * math.sqrt(252))  # ≈ 634
        assert abs(result["is_sharpe"] - expected) / abs(expected) < 0.05

    def test_no_is_data_returns_zero_sharpe(self):
        """If all data is after pub_year, IS sharpe should be 0."""
        spec = self._simple_spec(pub_year=1970)
        table = _make_table("SMB", range(1975, 1985))  # all post-pub
        result = compute_factor_stats(spec, table)
        assert result["is_sharpe"] == 0.0

    def test_decay_pct_increases_with_oos_decline(self):
        """Bigger OOS decline → bigger decay_pct."""
        spec = self._simple_spec(pub_year=1975)
        # Scenario A: moderate OOS decline
        is_t   = _make_table("SMB", range(1970, 1975), mean_pct=0.3, vol_pct=0.01)
        oos_a  = _make_table("SMB", range(1975, 1990), mean_pct=0.2, vol_pct=0.01)
        oos_b  = _make_table("SMB", range(1975, 1990), mean_pct=-0.1, vol_pct=0.01)
        result_a = compute_factor_stats(spec, {**is_t, **oos_a})
        result_b = compute_factor_stats(spec, {**is_t, **oos_b})
        assert result_b["decay_pct"] > result_a["decay_pct"]

    def test_missing_factor_returns_zero(self):
        """Table without the expected factor column → zero stats."""
        spec = self._simple_spec(factor="MISSING")
        table = _make_table("SMB", range(1970, 1985))
        result = compute_factor_stats(spec, table)
        assert result["is_sharpe"] == 0.0
        assert result["oos_sharpe"] == 0.0
