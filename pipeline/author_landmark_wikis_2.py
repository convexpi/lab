"""
author_landmark_wikis_2.py — wikis for the behavioral, volatility/econometrics, and theory landmarks.

Keyed by DOI (rows seeded by seed_landmark_papers.py). Covers behavioral models (Daniel-Hirshleifer-
Subrahmanyam, Lakonishok-Shleifer-Vishny), the P/E effect (Basu), the random-walk/variance-ratio test
(Lo-MacKinlay), excess volatility (Shiller), structural credit (Merton 1974), the equity-premium puzzle
(Mehra-Prescott), Black-Litterman portfolio construction, the ARCH/GARCH/EGARCH volatility family
(Engle, Bollerslev, Nelson), and HAC standard errors (Newey-West). Public, paper-focused.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_landmark_wikis_2.py --dry-run
    ...                                          python pipeline/author_landmark_wikis_2.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.parse, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["10.1111/0022-1082.00077"] = """\
# Investor Psychology and Security Market Under- and Overreactions

**Source:** Daniel, K., Hirshleifer, D. & Subrahmanyam, A. (1998). *Journal of Finance* 53(6),
1839–1885.

## TL;DR
A behavioral model built on two biases — **overconfidence** (investors overestimate the precision of
their private information) and **biased self-attribution** (they credit gains to skill, blame losses on
bad luck). Together these generate **short-horizon momentum and continued overreaction**, followed by
**long-horizon reversal**, plus public-event drift — a unified account of the major return anomalies.

## What it documents (models)
How specific, well-documented psychological biases produce the empirical pattern of underreaction at
short horizons and overreaction at long horizons, complementing Barberis-Shleifer-Vishny (1998).

## Mechanism
- **Overconfidence** makes investors overweight their private signal, pushing prices past fundamentals.
- **Self-attribution** means confirming public news boosts overconfidence further, so overreaction
  *continues* for a while → momentum.
- Eventually prices correct as fundamentals assert themselves → long-run reversal; public news triggers
  predictable post-event drift.

## Why it matters
A foundational behavioral-finance model that links momentum, long-term reversal, and post-event drift
to a coherent psychology, and (with BSV and Hong-Stein) frames the behavioral explanation of
predictability that the efficient-markets view must contend with.

## Limitations and risks
- The biases are assumed and calibrated, not derived; it rationalizes known anomalies more than it
  predicts new ones.
- A stylized model abstracting from arbitrage and heterogeneity.

## Key references
- Daniel, K., Hirshleifer, D. & Subrahmanyam, A. (1998) — *Investor Psychology and Security Market Under- and Overreactions* — Journal of Finance
- Barberis, N., Shleifer, A. & Vishny, R. (1998) — *A Model of Investor Sentiment* — Journal of Financial Economics
- Hong, H. & Stein, J. (1999) — *A Unified Theory of Underreaction, Momentum Trading and Overreaction* — Journal of Finance
"""

WIKIS["10.3386/w4360"] = """\
# Contrarian Investment, Extrapolation, and Risk

**Source:** Lakonishok, J., Shleifer, A. & Vishny, R. (1994). *Journal of Finance* 49(5), 1541–1578.

## TL;DR
Makes the **behavioral case for the value premium**. Value strategies (high book-to-market, earnings-
to-price, cash-flow-to-price, and low past sales growth) outperform "glamour" stocks, and the authors
argue this is because investors **over-extrapolate** past growth — over-pricing glamour and under-pricing
value — rather than because value stocks are fundamentally riskier.

## What anomaly it documents
The value/glamour spread, attributed to expectational errors: investors naively extrapolate past
performance into the future, so glamour disappoints and value pleasantly surprises.

## How it is constructed
- Sort stocks on value measures (B/M, E/P, C/P) and on past growth; form value-minus-glamour portfolios.
- Crucially, examine whether value's higher returns come with **higher risk** — including performance
  in down markets and recessions.

## Evidence
- Value beats glamour by a wide margin across measures.
- Value does **not** underperform in bad states (recessions, market declines, worst months) — so the
  premium is hard to attribute to risk, supporting the extrapolation/mispricing interpretation.

## Why it matters
The cornerstone behavioral argument for value, directly opposing the risk-based (Fama-French, Zhang)
view. The value-premium debate — risk vs. mispricing — traces to this paper.

