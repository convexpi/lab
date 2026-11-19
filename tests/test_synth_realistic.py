"""The realistic (GARCH) market mode is opt-in: default market economics must stay unchanged,
and the GARCH mode must add volatility clustering while preserving the planted alpha.
"""
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from convexpi.lab import SyntheticMarket

# Snapshots derive from the original byte-verified NumPy 1.26.4 markets. NumPy/BLAS
# upgrades change last-place rounding (~5e-13 in prices), so portable regression
# checks use tight numeric tolerances. Repeated generation on one runtime must
# still be byte-identical. See fixtures/README.md for provenance.
SEEDS = (42, 7, 2026)


def _clustering(m):
    r = m.returns("all")
    ac = []
    for n in range(r.shape[1]):
        x = r[:, n] ** 2 - (r[:, n] ** 2).mean()
        ac.append(np.sum(x[1:] * x[:-1]) / np.sum(x * x))
    return float(np.mean(ac))


def _alpha_ic(m):
    r = m.returns("all")
    f = m.features("all")["mom_1m"]
    return float(np.nanmean([np.corrcoef(rankdata(f[t]), rankdata(r[t]))[0, 1] for t in range(len(r))]))


def test_default_market_matches_reference_and_is_deterministic():
    with np.load(Path(__file__).parent / "fixtures" / "default_market.npz") as gold:
        for seed in SEEDS:
            prices = SyntheticMarket(seed=seed).prices("all")
            np.testing.assert_array_equal(prices, SyntheticMarket(seed=seed).prices("all"))
            assert prices.shape == (1260, 200)
            for name, actual in (("daily_mean", prices.mean(axis=1)),
                                 ("daily_std", prices.std(axis=1)),
                                 ("final_prices", prices[-1])):
                np.testing.assert_allclose(actual, gold[f"{seed}_{name}"], rtol=1e-12, atol=1e-12)


def test_garch_is_deterministic():
    a = SyntheticMarket(seed=42, idio_process="garch").prices("all")
    b = SyntheticMarket(seed=42, idio_process="garch").prices("all")
    assert np.array_equal(a, b)


def test_garch_adds_clustering_and_preserves_alpha():
    mt = SyntheticMarket(seed=42, idio_process="t")
    mg = SyntheticMarket(seed=42, idio_process="garch")
    assert _clustering(mg) > _clustering(mt) + 0.02   # meaningfully more volatility clustering
    assert _alpha_ic(mg) > 0                           # planted alpha still recoverable
    assert not np.allclose(mt.prices("all"), mg.prices("all"))


def test_market_exhibits_stylized_facts():
    """Use finmlsim.stylized as an independent oracle: the market must LOOK real (fat tails,
    ~uncorrelated returns), and the garch mode must show more volatility clustering."""
    import finmlsim as fms

    def facts(m, key):
        r = m.returns("all")
        return float(np.mean([fms.stylized.summary(r[:, n])[key] for n in range(0, r.shape[1], 10)]))

    mt = SyntheticMarket(seed=42)                       # default (Student-t)
    assert facts(mt, "excess_kurtosis") > 0.5           # heavy tails
    assert abs(facts(mt, "ret_acf_lag1")) < 0.1         # returns ≈ uncorrelated (no free direction edge)

    mg = SyntheticMarket(seed=42, idio_process="garch")
    assert facts(mg, "sq_ret_acf_mean") > facts(mt, "sq_ret_acf_mean")  # more volatility clustering
