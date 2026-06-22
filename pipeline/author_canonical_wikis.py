"""
author_canonical_wikis.py — hand-authored wikis for canonical papers missing them.

A curated batch covering the field-defining papers that the auto-pipeline had not yet reached:
option pricing (Black-Scholes, Heston), behavioural/sentiment (Baker-Wurgler), out-of-sample
prediction and portfolio construction (Welch-Goyal, DeMiguel et al.), machine learning in asset
pricing (Gu-Kelly-Xiu), overfitting/selection bias (Bailey-Lopez de Prado), and the lottery anomaly
(Bali-Cakici-Whitelaw). Public, paper-focused content only.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_canonical_wikis.py --dry-run
    ...                                          python pipeline/author_canonical_wikis.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["5e738c91-5c2d-4bb6-950c-f2875e730c0a"] = """\
# The Pricing of Options and Corporate Liabilities

**Source:** Black, F. & Scholes, M. (1973). *Journal of Political Economy* 81(3), 637–654.

## TL;DR
Derives a closed-form price for a European option by constructing a continuously rebalanced,
risk-free hedge of the option against its underlying. The resulting price depends only on the
underlying price, the strike, time to maturity, the risk-free rate, and the underlying's volatility
— and, remarkably, *not* on the asset's expected return. This is the foundation of modern
derivatives pricing.

## What it solves
How do you value an option when you can trade the underlying continuously? Black and Scholes show
that a portfolio that is long the option and short the right amount of stock (the delta) is locally
riskless, so by no-arbitrage it must earn the risk-free rate. That hedging argument pins down a
unique price.

## The model and its assumptions
- The underlying follows geometric Brownian motion with constant volatility σ and drift.
- Continuous, frictionless trading; no transaction costs or taxes; no dividends.
- A constant risk-free rate; unlimited borrowing/lending and short-selling.
- No arbitrage.

Under these assumptions the option price solves the Black-Scholes partial differential equation, and
the call price is C = S·N(d₁) − K·e^(−rT)·N(d₂), where d₁ = [ln(S/K) + (r + σ²/2)T] / (σ√T) and
d₂ = d₁ − σ√T. Equivalently, the option is priced as the discounted expectation of its payoff under
the risk-neutral measure.

## Why it matters
- **Implied volatility:** inverting the formula for σ given a market price defines implied vol — the
  market's language for option prices.
- **The Greeks:** the partial derivatives (delta, gamma, vega, theta, rho) drive hedging and risk
  management across every derivatives desk.
- **Risk-neutral valuation:** the insight that derivatives are priced under a risk-adjusted measure
  generalises far beyond options.
- It launched an industry and earned the 1997 Nobel (with Merton, who extended it the same year).

## Limitations and risks
- **Constant volatility is false:** real option prices imply a volatility *smile/skew*, motivating
  stochastic-volatility (Heston, 1993) and local-volatility (Dupire, 1994) models.
- **No jumps / thin tails:** the lognormal assumption understates crash risk — starkly exposed by
  the 1987 crash, after which equity-index skew became permanent.
- **Frictions:** continuous costless hedging is impossible; discrete hedging and costs create error.
- **American/early exercise and dividends** require modifications.

## Key references
- Black, F. & Scholes, M. (1973) — *The Pricing of Options and Corporate Liabilities* — Journal of Political Economy
- Merton, R. (1973) — *Theory of Rational Option Pricing* — Bell Journal of Economics
- Heston, S. (1993) — *A Closed-Form Solution for Options with Stochastic Volatility* — Review of Financial Studies
- Dupire, B. (1994) — *Pricing with a Smile* — Risk
"""

WIKIS["24d3481a-87fb-4108-8d5a-97e42b3545a5"] = """\
# A Closed-Form Solution for Options with Stochastic Volatility

**Source:** Heston, S. L. (1993). *Review of Financial Studies* 6(2), 327–343.

## TL;DR
Extends Black-Scholes by letting volatility itself be random — a mean-reverting square-root process
correlated with the asset price. Heston derives a semi-closed-form option price (via the
characteristic function and Fourier inversion) that reproduces the volatility smile and skew that
Black-Scholes cannot, while remaining tractable enough to calibrate to market prices.

## What it solves
Black-Scholes assumes constant volatility, which is contradicted by the market's implied-volatility
smile/skew and by the empirical leverage effect (volatility rises when prices fall). Heston's model
captures both with a small number of economically interpretable parameters.