## Limitations and risks
- Whether value is riskless "free lunch" or compensation for hard-to-measure risk remains contested.
- Costs, capacity, and the post-2007 value drought temper the practical premium.

## Key references
- Lakonishok, J., Shleifer, A. & Vishny, R. (1994) — *Contrarian Investment, Extrapolation, and Risk* — Journal of Finance
- Fama, E. & French, K. (1992) — *The Cross-Section of Expected Stock Returns* — Journal of Finance
- Zhang, L. (2005) — *The Value Premium* — Journal of Finance
"""

WIKIS["10.2307/2326304"] = """\
# Investment Performance of Common Stocks in Relation to Their Price-Earnings Ratios

**Source:** Basu, S. (1977). *Journal of Finance* 32(3), 663–682.

## TL;DR
One of the first documented contradictions of the efficient-market hypothesis: **low price-earnings
(P/E) stocks earn higher risk-adjusted returns** than high-P/E stocks. The "P/E effect" is an early
form of the value premium and a direct challenge to the CAPM and semi-strong efficiency.

## What anomaly it documents
A negative relation between the P/E ratio and subsequent returns: cheap (low-P/E) stocks outperform
expensive (high-P/E) ones even after adjusting for CAPM risk, implying public valuation information was
not "fully reflected" in prices.

## How it is constructed
- Rank NYSE stocks into portfolios by trailing P/E ratio.
- Compare returns and CAPM-adjusted performance across P/E quintiles over the holding period.

## Evidence
- Low-P/E portfolios earn higher absolute and risk-adjusted returns than high-P/E portfolios.
- The difference survives CAPM beta adjustment — a genuine anomaly relative to the model.

## Why it matters
A historical anchor for value investing and one of the earliest "anomalies" that motivated the move
from the CAPM to multi-factor models; the P/E effect foreshadows the book-to-market (HML) value factor.

## Limitations and risks
- Subject to the joint-hypothesis problem (anomaly vs. wrong risk model) and to look-ahead in earnings
  data if not handled carefully.
- Later subsumed by the broader value factor; magnitude varies across eras.

## Key references
- Basu, S. (1977) — *Investment Performance of Common Stocks in Relation to Their Price-Earnings Ratios* — Journal of Finance
- Fama, E. & French, K. (1992) — *The Cross-Section of Expected Stock Returns* — Journal of Finance
- Lakonishok, J., Shleifer, A. & Vishny, R. (1994) — *Contrarian Investment, Extrapolation, and Risk* — Journal of Finance
"""

WIKIS["10.3386/w2168"] = """\
# Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple Specification Test

**Source:** Lo, A. W. & MacKinlay, A. C. (1988). *Review of Financial Studies* 1(1), 41–66.

## TL;DR
Introduces the **variance-ratio test** and uses it to **reject the random-walk hypothesis** for weekly
U.S. stock returns. Under a random walk, return variance should grow **linearly** with the horizon; Lo
and MacKinlay find variance grows **faster** than linearly at short horizons — evidence of positive
autocorrelation, especially in portfolios and small stocks.

## What it documents
A clean statistical test of weak-form efficiency. The variance ratio VR(q) = Var(q-period return) /
(q × Var(1-period return)) equals 1 under a random walk; departures from 1 reveal predictable structure.

## Method
- Compute the variance of returns over base and longer horizons; form the variance ratio.
- Use heteroskedasticity-robust test statistics to assess whether VR(q) differs significantly from 1.

## Evidence
- VR(q) > 1 for weekly returns → **positive serial correlation** at short horizons; the random walk is
  rejected, more strongly for equal-weighted (small-stock-heavy) indices than value-weighted.
- The rejection is robust to heteroskedasticity, so it is not just changing volatility.

## Why it matters
A foundational reference on **return predictability and (non-)stationarity** of prices, and the
variance-ratio test is a standard tool for detecting mean reversion/momentum and for evaluating whether
a series behaves like a random walk — directly relevant to the stylized-facts and leakage material.

## Limitations and risks
- Short-horizon autocorrelation can reflect microstructure (nonsynchronous trading, bid-ask bounce),
  not exploitable predictability.
- Results are horizon- and sample-dependent.

