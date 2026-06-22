"""
author_canonical_wikis_4.py — fourth batch of hand-authored wikis for canonical papers.

Extends coverage into credit/distress (Campbell-Hilscher-Szilagyi, Bharath-Shumway), systemic risk
(Adrian-Brunnermeier CoVaR, Billio-Getmansky-Lo-Pelizzon), text as data (Antweiler-Frank, Fang-Peress),
volatility forecasting and variance risk (Hansen-Lunde, Bollerslev-Tauchen-Zhou), microstructure
pricing (Easley-Hvidkjaer-O'Hara), dispersion (Diether-Malloy-Scherbina), ESG/carbon (Bolton-
Kacperczyk), and jump-diffusion option pricing (Bates). Public, paper-focused content only.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_canonical_wikis_4.py --dry-run
    ...                                          python pipeline/author_canonical_wikis_4.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["13a1eae4-ca2f-4106-b124-c3a8285f6b73"] = """\
# Is All That Talk Just Noise? The Information Content of Internet Stock Message Boards

**Source:** Antweiler, W. & Frank, M. Z. (2004). *Journal of Finance* 59(3), 1259–1294.

## TL;DR
An early, careful study of **social-media text as a market signal**. The authors classify roughly 1.5
million posts from Yahoo! Finance and Raging Bull message boards as bullish/bearish/neutral and show
that message activity is not just noise: posting volume predicts next-day **volatility** and trading
volume, and disagreement among posters predicts higher trading volume — though the return effects are
small and short-lived.

## What it documents
The information content of retail online chatter — a precursor to today's social-media and alternative
-data signals — and the methodological challenge of turning unstructured, noisy posts into a usable
sentiment measure.

## How it is measured
- Collect posts for a set of stocks; classify each with a supervised text classifier (Naive Bayes /
  support vector machine) trained on hand-labelled messages into bullish/bearish/neutral.
- Aggregate into a daily "bullishness" index and a measure of disagreement, then relate them to
  returns, volatility, and volume.

## Evidence
- **Message volume predicts volatility** and helps predict trading volume.
- **Disagreement** (dispersion of opinions) predicts higher subsequent trading volume.
- Return predictability is statistically present but economically small and quickly reversed.

## Why it matters
A foundational reference for text/sentiment-as-data in finance: it established that even informal
online text carries measurable information about volume and volatility, and it modelled the
supervised-classification pipeline now standard for alternative data.

## Limitations and risks
- Message-board populations are unrepresentative and gameable (pump-and-dump, spam).
- Return effects are weak and short-horizon; costs erode tradability.
- Classifier quality and labelling drive results; later embedding/LLM methods supersede bag-of-words.

## Key references
- Antweiler, W. & Frank, M. (2004) — *Is All That Talk Just Noise?* — Journal of Finance
- Tetlock, P. (2007) — *Giving Content to Investor Sentiment* — Journal of Finance
- Da, Z., Engelberg, J. & Gao, P. (2015) — *The Sum of All FEARS* — Review of Financial Studies
"""

WIKIS["b7c81c5c-aae9-4a80-83af-6697177f1f1c"] = """\
# Media Coverage and the Cross-Section of Stock Returns

**Source:** Fang, L. H. & Peress, J. (2009). *Journal of Finance* 64(5), 2023–2052.

## TL;DR
Stocks with **no media coverage earn higher returns** than otherwise-similar stocks with high
coverage — a "no-media premium" of several percent per year after controlling for size, book-to-market,
momentum, and liquidity. The result fits Merton's investor-recognition hypothesis: neglected stocks
need a higher expected return to attract under-diversified, attention-constrained investors.

## What anomaly it documents
A cross-sectional premium tied to investor attention/recognition: low-visibility stocks are held by
fewer investors, so they trade cheaper and earn more — a complement to the attention-pressure results
of Barber-Odean and Da-Engelberg-Gao.

