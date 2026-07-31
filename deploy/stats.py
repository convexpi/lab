"""
stats.py — Sharpe statistics that account for how many strategies were tried.

A leaderboard is a maximum, and maxima are biased. Rank N models by Sharpe and the winner's score
is not an estimate of its skill — it is an estimate of its skill plus whatever luck it needed to
come first. With enough entrants somebody posts a spectacular Sharpe from noise alone, and the
board presents that as the best model on the site.

The correction is Bailey & López de Prado's Deflated Sharpe Ratio: work out how high the best
Sharpe would be expected to run under the null that no model has any skill, then ask how confident
we can be that the observed Sharpe beats *that* benchmark rather than beating zero.

Everything here works in per-period (daily) units; annualise only for display.
"""
from __future__ import annotations

import math

EULER_MASCHERONI = 0.5772156649015329


def norm_cdf(x: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Standard normal inverse CDF (Acklam's rational approximation, |error| < 1.15e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5])*q / \
           (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)


def expected_max_sharpe(n_trials: int, sharpe_variance: float) -> float:
    """The Sharpe the *best* of `n_trials` skill-less strategies would be expected to post.

    This is the benchmark a leaderboard winner actually has to beat. `sharpe_variance` is the
    variance of the Sharpe ratios across the trials, in the same per-period units as the result.
    """
    if n_trials <= 1 or sharpe_variance <= 0:
        return 0.0
    sd = math.sqrt(sharpe_variance)
    n = float(n_trials)
    # Bailey & López de Prado (2014), eq. for E[max] of n iid normal draws.
    return sd * ((1 - EULER_MASCHERONI) * norm_ppf(1 - 1 / n)
                 + EULER_MASCHERONI * norm_ppf(1 - 1 / (n * math.e)))


def probabilistic_sharpe(sharpe: float, n_obs: int, skew: float = 0.0,
                         kurtosis: float = 3.0, benchmark: float = 0.0) -> float:
    """P(true Sharpe > `benchmark`) given the observed Sharpe and the returns' shape.

    Non-normality matters: negative skew and fat tails — exactly what a short-vol or momentum
    strategy produces — make a given Sharpe less trustworthy than the normal case implies.
    All Sharpe arguments are per-period.
    """
    if n_obs < 2:
        return 0.0
    denom = 1.0 - skew * sharpe + ((kurtosis - 1.0) / 4.0) * sharpe ** 2
    if denom <= 0:
        return 0.0
    return norm_cdf((sharpe - benchmark) * math.sqrt(n_obs - 1) / math.sqrt(denom))


def deflated_sharpe(sharpe: float, n_obs: int, n_trials: int, sharpe_variance: float,
                    skew: float = 0.0, kurtosis: float = 3.0) -> float:
    """P(true Sharpe > 0) after accounting for having tried `n_trials` strategies.

    Returns a probability in [0, 1]. Read it as confidence that the model is not simply the
    luckiest of the entrants: 0.95+ is a genuine result, 0.5 is a coin flip dressed up as skill.
    """
    benchmark = expected_max_sharpe(n_trials, sharpe_variance)
    return probabilistic_sharpe(sharpe, n_obs, skew, kurtosis, benchmark)
