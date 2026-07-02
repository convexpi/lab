"""The realistic (GARCH) market mode is opt-in: the default DGP must stay byte-identical (grades
depend on it), and the GARCH mode must add volatility clustering while preserving the planted alpha.
"""
import hashlib

import numpy as np
from scipy.stats import rankdata

from convexpi.lab import SyntheticMarket

# Golden hashes of the default (Student-t) market — if these change, grades change. Do not update
# without deliberately re-baselining.
GOLD = {42: "daf0573a4500d002", 7: "808b79bb4b7c1353", 2026: "24b39b7f84fb8d0f"}


def _hash(p):
    return hashlib.sha256(np.ascontiguousarray(p).tobytes()).hexdigest()[:16]


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


def test_default_market_is_byte_identical():
    for seed, gold in GOLD.items():
        assert _hash(SyntheticMarket(seed=seed).prices("all")) == gold, f"default DGP changed for seed {seed}"


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