## How it is measured
- Count newspaper articles mentioning each firm (e.g. from major US dailies) to proxy media coverage.
- Sort stocks into coverage portfolios and measure risk-adjusted return differences, controlling for
  standard factors and liquidity.

## Evidence
- A long no-coverage / short high-coverage portfolio earns a positive risk-adjusted return.
- The premium is **stronger among small, low-analyst, high-individual-ownership, high-volatility
  stocks** — exactly where recognition and arbitrage frictions bite hardest.

## Why it matters
A key result linking media/attention to expected returns through the *recognition* channel (lower
visibility → higher required return), distinct from the short-horizon *attention-buying* pressure of
high-coverage stocks. Central to the use of news/media data in cross-sectional strategies.

## Limitations and risks
- Coverage and visibility have changed enormously with social media since 2009.
- The premium concentrates in hard-to-arbitrage small caps; costs limit capture.

## Key references
- Fang, L. & Peress, J. (2009) — *Media Coverage and the Cross-Section of Stock Returns* — Journal of Finance
- Merton, R. (1987) — *A Simple Model of Capital Market Equilibrium with Incomplete Information* — Journal of Finance
- Barber, B. & Odean, T. (2008) — *All That Glitters* — Review of Financial Studies
"""

WIKIS["2452731f-2841-457a-907d-fed3e00cb61f"] = """\
# In Search of Distress Risk

**Source:** Campbell, J. Y., Hilscher, J. & Szilagyi, J. (2008). *Journal of Finance* 63(6),
2899–2939.

## TL;DR
Builds a dynamic model of corporate **failure probability** from accounting and market variables, then
shows the "distress puzzle": stocks with the **highest** probability of financial distress earn
**abnormally low** returns. This is the opposite of what a risk-based story predicts (distress risk
should be compensated), making distress a prominent anomaly.

## What anomaly it documents
A negative relation between failure risk and subsequent returns: the most distressed firms
underperform, with high volatility and high market betas — they look risky yet pay less, a puzzle for
rational asset pricing.

## How it is constructed
- Estimate a **dynamic logit model** of failure using leverage, profitability, past returns,
  volatility, market capitalisation, cash holdings, and the market-to-book ratio, predicting failure
  at horizons from one month to several years.
- Sort stocks on fitted failure probability and measure risk-adjusted returns across the distribution.

## Evidence and replication
| Portfolio | Result | Source |
|-----------|--------|--------|
| Highest failure-probability decile | Low / negative risk-adjusted returns, high volatility & beta | this paper |
| Long safe / short distressed | Positive alpha | this paper |

The failure model itself is a clean example of logistic-regression-based credit/default prediction;
the return pattern is the anomaly.

## Why it might work
- **Mispricing / limits to arbitrage:** distressed stocks are lottery-like and costly to short, so
  they stay overpriced (links to MAX and idiosyncratic-volatility anomalies).
- Rational distress-risk premia would predict the opposite sign, deepening the puzzle.

## Limitations and risks
- The short leg sits in tiny, illiquid, hard-to-short names; costs are severe.
- The failure model needs careful point-in-time accounting data to avoid look-ahead.

## Key references
- Campbell, J., Hilscher, J. & Szilagyi, J. (2008) — *In Search of Distress Risk* — Journal of Finance
- Dichev, I. (1998) — *Is the Risk of Bankruptcy a Systematic Risk?* — Journal of Finance
- Bali, T., Cakici, N. & Whitelaw, R. (2011) — *Maxing Out* — Journal of Financial Economics
"""

WIKIS["3ed40025-1478-4801-bcdc-d451b67725e8"] = """\
# Forecasting Default with the Merton Distance to Default Model

**Source:** Bharath, S. T. & Shumway, T. (2008). *Review of Financial Studies* 21(3), 1339–1369.

## TL;DR
Evaluates how well the structural **Merton distance-to-default (DD)** model predicts corporate
default, and finds that while DD is a useful predictor, it is **not a sufficient statistic** — a
simple "naive" approximation of DD that skips the model's nonlinear equation-solving predicts default
about as well, and a hazard model using both DD and other variables does better than DD alone.

