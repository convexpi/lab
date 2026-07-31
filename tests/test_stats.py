"""Tests for the selection-bias-aware Sharpe statistics."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy"))

from stats import (  # noqa: E402
    deflated_sharpe, expected_max_sharpe, norm_cdf, norm_ppf, probabilistic_sharpe,
)


@pytest.mark.parametrize("p,expected", [
    (0.5, 0.0), (0.975, 1.959964), (0.025, -1.959964), (0.99, 2.326348), (0.001, -3.090232),
])
def test_norm_ppf_matches_known_quantiles(p, expected):
    assert norm_ppf(p) == pytest.approx(expected, abs=1e-5)


def test_norm_ppf_inverts_norm_cdf():
    for x in (-3.0, -1.0, -0.25, 0.0, 0.25, 1.0, 3.0):
        assert norm_ppf(norm_cdf(x)) == pytest.approx(x, abs=1e-6)


def test_expected_max_grows_with_trials():
    """More strategies tried means a higher bar — that is the whole point."""
    v = 0.01
    vals = [expected_max_sharpe(n, v) for n in (2, 10, 100, 1000)]
    assert vals == sorted(vals)
    assert all(b > a for a, b in zip(vals, vals[1:]))


def test_expected_max_is_zero_without_trials_or_spread():
    assert expected_max_sharpe(1, 0.01) == 0.0
    assert expected_max_sharpe(50, 0.0) == 0.0


def test_expected_max_matches_simulation():
    """Sanity-check the closed form against the empirical max of iid normal Sharpes."""
    rng = np.random.default_rng(7)
    n_trials, sd = 50, 0.1
    empirical = np.mean([rng.normal(0, sd, n_trials).max() for _ in range(4000)])
    assert expected_max_sharpe(n_trials, sd ** 2) == pytest.approx(empirical, rel=0.05)


def test_probabilistic_sharpe_is_half_at_the_benchmark():
    assert probabilistic_sharpe(0.1, 250, benchmark=0.1) == pytest.approx(0.5)


def test_probabilistic_sharpe_rises_with_sample_length():
    a = probabilistic_sharpe(0.05, 60)
    b = probabilistic_sharpe(0.05, 600)
    assert b > a, "a longer track record should raise confidence in the same Sharpe"


def test_negative_skew_and_fat_tails_lower_confidence():
    base = probabilistic_sharpe(0.1, 250, skew=0.0, kurtosis=3.0)
    skewed = probabilistic_sharpe(0.1, 250, skew=-1.5, kurtosis=3.0)
    fat = probabilistic_sharpe(0.1, 250, skew=0.0, kurtosis=9.0)
    assert skewed < base and fat < base


def test_deflated_sharpe_penalises_a_crowded_leaderboard():
    """The same track record is worth less when it won out over more competitors."""
    kw = dict(sharpe=0.12, n_obs=250, sharpe_variance=0.01)
    few = deflated_sharpe(n_trials=2, **kw)
    many = deflated_sharpe(n_trials=500, **kw)
    assert few > many
    assert 0.0 <= many <= 1.0 and 0.0 <= few <= 1.0


def test_deflated_sharpe_rejects_the_luckiest_of_many():
    """A Sharpe typical of the null, selected as best of 100, should not read as a real result."""
    n_obs, sd = 21, 0.1
    lucky = expected_max_sharpe(100, sd ** 2)      # exactly what luck alone would produce
    assert deflated_sharpe(lucky, n_obs, 100, sd ** 2) < 0.6


def test_deflated_sharpe_still_credits_a_strong_long_record():
    """The correction must not flatten everything — real skill over a long sample survives it.

    Units matter for calibration: 0.03 is a realistic spread of *daily* Sharpes across a field of
    models (≈0.5 annualised). Using a spread of 0.1 daily (≈1.6 annualised) would say the field is
    wildly dispersed, which correctly sets the bar above the observed Sharpe — see the companion
    test below.
    """
    strong = deflated_sharpe(0.15, 2000, 20, 0.03 ** 2)
    assert strong > 0.95, "a large, sustained edge must survive the correction"


def test_deflated_sharpe_defers_to_a_wildly_dispersed_field():
    """When trial Sharpes scatter that far, the best of them is expected to look good by luck."""
    assert deflated_sharpe(0.15, 2000, 20, 0.1 ** 2) < 0.1


def test_annualisation_is_the_callers_job():
    """Guard the unit convention: these functions are per-period, not annualised."""
    daily = 0.1
    assert probabilistic_sharpe(daily, 250) != probabilistic_sharpe(daily * math.sqrt(252), 250)