## Key references
- Lo, A. & MacKinlay, A. C. (1988) — *Stock Market Prices Do Not Follow Random Walks* — Review of Financial Studies
- Lo, A. & MacKinlay, A. C. (1990) — *When Are Contrarian Profits Due to Stock Market Overreaction?* — Review of Financial Studies
- Fama, E. (1970) — *Efficient Capital Markets* — Journal of Finance
"""

WIKIS["10.3386/w0456"] = """\
# Do Stock Prices Move Too Much to Be Justified by Subsequent Changes in Dividends?

**Source:** Shiller, R. J. (1981). *American Economic Review* 71(3), 421–436.

## TL;DR
Shows that stock prices are **far more volatile** than the present value of the dividends that actually
followed — the **excess-volatility puzzle**. Under the efficient-markets present-value model, price
should equal the rational forecast of discounted future dividends, which is *smoother* than the price
itself; the bound is violated, suggesting prices move for reasons beyond dividend news.

## What it documents
A **variance-bounds** test of market efficiency: the rational present value of dividends (computed
ex-post) is much smoother than observed prices, so prices "move too much." A direct empirical challenge
to the simple efficient-markets/present-value view.

## Method
- Construct the **ex-post rational price** — the actual discounted sum of subsequent real dividends.
- Compare its variance to the variance of observed real prices; efficiency implies Var(price) ≤
  Var(ex-post rational price).

## Evidence
- Observed prices are **several times more volatile** than the variance bound allows — the inequality is
  violated by a wide margin.
- Volatility seems driven by something other than rational dividend forecasts (later framed as
  discount-rate variation or sentiment).

## Why it matters
A founding paper of behavioral finance and of the discount-rate-variation literature; it shifted the
question from "do prices reflect dividends?" to "why are prices so volatile?" Shiller shared the 2013
Nobel partly for this work.

## Limitations and risks
- The original variance-bounds tests are sensitive to non-stationarity, the assumed discount rate, and
  small samples (critiqued by Marsh-Merton, Kleidon).
- Excess volatility can be reconciled with efficiency via **time-varying discount rates** (Cochrane) —
  the interpretation is debated.

## Key references
- Shiller, R. (1981) — *Do Stock Prices Move Too Much to Be Justified by Subsequent Changes in Dividends?* — American Economic Review
- LeRoy, S. & Porter, R. (1981) — *The Present-Value Relation: Tests Based on Implied Variance Bounds* — Econometrica
- Cochrane, J. (2011) — *Discount Rates* — Journal of Finance
"""

WIKIS["10.2307/2978814"] = """\
# On the Pricing of Corporate Debt: The Risk Structure of Interest Rates

**Source:** Merton, R. C. (1974). *Journal of Finance* 29(2), 449–470.