## What it addresses
Merton (1974) treats equity as a call option on firm assets, so default is when asset value falls
below debt; "distance to default" measures how many volatility units the firm is from that boundary.
The paper asks whether this elegant structural measure is actually the best default predictor.

## Method
- Compute Merton DD by solving for unobserved asset value and volatility from equity value/volatility
  and debt.
- Construct a **naive DD** that plugs in simple proxies without the iterative solve.
- Compare both in hazard (default-prediction) regressions against KMV-style and reduced-form benchmarks.

## Evidence
- DD predicts default, but the **naive DD performs comparably**, implying the value comes from the
  functional form (leverage and volatility), not the precise structural solve.
- Adding DD to a hazard model with market and accounting variables beats DD alone.

## Why it matters
A practical, widely cited reference on credit-default modelling: it validates the intuition behind
structural models while showing that simpler, robust features capture most of the signal — a recurring
theme in applied prediction.

## Limitations and risks
- Default is rare and clustered; samples are imbalanced and regime-dependent.
- Structural assumptions (lognormal assets, single debt horizon) are stylised.

## Key references
- Bharath, S. & Shumway, T. (2008) — *Forecasting Default with the Merton Distance to Default Model* — Review of Financial Studies
- Merton, R. (1974) — *On the Pricing of Corporate Debt* — Journal of Finance
- Shumway, T. (2001) — *Forecasting Bankruptcy More Accurately: A Simple Hazard Model* — Journal of Business
"""

WIKIS["0d5f0dcf-b75a-4313-ad06-1eb89cba9cf9"] = """\
# CoVaR

**Source:** Adrian, T. & Brunnermeier, M. K. (2016). *American Economic Review* 106(7), 1705–1741.

## TL;DR
Proposes **CoVaR**, a measure of **systemic risk**: the Value-at-Risk of the whole financial system
*conditional on* a particular institution being in distress. An institution's contribution to systemic
risk is **ΔCoVaR** — the difference between system VaR when the institution is in distress versus its
median state. Institutions with similar individual VaR can contribute very differently to systemic risk.

## What it documents (proposes)
A shift from measuring an institution's *own* risk (VaR) to measuring its *contribution to system-wide*
risk, capturing spillovers, interconnectedness, and tail dependence that VaR ignores.

## Method
- Estimate VaR of the system and of each institution, then the system's VaR conditional on the
  institution's distress, typically via **quantile regression** (and a time-varying version using
  state variables).
- **ΔCoVaR** = system CoVaR given the institution at its VaR level minus system CoVaR given the
  institution at its median — its marginal systemic contribution.
- Relate ΔCoVaR to leverage, size, maturity mismatch, and the institution's own VaR.

## Evidence
- An institution's own VaR is a poor guide to its systemic importance; **ΔCoVaR** is forecastable from
  characteristics like leverage and size, enabling counter-cyclical, pre-emptive measurement.

## Why it matters
A foundational post-2008 systemic-risk metric used by regulators and researchers; it reframes risk
measurement around externalities and tail co-movement, complementing network measures of contagion.

## Limitations and risks
- Estimates are sensitive to the conditioning method and to the choice of state variables.
- Conditional tail measures are hard to estimate precisely and can be unstable in crises.

## Key references
- Adrian, T. & Brunnermeier, M. (2016) — *CoVaR* — American Economic Review
- Acharya, V., Pedersen, L., Philippon, T. & Richardson, M. (2017) — *Measuring Systemic Risk* — Review of Financial Studies
- Billio, M., Getmansky, M., Lo, A. & Pelizzon, L. (2012) — *Econometric Measures of Connectedness and Systemic Risk* — Journal of Financial Economics
"""

WIKIS["3cfeddfc-de0f-4fe0-8e4e-d103bc27583f"] = """\
# Econometric Measures of Connectedness and Systemic Risk in the Finance and Insurance Sectors

