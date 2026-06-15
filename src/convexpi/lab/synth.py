"""
synth.py — Synthetic equity panel generator for the Lab.

Generates a realistic cross-section: N stocks × T days, daily prices and
features, with a multi-factor return model, regime-switching volatility,
fat-tailed idiosyncratic shocks, and planted alpha signals of known strength.

The signature pedagogical feature: ground truth is known. The grader can
verify which signals students actually discovered and which were noise.

Quick start:
    from synth import SyntheticMarket, PlantedAlpha

    market = SyntheticMarket(n_stocks=200, n_days=1260, seed=42)

    # Student-visible data (train split)
    prices    = market.prices("train")          # (n_train, n_stocks)
    features  = market.features("train")        # dict str -> (n_train, n_stocks)

    # Hidden holdout (grader only)
    oos_prices = market.prices("test")

    # Ground truth (grader only)
    alphas = market.alpha_returns()             # (n_days, n_stocks)

Return model:
    r_{i,t} = Σ_k β_{ik} f_{k,t} + ε_{i,t} + α_{i,t}

where α_{i,t} = Σ_j θ_j · rank_normalize(signal_{i,j,t-1})
is the planted alpha — instructor-controlled, hidden from students.

Features exposed to students:
    mom_1m, mom_3m, mom_12m   — price momentum (skip-1m for 12m)
    val_bm                    — value: book-to-market (quarterly updates)
    qual_roe                  — quality: return on equity (annual updates)
    size_cap                  — size: log market cap
    vol_1m                    — realized 1-month volatility
    reversal_1w               — short-term reversal (contrarian 1-week)
    noise_1, noise_2, noise_3 — pure noise (no planted alpha)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Planted alpha specification
# ---------------------------------------------------------------------------

@dataclass
class PlantedAlpha:
    """
    One embedded alpha signal.

    The feature `feature` predicts the next day's cross-sectional return with
    strength `strength_bps / 10000` per unit of rank (rank is normalized to
    [-0.5, 0.5] cross-sectionally). For example, with strength_bps=2.0, the
    top-ranked stock earns +1 bps more than average and the bottom-ranked
    stock earns -1 bps less — equivalent to a ~2% annualized long-short spread
    for a top/bottom decile portfolio of 200 stocks.
    """
    feature: str           # which feature name carries this signal
    strength_bps: float    # daily alpha per unit rank, in basis points
    halflife_days: int     # for reference / decay-weighted variants
    start_day: int = 0     # alpha activates at this day (allows nonstationarity)
    end_day: int = -1      # -1 = runs to end of sample


def _default_alphas() -> list[PlantedAlpha]:
    """Two planted alphas matching classic factor anomalies."""
    return [
        PlantedAlpha("mom_1m", strength_bps=6.0, halflife_days=20),
        PlantedAlpha("val_bm", strength_bps=1.5, halflife_days=60, start_day=63),
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cross_rank(x: np.ndarray) -> np.ndarray:
    """Cross-sectionally rank-normalize to [-0.5, 0.5]. NaN → 0."""
    out = np.zeros(len(x), dtype=float)
    valid = ~np.isnan(x)
    n = valid.sum()
    if n < 2:
        return out
    ranks = np.argsort(np.argsort(x[valid])).astype(float)
    out[valid] = ranks / (n - 1) - 0.5
    return out


def _cs_zscore(x: np.ndarray) -> np.ndarray:
    """Cross-sectional z-score. NaN passthrough."""
    valid = ~np.isnan(x)
    if valid.sum() < 2:
        return x.copy()
    mu = np.nanmean(x)
    sigma = np.nanstd(x)
    return (x - mu) / (sigma + 1e-9)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

class SyntheticMarket:
    """
    Synthetic equity panel with planted alphas.

    Parameters
    ----------
    n_stocks : int
        Number of synthetic stocks (default 200).
    n_days : int
        Total trading days (default 1260 ≈ 5 years).
    n_factors : int
        Number of latent return factors, max 5 (default 3).
    planted_alphas : list[PlantedAlpha] | None
        Alpha signals to embed. None → default two-signal setup.
    train_frac : float
        Fraction of days shown to students; rest is hidden holdout.
    tc_bps : float
        Reference one-way transaction cost in basis points.
    seed : int
        Random seed — same seed always yields identical data.
    """

    FEATURE_NAMES = [
        "mom_1m", "mom_3m", "mom_12m",
        "val_bm", "qual_roe", "size_cap",
        "vol_1m", "reversal_1w",
        "noise_1", "noise_2", "noise_3",
    ]

    def __init__(
        self,
        n_stocks: int = 200,
        n_days: int = 1260,
        n_factors: int = 3,
        planted_alphas: Optional[list[PlantedAlpha]] = None,
        train_frac: float = 0.70,
        tc_bps: float = 10.0,
        seed: int = 42,
        *,
        n_assets: Optional[int] = None,  # alias for n_stocks
    ):
        self.n_stocks = n_assets if n_assets is not None else n_stocks
        self.n_days = n_days
        self.n_factors = min(n_factors, 5)
        self.planted_alphas = planted_alphas if planted_alphas is not None else _default_alphas()
        self.train_frac = train_frac
        self.tc_bps = tc_bps
        self.rng = np.random.default_rng(seed)

        self._prices: Optional[np.ndarray] = None      # (T, N)
        self._features: Optional[dict] = None
        self._alpha_returns: Optional[np.ndarray] = None

        self._generate()

    @property
    def n_assets(self) -> int:
        return self.n_stocks

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def train_end(self) -> int:
        return int(self.n_days * self.train_frac)

    @property
    def stock_ids(self) -> list[str]:
        return [f"STK{i:04d}" for i in range(self.n_stocks)]

    def prices(self, split: str = "train") -> np.ndarray:
        """Price panel (n_days_split, n_stocks). Starting price ≈ $20–$150."""
        return self._split(self._prices, split)

    def returns(self, split: str = "train") -> np.ndarray:
        """Daily simple returns (n_days_split - 1, n_stocks)."""
        p = self._split(self._prices, split)
        return p[1:] / p[:-1] - 1

    def features(self, split: str = "train") -> dict[str, np.ndarray]:
        """
        Dict of feature_name → (n_days_split, n_stocks).
        NaN where the lookback window is insufficient (early rows).
        Each feature is cross-sectionally z-scored daily.
        """
        return {k: self._split(v, split) for k, v in self._features.items()}

    def alpha_returns(self) -> np.ndarray:
        """
        GRADER ONLY — the planted alpha contribution to each stock's daily return.
        Shape (n_days, n_stocks). Do not expose to students.
        """
        return self._alpha_returns

    def describe(self) -> None:
        """Print a summary of the synthetic market."""
        print(f"SyntheticMarket: {self.n_stocks} stocks × {self.n_days} days")
        print(f"  train: days 0–{self.train_end-1}  ({self.train_end} days)")
        print(f"  test:  days {self.train_end}–{self.n_days-1}  ({self.n_days - self.train_end} days)")
        p = self._prices
        rets = p[1:] / p[:-1] - 1
        print(f"  cross-sectional mean daily return: {rets.mean()*100:.3f}%")
        print(f"  cross-sectional mean daily vol:    {rets.std()*100:.3f}%")
        print(f"  planted alphas:")
        for a in self.planted_alphas:
            print(f"    {a.feature}: {a.strength_bps:.1f} bps/rank-unit  "
                  f"halflife={a.halflife_days}d  "
                  f"active days {a.start_day}–{a.end_day if a.end_day >= 0 else self.n_days}")

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _split(self, arr: np.ndarray, split: str) -> np.ndarray:
        if split == "train":
            return arr[:self.train_end]
        if split == "test":
            return arr[self.train_end:]
        if split == "all":
            return arr
        raise ValueError(f"split must be 'train' | 'test' | 'all', got '{split}'")

    def _generate(self):
        rng = self.rng
        N, T, K = self.n_stocks, self.n_days, self.n_factors

        # ---- 1. Regime (2-state Markov: calm / turbulent) ----
        regime = np.zeros(T, dtype=int)
        for t in range(1, T):
            # ~2% chance of switching per day in each direction
            if regime[t-1] == 0:
                regime[t] = int(rng.random() < 0.005)
            else:
                regime[t] = int(rng.random() > 0.03)
        regime_mult = np.where(regime == 0, 1.0, 2.5)  # (T,)

        # ---- 2. Factor returns ----
        base_vols = np.array([0.010, 0.007, 0.006, 0.005, 0.005][:K])
        # Correlation: market factor (0) correlates 0.5 with others, rest 0.25
        corr = np.full((K, K), 0.25)
        np.fill_diagonal(corr, 1.0)
        if K > 1:
            corr[0, 1:] = corr[1:, 0] = 0.5
        chol = np.linalg.cholesky(corr)
        z = rng.standard_normal((T, K))
        factor_rets = (z @ chol.T) * base_vols * regime_mult[:, None]  # (T, K)

        # ---- 3. Stock factor loadings ----
        betas = rng.normal(0.0, 0.4, (N, K))
        if K > 0:
            betas[:, 0] = rng.normal(1.0, 0.15, N)   # market beta ≈ 1
        common = factor_rets @ betas.T                  # (T, N)

        # ---- 4. Idiosyncratic returns (fat-tailed, student-t df=5) ----
        idio_vols = rng.uniform(0.008, 0.022, N)
        df = 5
        t_shocks = rng.standard_t(df, (T, N))
        t_shocks /= np.sqrt(df / (df - 2))             # normalize to σ=1
        idio_rets = t_shocks * idio_vols                # (T, N)

        # ---- 5. Base returns and prices ----
        base_rets = common + idio_rets
        base_rets[0] = 0.0                              # no return on day 0
        start_prices = rng.uniform(20.0, 150.0, N)
        base_prices = start_prices * np.exp(np.cumsum(np.log1p(base_rets), axis=0))

        # ---- 6. Features from base prices ----
        self._features = self._compute_features(base_prices, rng)

        # ---- 7. Planted alpha returns ----
        alpha_rets = np.zeros((T, N))
        for a in self.planted_alphas:
            feat = self._features.get(a.feature)
            if feat is None:
                print(f"Warning: planted feature '{a.feature}' not found, skipping.")
                continue
            end = a.end_day if a.end_day >= 0 else T
            for t in range(max(1, a.start_day + 1), min(T, end + 1)):
                alpha_rets[t] += a.strength_bps / 10000 * _cross_rank(feat[t-1])
        self._alpha_returns = alpha_rets

        # ---- 8. Final prices (base + alpha) ----
        total_rets = base_rets + alpha_rets
        total_rets[0] = 0.0
        self._prices = start_prices * np.exp(np.cumsum(np.log1p(total_rets), axis=0))

    def _compute_features(
        self, prices: np.ndarray, rng: np.random.Generator
    ) -> dict[str, np.ndarray]:
        T, N = prices.shape
        nan_row = np.full(N, np.nan)
        feat: dict[str, np.ndarray] = {}

        # Helper: safe N-day return at day t
        def ret(t: int, lag: int) -> np.ndarray:
            return prices[t] / prices[t - lag] - 1 if t >= lag else nan_row.copy()

        # Momentum
        mom1  = np.array([ret(t, 21)  for t in range(T)])
        mom3  = np.array([ret(t, 63)  for t in range(T)])
        mom12 = np.array([ret(t, 252) for t in range(T)])
        # Skip-1m 12-month (industry standard)
        mom12_skip = np.where(np.isnan(mom12) | np.isnan(mom1), np.nan, mom12 - mom1)

        feat["mom_1m"]  = np.array([_cs_zscore(row) for row in mom1])
        feat["mom_3m"]  = np.array([_cs_zscore(row) for row in mom3])
        feat["mom_12m"] = np.array([_cs_zscore(row) for row in mom12_skip])

        # Short-term reversal (negative 1-week return — contrarian signal)
        rev = np.array([-ret(t, 5) for t in range(T)])
        feat["reversal_1w"] = np.array([_cs_zscore(row) for row in rev])

        # Realized volatility (21-day rolling)
        log_rets = np.zeros((T, N))
        log_rets[1:] = np.log(prices[1:] / prices[:-1])
        vol = np.full((T, N), np.nan)
        for t in range(21, T):
            vol[t] = log_rets[t-20:t+1].std(axis=0) * np.sqrt(252)
        feat["vol_1m"] = np.array([_cs_zscore(row) for row in vol])

        # Value: book-to-market (slow-moving, quarterly updates)
        bm = np.full((T, N), np.nan)
        bm[0] = rng.uniform(-1.5, 1.5, N)
        for t in range(1, T):
            if t % 63 == 0:
                bm[t] = bm[t-1] * 0.8 + rng.normal(0, 0.3, N)
            else:
                bm[t] = bm[t-1]
        feat["val_bm"] = np.array([_cs_zscore(row) for row in bm])

        # Quality: ROE (annual updates)
        roe = np.full((T, N), np.nan)
        roe[0] = rng.normal(0, 1, N)
        for t in range(1, T):
            if t % 252 == 0:
                roe[t] = roe[t-1] * 0.7 + rng.normal(0, 0.4, N)
            else:
                roe[t] = roe[t-1]
        feat["qual_roe"] = np.array([_cs_zscore(row) for row in roe])

        # Size: log market cap (grows with prices)
        log_cap = np.log(prices) + rng.normal(3.0, 0.5, N)
        feat["size_cap"] = np.array([_cs_zscore(row) for row in log_cap])

        # Noise features (no planted alpha — distractors)
        for i in range(1, 4):
            feat[f"noise_{i}"] = rng.standard_normal((T, N))

        return feat