## The model
The asset and its variance v follow:
- dS = μS dt + √v · S dW₁
- dv = κ(θ − v) dt + σ_v · √v dW₂
- corr(dW₁, dW₂) = ρ

with κ the speed of mean reversion, θ the long-run variance, σ_v the volatility of volatility, and ρ
the correlation that generates skew (a negative ρ produces the equity-index skew). The option price
is obtained by Fourier-inverting the model's characteristic function — fast enough for repeated
calibration.

## Why it matters
- **Fits the smile:** with four parameters it matches a cross-section of implied vols far better than
  Black-Scholes, and ρ ties the skew to the leverage effect.
- **Workhorse for exotics and vol trading:** the standard benchmark stochastic-volatility model;
  calibrated daily on desks and used to price path-dependent and volatility derivatives.
- **Analytical tractability:** the characteristic-function approach became a template for affine
  models throughout derivatives pricing.

## Limitations and risks
- **No jumps:** short-maturity skew is still underfit; jump-diffusion extensions (Bates, 1996) add
  jumps on top of Heston dynamics.
- **Calibration instability:** parameters can be poorly identified and drift over time; the Feller
  condition (2κθ ≥ σ_v²) may be violated by fitted parameters.
- **Single-factor variance** misses the term structure of volatility-of-volatility.

## Key references
- Heston, S. (1993) — *A Closed-Form Solution for Options with Stochastic Volatility* — Review of Financial Studies
- Black, F. & Scholes, M. (1973) — *The Pricing of Options and Corporate Liabilities* — Journal of Political Economy
- Bates, D. (1996) — *Jumps and Stochastic Volatility* — Review of Financial Studies
- Gatheral, J. (2006) — *The Volatility Surface* — Wiley
"""

WIKIS["6fac6a66-f70d-483e-85e7-2c2ee9fefe9d"] = """\
# Investor Sentiment and the Cross-Section of Stock Returns

**Source:** Baker, M. & Wurgler, J. (2006). *Journal of Finance* 61(4), 1645–1680.

## TL;DR
Builds a market-wide investor-sentiment index and shows it conditions the cross-section of returns:
when sentiment is high, stocks that are hardest to value and hardest to arbitrage — small, young,
volatile, unprofitable, non-dividend-paying, distressed, or extreme-growth firms — subsequently earn
*low* returns; when sentiment is low, the pattern reverses. Sentiment is not noise to be averaged
away; it predictably mis-prices a recognisable set of stocks.

## What anomaly it documents
A conditioning variable rather than a single tradable factor: the sign and size of many
cross-sectional return spreads depend on the prevailing level of sentiment. The affected
characteristics are precisely those that make a stock speculative and costly to short.

## How to construct it
- **Sentiment index:** first principal component of six proxies — the closed-end fund discount, NYSE
  share turnover, the number and average first-day returns of IPOs, the equity share in new issues,
  and the dividend premium — each orthogonalised to macroeconomic conditions.
- **Sorting:** form portfolios on characteristics linked to valuation difficulty / arbitrage costs
  (size, age, return volatility, profitability, dividend policy, growth/distress).
- **Test:** compare subsequent returns of these portfolios conditional on beginning-of-period
  sentiment (high vs low).

## Evidence and replication
| Period | Result | Source |
|--------|--------|--------|
| IS (1962–2001) | Large conditional return differences; speculative stocks underperform after high sentiment | this paper |
| OOS / robustness | Direction broadly confirmed in later work, though magnitude is regime-dependent and sensitive to index construction | subsequent literature |

The result is conditional and statistical, not a clean always-on long-short factor; its
out-of-sample strength is debated and depends on how sentiment is measured.

## Why it might work
- **Limits to arbitrage:** hard-to-value, hard-to-short stocks can stay mispriced longest.
- **Sentiment-driven demand** from noise traders pushes speculative stocks above fundamentals when
  optimism is high.

## Limitations and risks
- **Index construction:** proxy choice, orthogonalisation, and look-ahead in building the index.
- **Regime dependence and non-stationarity** of the sentiment-return relation.
- **Tradability:** the short leg concentrates in expensive-to-short small caps.