**Source:** Billio, M., Getmansky, M., Lo, A. W. & Pelizzon, L. (2012). *Journal of Financial
Economics* 104(3), 535–559.

## TL;DR
Measures **interconnectedness** among hedge funds, banks, broker-dealers, and insurers using
principal-component analysis and Granger-causality networks built from their stock returns. Rising
connectedness precedes and accompanies systemic events — the financial system became far more tightly
linked before the 2007–2009 crisis, and these network measures have predictive content for distress.

## What it documents (proposes)
Data-driven, return-based gauges of systemic risk that need no balance-sheet data: how much of the
sector's variation loads on a few common components (PCA), and which institutions Granger-cause others
(directional network linkages).

## Method
- **PCA:** the fraction of total variance explained by the top principal components of the four
  sectors' returns measures commonality/connectedness.
- **Granger-causality network:** pairwise tests of whether one institution's returns predict another's
  build a directed network; aggregate statistics (degree, centrality) summarise systemic linkage.

## Evidence
- Connectedness (both PCA commonality and Granger linkages) **rose sharply ahead of the crisis** and
  is asymmetric — banks and insurers became increasingly central transmitters of shocks.
- The measures have out-of-sample predictive value for institution-level distress.

## Why it matters
A practical bridge between dimensionality reduction (PCA), network analysis, and systemic-risk
monitoring — directly illustrating how factor structure and connectedness are two sides of the same
data, and how unsupervised methods inform risk surveillance.

## Limitations and risks
- Granger causality captures predictive, not structural/causal, links and is sensitive to lag choice.
- Return-based measures miss off-balance-sheet and funding linkages; networks are noisy in calm periods.

## Key references
- Billio, M., Getmansky, M., Lo, A. & Pelizzon, L. (2012) — *Econometric Measures of Connectedness and Systemic Risk* — Journal of Financial Economics
- Diebold, F. & Yilmaz, K. (2014) — *On the Network Topology of Variance Decompositions* — Journal of Econometrics
- Adrian, T. & Brunnermeier, M. (2016) — *CoVaR* — American Economic Review
"""

WIKIS["8402d92c-6b9d-4f30-8486-88bab1f5e672"] = """\
# Differences of Opinion and the Cross Section of Stock Returns

**Source:** Diether, K. B., Malloy, C. J. & Scherbina, A. (2002). *Journal of Finance* 57(5),
2113–2141.

## TL;DR
Stocks with **greater disagreement among analysts** — measured by the dispersion of earnings forecasts
— earn **lower** future returns. A long low-dispersion / short high-dispersion strategy is profitable,
consistent with Miller's (1977) hypothesis that when opinions diverge and short-selling is constrained,
prices reflect optimists and become overvalued.

## What anomaly it documents
Forecast dispersion proxies for divergence of opinion; under short-sale constraints, pessimists are
kept out of prices, so high-dispersion stocks are overpriced and subsequently underperform — evidence
against treating dispersion as a simple risk proxy.

## How it is constructed
- **Sorting variable:** dispersion = standard deviation of analyst EPS forecasts scaled by the mean
  forecast (or price).
- Sort into dispersion quintiles (often within size groups) and measure subsequent risk-adjusted
  returns; long low-dispersion, short high-dispersion.

## Evidence and replication
| Portfolio | Result | Source |
|-----------|--------|--------|
| High-dispersion | Low future returns | this paper |
| Low − high dispersion | Positive, larger among small and low-priced stocks | this paper |

The effect strengthens where short-sale constraints bind most (small, low-priced stocks).

## Why it might work
- **Miller (1977) overpricing** under binding short-sale constraints and heterogeneous beliefs.
- Behavioural over-optimism in analyst forecasts for hard-to-value firms.

## Limitations and risks
- Dispersion is confounded with uncertainty, distress, and liquidity; identification is debated.
- Short leg is hard/expensive to short — exactly the friction the theory relies on.