## TL;DR
Founds the **structural model of credit risk**. Treating a firm's equity as a **call option on its
assets** (with the debt's face value as the strike), Merton prices risky corporate debt with the
Black-Scholes machinery: the firm defaults if asset value falls below what is owed at maturity. Credit
spreads follow from asset value, asset volatility, and leverage.

## What it documents (models)
A no-arbitrage link between a firm's capital structure and the value/yield of its debt: equity holders
hold a call (limited liability), debt holders are effectively short a put on the firm's assets, and the
credit spread compensates for default risk.

## The model
- Firm assets follow geometric Brownian motion; debt is a single zero-coupon obligation maturing at T.
- **Default** occurs if asset value < face value at T.
- Equity = call option on assets; risky debt = risk-free debt − a put. Spreads rise with leverage and
  asset volatility and fall with the firm's "distance to default."

## Why it matters
- The foundation of **structural credit risk**, leading to the KMV/Moody's distance-to-default and
  expected-default-frequency models (and Bharath-Shumway's evaluation of them).
- Connects equity, options, and credit in one framework — a pillar of quantitative risk management.

## Limitations and risks
- Predicts **too-low short-term spreads** (firms rarely default suddenly) — addressed by jump and
  first-passage extensions.
- Assumes a single debt maturity, constant volatility, and observable asset value/vol (which must be
  inferred from equity).

## Key references
- Merton, R. (1974) — *On the Pricing of Corporate Debt* — Journal of Finance
- Black, F. & Scholes, M. (1973) — *The Pricing of Options and Corporate Liabilities* — Journal of Political Economy
- Bharath, S. & Shumway, T. (2008) — *Forecasting Default with the Merton Distance to Default Model* — Review of Financial Studies
"""

WIKIS["10.1016/0304-3932(85)90061-3"] = """\
# The Equity Premium: A Puzzle

**Source:** Mehra, R. & Prescott, E. C. (1985). *Journal of Monetary Economics* 15(2), 145–161.

## TL;DR
Documents the **equity-premium puzzle**: the historical premium of U.S. stocks over risk-free bonds
(around 6% per year) is **far larger** than a standard consumption-based asset-pricing model can explain
with any plausible level of risk aversion. Matching the data requires implausibly high risk aversion —
a puzzle that has shaped macro-finance ever since.

## What it documents
That the canonical model — a representative agent with time-separable power utility consuming aggregate
consumption — cannot simultaneously fit the **high equity premium** and the **low, stable risk-free
rate**, because aggregate consumption is too smooth to make stocks seem risky enough.

## The argument
- In the model, the premium is proportional to risk aversion times the covariance of returns with
  consumption growth.
- Consumption growth is so smooth that fitting a 6% premium implies a risk-aversion coefficient an
  order of magnitude larger than micro evidence supports — and that, in turn, implies a counterfactually
  high risk-free rate (the related "risk-free-rate puzzle").

## Why it matters
A defining puzzle of asset pricing that motivated the major resolutions covered elsewhere: **habit
formation** (Campbell-Cochrane), **long-run risk** (Bansal-Yaron), and **rare disasters** (Rietz,
Barro), as well as behavioral and prospect-theory explanations.

## Limitations and risks
- The "puzzle" depends on the model assumptions (preferences, complete markets, the consumption proxy);
  each resolution relaxes one of them.
- Historical premia may be overstated by survivorship/peso problems (a disasters-based critique).

## Key references
- Mehra, R. & Prescott, E. (1985) — *The Equity Premium: A Puzzle* — Journal of Monetary Economics
- Campbell, J. & Cochrane, J. (1999) — *By Force of Habit* — Journal of Political Economy
- Bansal, R. & Yaron, A. (2004) — *Risks for the Long Run* — Journal of Finance
"""

WIKIS["10.2469/faj.v48.n5.28"] = """\
# Global Portfolio Optimization

**Source:** Black, F. & Litterman, R. (1992). *Financial Analysts Journal* 48(5), 28–43.

## TL;DR
Introduces the **Black-Litterman model**, a Bayesian fix for the fragility of mean-variance
optimization. Instead of feeding in raw expected-return estimates (which produce extreme, unstable
portfolios), it starts from the **market-equilibrium implied returns** (reverse-engineered from market
weights) as a prior, then **blends in the investor's views** with confidence weights — yielding stable,
intuitive, well-diversified portfolios.

## What it addresses
Markowitz optimization is hypersensitive to expected-return inputs: tiny changes produce wildly
different, often extreme and unintuitive weights. Black-Litterman tames this by anchoring to equilibrium.

## The method
- **Reverse-optimize** market-cap weights to obtain the equilibrium (CAPM-implied) expected returns —
  the neutral prior.
- Express **views** ("asset A will beat B by x%") with a confidence (uncertainty) on each.
- Combine prior and views via Bayes' rule to get blended expected returns, then optimize — the result
  tilts away from the market only where the investor has confident views.

## Why it matters
The standard practitioner framework for combining a model/market prior with discretionary or
quantitative views; it operationalizes "shrink toward equilibrium" and largely solves mean-variance's
instability (a companion lesson to DeMiguel et al. on estimation error).

## Limitations and risks
- Requires specifying the prior covariance, the risk-aversion scalar, and view confidences — judgment
  calls that drive results.
- Garbage views in, garbage portfolio out; it stabilizes optimization but does not create skill.

## Key references
- Black, F. & Litterman, R. (1992) — *Global Portfolio Optimization* — Financial Analysts Journal
- Markowitz, H. (1952) — *Portfolio Selection* — Journal of Finance
- DeMiguel, V., Garlappi, L. & Uppal, R. (2009) — *Optimal Versus Naive Diversification* — Review of Financial Studies
"""

WIKIS["10.2307/1912773"] = """\
# Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation

**Source:** Engle, R. F. (1982). *Econometrica* 50(4), 987–1007.

## TL;DR
Introduces **ARCH** (autoregressive conditional heteroscedasticity), the first model in which the
**variance changes over time and depends on past shocks**. ARCH formalizes **volatility clustering** —
large changes follow large changes — and launched the entire field of volatility modeling. Engle shared
the 2003 Nobel for this work.

## What it documents (models)
Classical models assume constant variance, but financial and inflation data show calm and turbulent
periods. ARCH lets the conditional variance be a function of recent squared residuals, so volatility is
**predictable** even when the mean is not.

## The model
σ²_t = α₀ + α₁ ε²_{t-1} + … + α_q ε²_{t-q}: today's conditional variance rises after recent large
(squared) shocks. Estimated by maximum likelihood; the original application is to U.K. inflation
uncertainty.

## Why it matters
- The foundation of **all conditional-volatility modeling** (GARCH, EGARCH, GJR-GARCH, stochastic
  volatility, realized volatility).
- Volatility forecasting, Value-at-Risk, and option pricing all build on the ARCH idea that variance is
  time-varying and forecastable.

## Limitations and risks
- Pure ARCH needs many lags to capture persistence; **GARCH** (Bollerslev) fixes this parsimoniously.
- Symmetric in shocks (no leverage effect) — addressed by EGARCH/GJR-GARCH.

## Key references
- Engle, R. (1982) — *Autoregressive Conditional Heteroscedasticity...* — Econometrica
- Bollerslev, T. (1986) — *Generalized Autoregressive Conditional Heteroskedasticity* — Journal of Econometrics
- Nelson, D. (1991) — *Conditional Heteroskedasticity in Asset Returns (EGARCH)* — Econometrica
"""

WIKIS["10.1016/0304-4076(86)90063-1"] = """\
# Generalized Autoregressive Conditional Heteroskedasticity

**Source:** Bollerslev, T. (1986). *Journal of Econometrics* 31(3), 307–327.

## TL;DR
Generalizes Engle's ARCH to **GARCH** by letting the conditional variance depend on its **own past
values** as well as past squared shocks. The result is dramatically more parsimonious: **GARCH(1,1)** —
just three parameters — captures the slowly decaying volatility persistence seen in nearly all financial
return series, and remains the default volatility model in practice.

## What it documents (models)
ARCH needed many lags to fit persistent volatility; GARCH adds lagged conditional variances, giving an
ARMA-like structure for variance that fits long memory in volatility with few parameters.

## The model
σ²_t = ω + α ε²_{t-1} + β σ²_{t-1} (GARCH(1,1)). The sum α + β measures **volatility persistence**
(close to 1 for most assets); ω/(1 − α − β) is the long-run variance the process mean-reverts toward.

## Why it matters
- The **workhorse** volatility model across finance — risk management, VaR, option pricing, and as the
  benchmark every richer model must beat (Hansen-Lunde: for many series, nothing does).
- The base for the asymmetric extensions (EGARCH, GJR-GARCH) that add the leverage effect.

## Limitations and risks
- Symmetric response to good/bad news (no leverage) — a key gap for equities.
- Assumes a specific parametric form; high persistence can approach non-stationarity (IGARCH).

## Key references
- Bollerslev, T. (1986) — *Generalized Autoregressive Conditional Heteroskedasticity* — Journal of Econometrics
- Engle, R. (1982) — *Autoregressive Conditional Heteroscedasticity...* — Econometrica
- Hansen, P. & Lunde, A. (2005) — *A Forecast Comparison of Volatility Models: Does Anything Beat a GARCH(1,1)?* — Journal of Applied Econometrics
"""

WIKIS["10.2307/2938260"] = """\
# Conditional Heteroskedasticity in Asset Returns: A New Approach

**Source:** Nelson, D. B. (1991). *Econometrica* 59(2), 347–370.

## TL;DR
Introduces **EGARCH** (exponential GARCH), which models the **logarithm** of conditional variance. Two
advantages over GARCH: log-variance is automatically positive so **no parameter constraints** are
needed, and the specification naturally captures the **leverage effect** — negative return shocks raise
future volatility more than positive shocks of the same size.

## What it documents (models)
GARCH requires non-negativity restrictions on its coefficients and treats positive and negative shocks
symmetrically. Nelson's EGARCH removes both limitations by working in logs and letting the sign of the
shock enter the variance equation.

## The model
ln σ²_t = ω + β ln σ²_{t-1} + α [|z_{t-1}| − E|z_{t-1}|] + γ z_{t-1}, where z is the standardized shock.
A negative γ produces the **leverage effect** (bad news → more volatility); the |z| term captures
magnitude. Because the left side is a log, σ²_t is positive for any parameters.

## Why it matters
- One of the two standard **asymmetric** volatility models (with GJR-GARCH), essential for equities
  where the leverage effect is strong.
- Widely used in volatility forecasting and risk management; the news-impact-curve framework (Engle-Ng)
  was built to compare such models.

## Limitations and risks
- The log specification complicates multi-step forecasting and aggregation.
- Like all GARCH-family models, it is parametric and daily-frequency; realized-volatility methods exploit
  intraday data instead.

## Key references
- Nelson, D. (1991) — *Conditional Heteroskedasticity in Asset Returns: A New Approach* — Econometrica
- Glosten, L., Jagannathan, R. & Runkle, D. (1993) — *On the Relation between the Expected Value and the Volatility...* — Journal of Finance
- Engle, R. & Ng, V. (1993) — *Measuring and Testing the Impact of News on Volatility* — Journal of Finance
"""

WIKIS["10.2307/1913610"] = """\
# A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix

**Source:** Newey, W. K. & West, K. D. (1987). *Econometrica* 55(3), 703–708.

## TL;DR
Provides the **Newey-West (HAC) estimator** — standard errors that remain valid when regression errors
are **heteroskedastic and autocorrelated**, while guaranteeing a positive semi-definite covariance
matrix. It is one of the most-used tools in empirical finance, essential whenever returns overlap or
errors are serially correlated (predictive regressions, long-horizon returns, Fama-MacBeth).

## What it addresses
Ordinary (and even White) standard errors are wrong when errors are serially correlated — common in
finance with overlapping observations or persistent predictors. Naive t-statistics then drastically
**overstate significance**, manufacturing spurious predictability.

## The method
- Estimate the long-run variance as a weighted sum of autocovariances up to a chosen **lag (bandwidth)**.
- Apply **Bartlett (triangular) weights** that decline with lag, which guarantees the estimator is
  positive semi-definite (a valid covariance matrix).
- Use the resulting HAC standard errors for valid inference.

## Why it matters
- The default fix for inference in time-series and panel finance regressions — directly relevant to
  honest evaluation, since uncorrected autocorrelation is a classic way backtests and predictive
  regressions look significant when they are not.
- Pairs conceptually with the multiple-testing/deflated-Sharpe literature on not fooling yourself.

## Limitations and risks
- Results depend on the **bandwidth/lag choice**; too few lags under-corrects, too many is noisy
  (Andrews 1991 gives data-driven choices).
- A large-sample (asymptotic) correction; small samples can still mislead.

## Key references
- Newey, W. & West, K. (1987) — *A Simple, Positive Semi-Definite, HAC Covariance Matrix* — Econometrica
- White, H. (1980) — *A Heteroskedasticity-Consistent Covariance Matrix Estimator* — Econometrica
- Andrews, D. (1991) — *Heteroskedasticity and Autocorrelation Consistent Covariance Matrix Estimation* — Econometrica
"""


def patch(doi, markdown):
    body = json.dumps({
        "wiki_markdown": markdown,
        "wiki_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }).encode()
    url = f"{URL}/rest/v1/papers?doi=eq.{urllib.parse.quote(doi)}"
    req = urllib.request.Request(url, data=body, method="PATCH",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"})
    urllib.request.urlopen(req).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not URL or not KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    for doi, md in WIKIS.items():
        title = md.splitlines()[0].lstrip("# ")
        print(f"[{'dry' if args.dry_run else 'write'}] {len(md):>5} chars  {title[:56]}")
        if not args.dry_run:
            patch(doi, md)
    print(f"\n{len(WIKIS)} wikis " + ("previewed (dry run)." if args.dry_run else "written."))


if __name__ == "__main__":
    main()