## Key references
- Baker, M. & Wurgler, J. (2006) — *Investor Sentiment and the Cross-Section of Stock Returns* — Journal of Finance
- Baker, M. & Wurgler, J. (2007) — *Investor Sentiment in the Stock Market* — Journal of Economic Perspectives
- De Long, J. B. et al. (1990) — *Noise Trader Risk in Financial Markets* — Journal of Political Economy
- Stambaugh, R., Yu, J. & Yuan, Y. (2012) — *The Short of It: Investor Sentiment and Anomalies* — Journal of Financial Economics
"""

WIKIS["4f8a44cc-9f2f-4a4f-8e42-aa19bf976411"] = """\
# A Comprehensive Look at the Empirical Performance of Equity Premium Prediction

**Source:** Welch, I. & Goyal, A. (2008). *Review of Financial Studies* 21(4), 1455–1508.

## TL;DR
A systematic out-of-sample test of the variables claimed to predict the equity premium — dividend
yield, earnings ratios, book-to-market, interest rates and spreads, and more — finds that, despite
often-strong in-sample fits, essentially **none beat the simple historical-average benchmark out of
sample**. The paper is a landmark demonstration that in-sample predictability routinely fails to
survive honest OOS evaluation.

## The problem it addresses
Decades of studies reported in-sample regressions in which various ratios predict the market's
excess return. Welch and Goyal ask the only question that matters for an investor: would these
signals have helped *in real time*, predicting out of sample?

## Main findings
- Most predictors deliver **negative out-of-sample R²** relative to the prevailing-mean benchmark —
  i.e. they would have hurt a forecaster.
- The apparent in-sample performance is **unstable**, often driven by a few episodes (e.g. the
  1973–75 oil shock) and not robust across subperiods.
- The reply by Campbell & Thompson (2008) shows that imposing economically motivated **sign and
  magnitude restrictions** can recover a small but real OOS R² (on the order of 0.5%/month for some
  predictors) — enough to matter for a mean-variance investor.

## Methodology
Expanding/rolling out-of-sample predictive regressions for each variable, compared against the
historical-average forecast, scored with out-of-sample R² and related statistics, over long samples
(roughly 1927–2005) with multiple subperiods.

## Implications for factor investing
- **Always evaluate out of sample;** a high in-sample R² or t-statistic is not evidence of a usable
  signal.
- Use the **prevailing mean as the benchmark** to beat.
- Economic restrictions and shrinkage toward sensible priors improve real-time forecasts.

## Key references
- Welch, I. & Goyal, A. (2008) — *A Comprehensive Look at the Empirical Performance of Equity Premium Prediction* — Review of Financial Studies
- Campbell, J. & Thompson, S. (2008) — *Predicting Excess Stock Returns Out of Sample* — Review of Financial Studies
- Rapach, D., Strauss, J. & Zhou, G. (2010) — *Out-of-Sample Equity Premium Prediction* — Review of Financial Studies
"""

WIKIS["74a985f5-b8d2-4d8b-8a21-23096588bd40"] = """\
# Optimal Versus Naive Diversification: How Inefficient Is the 1/N Portfolio Strategy?

**Source:** DeMiguel, V., Garlappi, L. & Uppal, R. (2009). *Review of Financial Studies* 22(5),
1915–1953.

## TL;DR
Across many datasets, **none of fourteen sophisticated portfolio-optimisation rules consistently
beats naive 1/N (equal-weighting) out of sample**, because estimation error in expected returns and
covariances overwhelms the theoretical gains from optimisation. Estimation error, not the math, is
the binding constraint in portfolio construction.

## The problem it addresses
Mean-variance optimisation (Markowitz, 1952) is optimal given the true inputs, but in practice the
inputs are estimated with large error — especially expected returns. The paper asks whether, after
honest out-of-sample evaluation, the optimised portfolios actually deliver.

## Main findings
- The equal-weighted **1/N portfolio has higher out-of-sample Sharpe ratios** than sample-based
  mean-variance optimisation and many of its refinements, across the datasets tested.
- Minimum-variance and some shrinkage rules narrow the gap but do not reliably win.
- The **estimation window required** for optimisation to beat 1/N is implausibly long (many decades
  for typical asset counts) — the gains arrive too slowly to exploit.

## Methodology
Rolling out-of-sample comparison of fourteen models against 1/N on multiple empirical datasets,
scored by out-of-sample Sharpe ratio, certainty-equivalent return, and turnover.

## Implications for factor investing
- **Robust construction beats clever optimisation** when inputs are noisy: shrinkage (Ledoit-Wolf),
  position constraints, and minimum-variance/equal-risk approaches help.
- Treat **estimation error as a first-class risk**; prefer methods that degrade gracefully.
- 1/N is a serious benchmark, not a strawman — beating it out of sample is genuinely hard.