## Key references
- Diether, K., Malloy, C. & Scherbina, A. (2002) — *Differences of Opinion and the Cross Section of Stock Returns* — Journal of Finance
- Miller, E. (1977) — *Risk, Uncertainty, and Divergence of Opinion* — Journal of Finance
- Hong, H. & Stein, J. (2007) — *Disagreement and the Stock Market* — Journal of Economic Perspectives
"""

WIKIS["f85523d3-3797-4db0-ba0f-3a37b012263e"] = """\
# Expected Stock Returns and Variance Risk Premia

**Source:** Bollerslev, T., Tauchen, G. & Zhou, H. (2009). *Review of Financial Studies* 22(11),
4463–4492.

## TL;DR
Defines the **variance risk premium (VRP)** — the gap between the risk-neutral expected variance
(implied by option prices, e.g. the squared VIX) and the actual (realized) expected variance — and
shows it **predicts stock-market returns**, with the strongest forecasting power at a **quarterly
horizon**, where it beats traditional predictors like the dividend yield and P/E ratio.

## What it documents
A new, option-implied predictor of the equity premium: when investors pay a large premium to insure
against variance (high VRP), subsequent returns tend to be high — compensation for variance/jump risk.

## How it is measured
- **Risk-neutral variance:** from a model-free implied-variance / VIX-type calculation on index options.
- **Realized variance:** from high-frequency intraday returns.
- VRP = risk-neutral minus expected realized variance; regress future market returns on VRP at various
  horizons.

## Evidence
- The VRP positively predicts market returns; predictability **peaks at roughly one quarter** and
  exceeds that of dividend yield, P/E, and other standard predictors at that horizon.
- A consumption-based model with time-varying economic uncertainty rationalises the pattern.

## Why it matters
Connects the options/volatility market to equity-premium predictability, and supplies one of the few
predictors with strong *short-to-medium* horizon power — complementing the long-horizon valuation-ratio
predictability of Campbell-Shiller.

## Limitations and risks
- VRP estimation depends on the implied- and realized-variance methodology and option data quality.
- Predictability is horizon-specific and can be unstable out of sample.

## Key references
- Bollerslev, T., Tauchen, G. & Zhou, H. (2009) — *Expected Stock Returns and Variance Risk Premia* — Review of Financial Studies
- Carr, P. & Wu, L. (2009) — *Variance Risk Premiums* — Review of Financial Studies
- Bekaert, G. & Hoerova, M. (2014) — *The VIX, the Variance Premium and Stock Market Volatility* — Journal of Econometrics
"""

WIKIS["8f70a8fa-1278-4360-94d7-05ba7e28e541"] = """\
# A Forecast Comparison of Volatility Models: Does Anything Beat a GARCH(1,1)?

**Source:** Hansen, P. R. & Lunde, A. (2005). *Journal of Applied Econometrics* 20(7), 873–889.

## TL;DR
Compares 330 ARCH-type volatility models out of sample. For **exchange rates**, nothing reliably beats
the simple **GARCH(1,1)**; for **equities (IBM)**, models that allow a **leverage effect** (asymmetry,
like GJR/EGARCH) do significantly better. A landmark demonstration that more complex volatility models
rarely help unless they add the *right* feature — here, asymmetry.

## What it addresses
Whether the proliferation of volatility-model variants yields out-of-sample gains over a parsimonious
benchmark — an honest, multiple-model forecasting horse race.

## Method
- Estimate 330 models spanning the ARCH/GARCH family on DM-USD exchange rates and IBM stock returns.
- Compare out-of-sample forecasts using a realized-volatility proxy and the **Superior Predictive
  Ability (SPA) test**, which controls for data-snooping across the many models.

## Evidence
- **Exchange rates:** no model significantly outperforms GARCH(1,1).
- **Equities:** GARCH(1,1) is significantly beaten by models incorporating the **leverage effect**
  (asymmetric volatility response to negative returns).

## Why it matters
A canonical lesson in model selection and honest evaluation: complexity must be justified out of
sample with multiple-comparison-aware tests, and the marginal value of an extra feature depends on the
data (asymmetry matters for stocks, not FX). It pairs naturally with the deflated-Sharpe / multiple-
testing theme.

## Limitations and risks
- Results depend on the realized-volatility proxy and the loss function used.
- Conclusions are about these series/periods; generalisation requires care.

## Key references
- Hansen, P. & Lunde, A. (2005) — *A Forecast Comparison of Volatility Models* — Journal of Applied Econometrics
- Hansen, P. (2005) — *A Test for Superior Predictive Ability* — Journal of Business & Economic Statistics
- Glosten, L., Jagannathan, R. & Runkle, D. (1993) — *On the Relation between the Expected Value and the Volatility...* — Journal of Finance
"""

WIKIS["03d06b48-d7d8-4be7-a36a-b7823d7c78bf"] = """\
# Is Information Risk a Determinant of Asset Returns?

**Source:** Easley, D., Hvidkjaer, S. & O'Hara, M. (2002). *Journal of Finance* 57(5), 2185–2221.

## TL;DR
The empirical companion to the information-and-cost-of-capital theory: it estimates the **probability
of informed trading (PIN)** from order flow and shows that **PIN is priced** in the cross-section.
Stocks with more information-based trading earn higher returns — on the order of a 0.1–0.3% per month
premium per unit of PIN, after controlling for size, book-to-market, and other factors.

## What anomaly it documents
A microstructure-based risk premium: uninformed investors require compensation to hold stocks where
they are more likely to trade against the informed, so information risk is a priced characteristic.

## How it is measured
- Estimate **PIN** for each stock from a structural sequential-trade model fit to daily buy/sell order
  imbalances (the probability that a trade comes from an informed trader).
- Sort stocks on PIN and run cross-sectional (Fama-MacBeth) regressions of returns on PIN plus controls.

## Evidence
- PIN carries a **positive, significant** cross-sectional return premium after standard controls.
- The effect is strongest among smaller stocks where information asymmetry is greatest.