## Key references
- DeMiguel, V., Garlappi, L. & Uppal, R. (2009) — *Optimal Versus Naive Diversification* — Review of Financial Studies
- Markowitz, H. (1952) — *Portfolio Selection* — Journal of Finance
- Ledoit, O. & Wolf, M. (2004) — *Honey, I Shrunk the Sample Covariance Matrix* — Journal of Portfolio Management
- Jagannathan, R. & Ma, T. (2003) — *Risk Reduction in Large Portfolios* — Journal of Finance
"""

WIKIS["7cf9f140-bc75-420d-9413-f52eba494c4c"] = """\
# Empirical Asset Pricing via Machine Learning

**Source:** Gu, S., Kelly, B. & Xiu, D. (2020). *Review of Financial Studies* 33(5), 2223–2273.

## TL;DR
A disciplined horse race of machine-learning methods — penalised linear models, random forests,
gradient-boosted trees, and neural networks — for predicting the cross-section of US stock returns
from roughly 94 firm characteristics and their interactions. Trees and neural networks roughly
**double the out-of-sample R² and the Sharpe ratio of the long-short portfolio** relative to linear
models, and the dominant predictors are price trends (momentum), liquidity, and volatility.

## The problem it addresses
The predictor space in asset pricing is high-dimensional and likely nonlinear, with many
characteristics and interactions. Linear factor models cannot exploit interactions or nonlinearity;
ML can, but only if applied with the regularisation and out-of-sample discipline that finance's low
signal-to-noise demands.

## Main findings
- **Neural networks (shallow, 1–4 layers) and gradient-boosted trees perform best;** very deep
  networks do *not* help on this low-signal tabular problem.
- Stock-level monthly out-of-sample R² is small in absolute terms (around 0.4%) but economically
  large: value-weighted long-short decile portfolios reach gross Sharpe ratios well above those of
  linear benchmarks.
- The most important predictors are **recent price trends (momentum), liquidity, and volatility** —
  consistent across methods.

## Methodology
A long sample (1957–2016) of ~30,000 stocks and ~94 characteristics, evaluated with a strict
expanding-window out-of-sample design, comparing predictive R², portfolio Sharpe ratios, and
variable importance across model families.

## Implications for factor investing
- Machine learning **adds real value on tabular finance data**, but the gains come from
  regularisation, interactions, and honest OOS testing — not from model size.
- Prefer **simpler networks** and ensemble trees; interpret models through variable importance.
- The improvements are meaningful yet bounded by the inherently low signal in returns.

## Key references
- Gu, S., Kelly, B. & Xiu, D. (2020) — *Empirical Asset Pricing via Machine Learning* — Review of Financial Studies
- Kelly, B., Pruitt, S. & Su, Y. (2019) — *Characteristics Are Covariances (IPCA)* — Journal of Financial Economics
- Kozak, S., Nagel, S. & Santosh, S. (2020) — *Shrinking the Cross-Section* — Journal of Financial Economics
- Freyberger, J., Neuhierl, A. & Weber, M. (2020) — *Dissecting Characteristics Nonparametrically* — Review of Financial Studies
"""

WIKIS["348d22a1-2e7c-4673-a5e3-bc290044c49b"] = """\
# The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality

**Source:** Bailey, D. H. & López de Prado, M. (2014). *Journal of Portfolio Management* 40(5),
94–107.

## TL;DR
Proposes the **Deflated Sharpe Ratio (DSR)**, which adjusts an observed Sharpe ratio for three
things standard tests ignore: the **number of strategy configurations tried** (selection bias), the
**length of the backtest**, and **non-normality** (skewness and excess kurtosis) of returns. The DSR
asks whether a Sharpe is genuinely significant or merely the maximum of many lucky trials.

## The problem it addresses
When a researcher tries many strategy variants and reports the best backtest, the winning Sharpe
ratio is biased upward — it is an order statistic, not a random draw. Conventional significance tests
take a single Sharpe at face value and so vastly overstate confidence, the quantitative engine of
backtest overfitting.

## Main findings
- Under the null of zero skill, the **expected maximum Sharpe across N independent trials grows with
  N**; the DSR deflates the observed Sharpe by this benchmark.
- The DSR returns the probability that the *true* Sharpe exceeds zero after accounting for trials,
  sample length, skew, and kurtosis.
- The framework yields a **minimum track-record length** needed to establish significance at a given
  confidence.