## Why it matters
Provides the empirical support for pricing information asymmetry (the Easley-O'Hara 2004 theory), and
established PIN as a workhorse microstructure measure — later refined by toxicity measures such as VPIN.

## Limitations and risks
- PIN estimation is noisy, and whether it is truly priced (vs. proxying liquidity/size) is debated in
  later work.
- The structural trade-classification model rests on strong assumptions.

## Key references
- Easley, D., Hvidkjaer, S. & O'Hara, M. (2002) — *Is Information Risk a Determinant of Asset Returns?* — Journal of Finance
- Easley, D. & O'Hara, M. (2004) — *Information and the Cost of Capital* — Journal of Finance
- Duarte, J. & Young, L. (2009) — *Why Is PIN Priced?* — Journal of Financial Economics
"""

WIKIS["475bbe1b-910c-4f71-8350-1d840369fb7a"] = """\
# Do Investors Care About Carbon Risk?

**Source:** Bolton, P. & Kacperczyk, M. (2021). *Journal of Financial Economics* 142(2), 517–549.

## TL;DR
Yes: stocks of firms with **higher carbon emissions earn higher returns** — a **carbon premium** —
suggesting investors already demand compensation for carbon-transition risk. The premium is driven by
the **level and growth of total emissions** (not emission intensity), is present across most sectors,
and coincides with some institutional investors beginning to divest on direct-emission (Scope 1) grounds.

## What anomaly it documents
A return premium tied to carbon exposure: higher-emission firms are perceived as riskier in a
decarbonising world, so they trade cheaper and earn more — the asset-pricing footprint of climate-
transition risk, central to ESG/responsible-investing analysis.

## How it is measured
- Match firm-level carbon emissions (Scope 1, 2, and 3) to returns.
- Run cross-sectional return regressions on emission levels, changes, and intensity, controlling for
  size, book-to-market, momentum, and other characteristics; examine institutional ownership patterns.

## Evidence
- A robust positive relation between **total emissions (level and growth)** and returns; **intensity**
  (emissions scaled by sales) is *not* priced the same way.
- Some institutions tilt away from high-Scope-1-emission firms, consistent with the onset of
  exclusionary screening.

## Why it matters
A foundational empirical reference for climate finance and ESG: it shows climate risk is partly priced
and frames the trade-off between divestment/exclusion and expected returns — directly relevant to the
ethics and constraints discussion (and a companion to Hong-Kacperczyk's "price of sin").

## Limitations and risks
- Emissions data is self-reported, estimated, and inconsistently disclosed (especially Scope 3).
- A short, recent sample; whether the carbon premium persists or reverses as policy and flows evolve
  is unsettled (cf. Pástor-Stambaugh-Taylor on green-vs-brown returns).

## Key references
- Bolton, P. & Kacperczyk, M. (2021) — *Do Investors Care About Carbon Risk?* — Journal of Financial Economics
- Hong, H. & Kacperczyk, M. (2009) — *The Price of Sin* — Journal of Financial Economics
- Pástor, Ľ., Stambaugh, R. & Taylor, L. (2022) — *Dissecting Green Returns* — Journal of Financial Economics
"""

WIKIS["124466a2-83d7-4361-a078-c6c6a206290d"] = """\
# Jumps and Stochastic Volatility: Exchange Rate Processes Implicit in Deutsche Mark Options

**Source:** Bates, D. S. (1996). *Review of Financial Studies* 9(1), 69–107.

## TL;DR
Adds **jumps** to a stochastic-volatility model, producing the **stochastic-volatility jump-diffusion
(SVJ, "Bates") model**, and shows that both stochastic volatility *and* jumps are needed to fit the
implied-volatility smile of currency options — especially the steep skew at **short maturities** that
pure stochastic-volatility (Heston) models miss.

## What it solves
Heston's (1993) stochastic-volatility model improves on Black-Scholes but still underfits short-dated
smiles, because diffusion alone cannot generate enough short-horizon skewness/kurtosis. Jumps supply
the missing tail behaviour.

## The model
Combines Heston-style mean-reverting stochastic variance with a **compound-Poisson jump** component in
the asset price: dS/S = (…)dt + √v dW₁ + jumps; dv = κ(θ−v)dt + σ_v√v dW₂, with correlated diffusions
and jump size/intensity parameters. Like Heston, it admits semi-closed-form option prices via the
characteristic function and Fourier inversion.

## Evidence
- Fitting Deutsche-Mark options shows that **jumps are required** to match the smile, particularly its
  short-maturity steepness; stochastic volatility alone is insufficient.
- The combined SVJ model calibrates well across strikes and maturities.

## Why it matters
The SVJ/Bates model is a standard tool for pricing and risk-managing options where tails matter, and a
direct extension of Heston that underpins much of the affine-jump-diffusion option-pricing literature.

## Limitations and risks
- More parameters mean harder, less stable calibration and identification.
- Jump parameters are difficult to estimate from prices alone; model risk in the tails remains.

## Key references
- Bates, D. (1996) — *Jumps and Stochastic Volatility* — Review of Financial Studies
- Heston, S. (1993) — *A Closed-Form Solution for Options with Stochastic Volatility* — Review of Financial Studies
- Duffie, D., Pan, J. & Singleton, K. (2000) — *Transform Analysis and Asset Pricing for Affine Jump-Diffusions* — Econometrica
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
        print(f"[{'dry' if args.dry_run else 'write'}] {len(md):>5} chars  {title[:58]}")
        if not args.dry_run:
            patch(pid, md)
    print(f"\n{len(WIKIS)} wikis " + ("previewed (dry run)." if args.dry_run else "written."))


if __name__ == "__main__":
    main()