## Methodology
Derives the sampling distribution of the maximum Sharpe ratio under multiple testing and combines it
with a non-normal correction to the Sharpe's standard error, producing a single deflated
probability.

## Implications for factor investing
- **Report the number of trials** behind any backtest; deflate the Sharpe accordingly.
- Prefer **longer backtests** and be sceptical of short, highly optimised ones.
- Pair with multiple-testing thresholds (Harvey, Liu & Zhu, 2016) — a t-statistic of 2 is not enough
  when hundreds of factors have been tested.

## Key references
- Bailey, D. & López de Prado, M. (2014) — *The Deflated Sharpe Ratio* — Journal of Portfolio Management
- Harvey, C., Liu, Y. & Zhu, H. (2016) — *… and the Cross-Section of Expected Returns* — Review of Financial Studies
- Harvey, C. & Liu, Y. (2015) — *Backtesting* — Journal of Portfolio Management
- López de Prado, M. (2018) — *Advances in Financial Machine Learning* — Wiley
"""

WIKIS["f8dbba7b-be68-4d58-8ed8-7b6737715309"] = """\
# Maxing Out: Stocks as Lotteries and the Cross-Section of Expected Returns

**Source:** Bali, T. G., Cakici, N. & Whitelaw, R. F. (2011). *Journal of Financial Economics*
99(2), 427–446.

## TL;DR
Stocks with high **maximum daily returns over the previous month (MAX)** — a lottery-like feature —
earn **low subsequent returns**. A strategy long low-MAX and short high-MAX stocks is profitable, and
MAX largely explains the otherwise puzzling negative relation between idiosyncratic volatility and
returns documented by Ang et al. (2006).

## What anomaly it documents
Investors appear to overpay for stocks that offer a small chance of a large payoff (positive
skewness / lottery characteristics). Those stocks become overpriced and subsequently underperform —
a cross-sectional anomaly driven by a behavioural preference for skewness.

## How to construct it
- **Sorting variable:** MAX = the average of the five highest daily returns of the stock in the prior
  month (MAX(1) uses just the single highest day; MAX(5) is the common version).
- **Universe:** US common stocks.
- **Portfolio:** long the bottom decile (low MAX), short the top decile (high MAX).
- **Weighting / rebalancing:** value-weighted legs, rebalanced monthly.

## Evidence and replication
| Period | Result | Source |
|--------|--------|--------|
| IS (1962–2005) | Raw decile spread ~1%/month; significant after Fama-French and momentum controls | this paper |
| Interaction | MAX absorbs much of the negative idiosyncratic-volatility effect (Ang et al. 2006) | this paper |

Like most anomalies, it should be expected to decay out of sample, and its short leg sits in volatile
small-caps where costs bite.

## Why it might work
- **Lottery preference / skewness demand:** investors overweight low-probability, high-payoff
  outcomes (Barberis & Huang, 2008).
- **Under-diversified retail investors** (Kumar, 2009) tilt toward lottery stocks.
- **Limits to arbitrage** keep these stocks overpriced.

## Limitations and risks
- **Transaction costs and shorting constraints** on the high-MAX short leg.
- **Overlap** with idiosyncratic volatility and illiquidity effects.
- **Out-of-sample decay** and sensitivity to the MAX definition.

## Key references
- Bali, T., Cakici, N. & Whitelaw, R. (2011) — *Maxing Out: Stocks as Lotteries* — Journal of Financial Economics
- Ang, A., Hodrick, R., Xing, Y. & Zhang, X. (2006) — *The Cross-Section of Volatility and Expected Returns* — Journal of Finance
- Barberis, N. & Huang, M. (2008) — *Stocks as Lotteries* — American Economic Review
- Kumar, A. (2009) — *Who Gambles in the Stock Market?* — Journal of Finance
"""


def patch(pid, markdown):
    body = json.dumps({
        "wiki_markdown": markdown,
        "wiki_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }).encode()
    req = urllib.request.Request(
        f"{URL}/rest/v1/papers?id=eq.{pid}", data=body, method="PATCH",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"})
    urllib.request.urlopen(req).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not URL or not KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    for pid, md in WIKIS.items():
        title = md.splitlines()[0].lstrip("# ")
        print(f"[{'dry' if args.dry_run else 'write'}] {len(md):>5} chars  {title[:60]}")
        if not args.dry_run:
            patch(pid, md)
    print(f"\n{len(WIKIS)} wikis " + ("previewed (dry run)." if args.dry_run else "written."))


if __name__ == "__main__":
    main()
