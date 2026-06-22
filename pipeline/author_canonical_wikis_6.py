"""
author_canonical_wikis_6.py — sixth batch of hand-authored wikis for canonical papers.

Covers investment/anomaly evaluation (Cooper-Gulen-Schill asset growth, Titman-Wei-Xie capital
investment, Fama-French "Dissecting Anomalies"), the idiosyncratic-volatility puzzle (Ang et al.
2008), asset-pricing theory (Zhang value premium, Bansal-Yaron long-run risk), out-of-sample
prediction via combination (Rapach-Strauss-Zhou), momentum and volume (Lee-Swaminathan), text/NLP
(Loughran-McDonald readability, Hassan et al. firm-level political risk), option-implied skew
(Bakshi-Kapadia-Madan), and ESG portfolio theory (Pedersen-Fitzgibbons-Pomorski). Public,
paper-focused content only.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_canonical_wikis_6.py --dry-run
    ...                                          python pipeline/author_canonical_wikis_6.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["4e358199-e6a3-4e01-afb4-384dec403813"] = """\
# Asset Growth and the Cross-Section of Stock Returns

**Source:** Cooper, M. J., Gulen, H. & Schill, M. J. (2008). *Journal of Finance* 63(4), 1609–1651.

## TL;DR
Firms that grow their **total assets** quickly earn **low** subsequent returns, and slow-growers earn
high returns. The asset-growth effect is large, robust across size groups, and one of the most
economically significant cross-sectional predictors — it underlies the modern "investment" factor (CMA
in the Fama-French five-factor model).

## What anomaly it documents
A negative relation between the rate of total-asset growth and future returns: aggressive expanders
(via capex, acquisitions, issuance) underperform conservative firms. The signal uses the whole balance
sheet, not a single line item.

## How it is constructed
- **Sorting variable:** year-over-year growth in total assets.
- **Universe:** US common stocks; the effect survives in large caps, not just microcaps.
- **Portfolio:** long low-asset-growth, short high-asset-growth; value- or equal-weighted, rebalanced
  annually.

## Evidence and replication
| Portfolio | Result | Source |
|-----------|--------|--------|
| Low − high asset growth | Large positive spread, robust to FF/momentum controls | this paper |
| By size | Present even among large stocks | this paper |

## Why it might work
- **Overinvestment / empire-building** that the market initially rewards then corrects (mispricing).
- **Investment-based asset pricing:** firms invest more when their cost of capital (expected return)
  is low — a risk-based reading consistent with q-theory.

## Limitations and risks
- Distinguishing mispricing from a rational investment factor is hard.
- Annual rebalancing on accounting data needs point-in-time discipline; costs apply.

## Key references
- Cooper, M., Gulen, H. & Schill, M. (2008) — *Asset Growth and the Cross-Section of Stock Returns* — Journal of Finance
- Titman, S., Wei, K. C. & Xie, F. (2004) — *Capital Investments and Stock Returns* — Journal of Financial and Quantitative Analysis
- Fama, E. & French, K. (2015) — *A Five-Factor Asset Pricing Model* — Journal of Financial Economics
"""

WIKIS["5a6cd154-587a-43ea-8a4d-e200fe9d9a53"] = """\
# Capital Investments and Stock Returns

**Source:** Titman, S., Wei, K. C. J. & Xie, F. (2004). *Journal of Financial and Quantitative
Analysis* 39(4), 677–700.

## TL;DR
Firms that substantially **increase capital investment** subsequently earn **lower** returns. The
effect is strongest for firms with the **greatest investment discretion** — high cash flow and low
debt — consistent with managers over-investing (empire-building) and investors underreacting to the
empire-building signal.

## What anomaly it documents
A negative investment-return relation at the firm level: abnormal capital expenditure predicts
underperformance, especially where managers have the freedom to over-invest. A close cousin of the
asset-growth and accruals anomalies.

## How it is constructed
- **Sorting variable:** abnormal capital investment (capex scaled and benchmarked against the firm's
  recent average / industry).
- Sort into portfolios; interact with proxies for managerial discretion (free cash flow, leverage).

## Evidence
- High-abnormal-investment firms underperform low-investment firms on a risk-adjusted basis.
- The negative relation is **concentrated** among firms with high cash flow and low leverage — those
  most able to over-invest without external discipline.

## Why it might work
- **Agency / over-investment:** entrenched managers expand beyond value-maximizing levels; the market
  underreacts and later corrects.
- **q-theory / risk-based:** firms invest more when discount rates are low, mechanically lowering
  future returns.

## Limitations and risks
- Overlaps with asset growth and accruals; isolating the capex channel is difficult.
- Accounting-based and annual; transaction costs and data timing matter.

## Key references
- Titman, S., Wei, K. C. & Xie, F. (2004) — *Capital Investments and Stock Returns* — Journal of Financial and Quantitative Analysis
- Cooper, M., Gulen, H. & Schill, M. (2008) — *Asset Growth and the Cross-Section of Stock Returns* — Journal of Finance
- Sloan, R. (1996) — *Do Stock Prices Fully Reflect Information in Accruals and Cash Flows?* — The Accounting Review
"""

WIKIS["19dc7902-7c21-4c4e-a28e-a716ae2b1b34"] = """\
# Dissecting Anomalies

**Source:** Fama, E. F. & French, K. R. (2008). *Journal of Finance* 63(4), 1653–1678.

## TL;DR
A systematic, skeptical evaluation of the major cross-sectional anomalies — net stock issues,
accruals, momentum, asset growth, and profitability — using two complementary tools: portfolio sorts
and cross-sectional regressions, examined separately by size. The key lesson: **many anomalies are
concentrated in tiny ("microcap") stocks** and shrink or vanish among the large stocks that actually
matter for capacity.

## The problem it addresses
Anomalies are often documented with equal-weighted portfolios dominated by small, illiquid stocks. Fama
and French ask which anomalies are **pervasive** (present across the size spectrum) and which are
**microcap phenomena** that would be hard or impossible to trade at scale.

## Main findings
- **Momentum** and **net stock issues** are pervasive across size groups.
- **Accruals** and **asset growth** are real but **concentrated in small/microcap** stocks.
- Sorts and regressions can disagree, because regressions give microcaps influence proportional to
  their number while value-weighted sorts do not — a methodological warning.

## Methodology
For each anomaly, form value-weighted sorts within size groups (microcap, small, big) and run
Fama-MacBeth cross-sectional regressions, comparing where the predictability actually lives.

## Implications for factor investing
- **Check where an anomaly lives:** an effect that exists only in microcaps is largely untradable.
- Prefer **value-weighted** evidence and be wary of equal-weighted results dominated by tiny stocks —
  a discipline directly relevant to honest backtesting.

## Key references
- Fama, E. & French, K. (2008) — *Dissecting Anomalies* — Journal of Finance
- Cooper, M., Gulen, H. & Schill, M. (2008) — *Asset Growth and the Cross-Section of Stock Returns* — Journal of Finance
- Hou, K., Xue, C. & Zhang, L. (2020) — *Replicating Anomalies* — Review of Financial Studies
"""

WIKIS["5f673460-c95c-483f-b0ef-b2cc11ac33ff"] = """\
# High Idiosyncratic Volatility and Low Returns: International and Further U.S. Evidence

**Source:** Ang, A., Hodrick, R. J., Xing, Y. & Zhang, X. (2009). *Journal of Financial Economics*
91(1), 1–23.

## TL;DR
Confirms and extends the **idiosyncratic-volatility puzzle**: stocks with high idiosyncratic
volatility (relative to the Fama-French model) earn **abnormally low** returns. The effect is present
in the U.S. and across 23 developed markets, and is robust to many controls — a puzzle because standard
theory says diversifiable risk should not be priced, and if anything higher total risk should earn more.

## What anomaly it documents
A negative relation between recent idiosyncratic volatility and future returns, contradicting both the
CAPM (idiosyncratic risk unpriced) and naive intuition (more risk, more return). It generalizes the
authors' 2006 U.S. result internationally.

## How it is constructed
- **Sorting variable:** idiosyncratic volatility = standard deviation of residuals from a Fama-French
  three-factor regression, estimated over the prior month of daily returns.
- Sort into quintiles; long low-IVOL, short high-IVOL; value-weighted, monthly.

## Evidence and replication
| Portfolio | Result | Source |
|-----------|--------|--------|
| High-IVOL quintile | Low / negative risk-adjusted returns | this paper |
| Low − high IVOL | Positive, present in the U.S. and 23 markets | this paper |

## Why it might work
- **Lottery preference / limits to arbitrage:** high-IVOL stocks are lottery-like and costly to short
  (links to MAX, Bali et al. 2011).
- Microstructure, one-month return reversal, and liquidity have all been proposed as partial
  explanations; the puzzle remains contested.

## Limitations and risks
- Sensitive to the estimation window and the factor model used to define "idiosyncratic."
- Short leg concentrates in volatile, hard-to-short small caps; costs are severe.

## Key references
- Ang, A., Hodrick, R., Xing, Y. & Zhang, X. (2009) — *High Idiosyncratic Volatility and Low Returns* — Journal of Financial Economics
- Ang, A., Hodrick, R., Xing, Y. & Zhang, X. (2006) — *The Cross-Section of Volatility and Expected Returns* — Journal of Finance
- Bali, T., Cakici, N. & Whitelaw, R. (2011) — *Maxing Out* — Journal of Financial Economics
"""

WIKIS["cf7d60f0-3329-48dd-9e7e-5f4ab23a8efc"] = """\
# The Value Premium

**Source:** Zhang, L. (2005). *Journal of Finance* 60(1), 67–103.

## TL;DR
Offers a **risk-based, investment-based** explanation of the value premium. Because investment is
**costly to reverse** and the price of risk is **countercyclical**, value firms — burdened with
unproductive capital they cannot easily shed in downturns — are riskier exactly when risk is most
painful, so they command higher expected returns than growth firms.

## What it documents (models)
A neoclassical (q-theory) production economy in which firms' real investment decisions generate the
value premium endogenously, without behavioral assumptions — a rational counterpoint to mispricing
stories of value.

## Mechanism
- **Costly reversibility:** cutting capital is more expensive than expanding it, so value firms
  (asset-heavy, low growth) are stuck with excess capacity in recessions.
- **Countercyclical price of risk:** risk aversion/risk premia are high in bad times.
- Together, value firms' cash flows covary badly with marginal utility, making them riskier and
  higher-returning; growth firms have valuable, flexible growth options that hedge bad times.

## Why it matters
A landmark rational explanation of the value premium that ties asset prices to firms' real investment
frictions, motivating investment-based factor models (e.g., the q-factor and CMA factors).

## Limitations and risks
- Calibration-dependent; whether the mechanism quantitatively matches the data is debated.
- Behavioral explanations (extrapolation, Lakonishok-Shleifer-Vishny) fit some facts the risk story
  struggles with — the value debate is unresolved.

## Key references
- Zhang, L. (2005) — *The Value Premium* — Journal of Finance
- Lakonishok, J., Shleifer, A. & Vishny, R. (1994) — *Contrarian Investment, Extrapolation, and Risk* — Journal of Finance
- Hou, K., Xue, C. & Zhang, L. (2015) — *Digesting Anomalies: An Investment Approach* — Review of Financial Studies
"""

WIKIS["2e3fb747-7313-413b-88bc-3ac996496711"] = """\
# Risks for the Long Run: A Potential Resolution of Asset Pricing Puzzles

**Source:** Bansal, R. & Yaron, A. (2004). *Journal of Finance* 59(4), 1481–1509.

## TL;DR
The **long-run risk** model: a small but **persistent predictable component** in consumption and
dividend growth, combined with **time-varying economic uncertainty** and **Epstein-Zin** recursive
preferences, can jointly explain the equity premium, the low risk-free rate, and the high volatility of
returns — puzzles that the standard consumption model cannot.

## What it documents (models)
A rational, consumption-based resolution of the equity-premium and related puzzles that relies on
investors caring about **long-run** growth prospects and uncertainty, not just short-run consumption.

## Mechanism
- Consumption growth has a tiny, highly persistent expected-growth component plus fluctuating
  volatility (economic uncertainty).
- With Epstein-Zin preferences, investors dislike both low expected growth and high uncertainty about
  it; this makes equities risky and raises the premium.
- The model generates predictability in returns and a low, stable risk-free rate.

## Why it matters
One of the two leading rational frameworks (alongside habit formation and rare disasters) for the
equity premium, and the foundation of a large "long-run risk" literature linking macro uncertainty to
asset prices.

## Limitations and risks
- The persistent growth component is **hard to detect** in consumption data, drawing criticism that it
  is nearly unfalsifiable.
- Results are sensitive to preference parameters and the assumed consumption dynamics.

## Key references
- Bansal, R. & Yaron, A. (2004) — *Risks for the Long Run* — Journal of Finance
- Epstein, L. & Zin, S. (1989) — *Substitution, Risk Aversion, and the Temporal Behavior of Consumption and Asset Returns* — Econometrica
- Campbell, J. & Cochrane, J. (1999) — *By Force of Habit* — Journal of Political Economy
"""

WIKIS["28a42f26-255e-456f-9cd8-523f0d09ee89"] = """\
# Out-of-Sample Equity Premium Prediction: Combination Forecasts and Links to the Real Economy

**Source:** Rapach, D. E., Strauss, J. K. & Zhou, G. (2010). *Review of Financial Studies* 23(2),
821–862.

## TL;DR
A constructive answer to the Welch-Goyal pessimism: while **individual** predictors of the equity
premium fail out of sample, **simple combinations** of many individual forecasts (e.g., the mean of
predictors) deliver **consistent, significant out-of-sample gains** and are tied to the business cycle —
combination forecasts beat both the historical average and any single predictor.

## The problem it addresses
Individual predictive regressions are unstable and overfit, so they fail out of sample. The paper asks
whether aggregating across many noisy predictors can recover real, usable predictability.

## Main findings
- **Combination forecasts** (especially simple averages) produce positive out-of-sample R² where
  individual models do not — they reduce forecast variance and are robust to model instability.
- The predictability is **countercyclical**, strengthening in recessions, linking return predictability
  to real-economic fluctuations.

## Methodology
Compute out-of-sample forecasts for many individual predictors, then combine them (mean, median,
trimmed mean, discounted MSE weights); evaluate with out-of-sample R² and utility gains against the
prevailing-mean benchmark.

## Implications for factor investing
- **Forecast combination / ensembling** is a powerful antidote to overfitting — averaging many weak,
  unstable signals beats betting on one.
- Predictability is regime-dependent (stronger in bad times), which matters for timing and risk.

## Key references
- Rapach, D., Strauss, J. & Zhou, G. (2010) — *Out-of-Sample Equity Premium Prediction: Combination Forecasts* — Review of Financial Studies
- Welch, I. & Goyal, A. (2008) — *A Comprehensive Look at the Empirical Performance of Equity Premium Prediction* — Review of Financial Studies
- Timmermann, A. (2006) — *Forecast Combinations* — Handbook of Economic Forecasting
"""

WIKIS["9b22629e-ea53-4243-8288-4a332a78d332"] = """\
# Price Momentum and Trading Volume

**Source:** Lee, C. M. C. & Swaminathan, B. (2000). *Journal of Finance* 55(5), 2017–2069.

## TL;DR
Past **trading volume** predicts the magnitude and persistence of momentum. High-volume stocks behave
like glamour stocks (low future returns) and low-volume like value stocks; volume helps reconcile
short-horizon **momentum** with long-horizon **reversal** through a "momentum life cycle" in which
stocks transition between winner and loser, glamour and value, states.

## What anomaly it documents
An interaction between momentum and volume: among winners, **low-volume** winners have stronger,
more persistent momentum; among losers, **high-volume** losers fall further — and momentum eventually
reverses, with volume signaling where a stock sits in its life cycle.

## How it is constructed
- Double-sort stocks on **past returns** (momentum) and **past trading volume** (turnover).
- Track returns over 1–5 years to map the transition from momentum to reversal.

## Evidence
- Low-volume winners and high-volume losers show the strongest momentum.
- High-volume stocks earn lower long-run returns (glamour-like); volume predicts the speed and
  direction of subsequent reversal.

## Why it might work
- **Behavioral:** volume proxies for investor (over/under) attention and disagreement, tracing
  underreaction that later overcorrects.
- The momentum life cycle integrates momentum and contrarian effects into one framework.

## Limitations and risks
- Volume's meaning has shifted with market structure (HFT, ETFs) since 2000.
- Double-sorts thin out portfolios; turnover and costs matter.

## Key references
- Lee, C. & Swaminathan, B. (2000) — *Price Momentum and Trading Volume* — Journal of Finance
- Jegadeesh, N. & Titman, S. (1993) — *Returns to Buying Winners and Selling Losers* — Journal of Finance
- Gervais, S., Kaniel, R. & Mingelgrin, D. (2001) — *The High-Volume Return Premium* — Journal of Finance
"""

WIKIS["96deeebc-7f7a-4568-92b3-84e7fb18f335"] = """\
# Measuring Readability in Financial Disclosures

**Source:** Loughran, T. & McDonald, B. (2014). *Journal of Finance* 69(4), 1643–1671.

## TL;DR
Shows that the **Fog index** — the standard readability measure imported from general linguistics — is
a **poor proxy** for the readability of 10-K filings, because its "complex word" component is dominated
by common multisyllabic business terms (e.g., "company," "operations") that readers understand. They
propose a far simpler, better proxy: the **10-K file size**. Bigger, more complex filings are
associated with more disagreement, volatility, and forecast errors.

## What it documents
A measurement caution for textual analysis: a metric that works in one domain can be meaningless in
finance. The paper supplies a robust, easy alternative and demonstrates why naive imports mislead.

## How it is measured
- Show the Fog index's complex-word count is driven by ubiquitous, well-understood business words.
- Propose **natural-log of 10-K file size** (in bytes) as a readability/complexity proxy, validated
  against post-filing return volatility, analyst dispersion, and earnings-forecast errors.

## Evidence
- Fog correlates poorly with outcomes that "readability" should predict.
- **File size** robustly predicts higher post-filing volatility, dispersion, and forecast errors —
  complex filings are genuinely harder to process.

## Why it matters
A foundational methodological reference for finance NLP (companion to Loughran-McDonald 2011): it warns
that text metrics must be validated in-domain and provides a simple, widely adopted complexity measure.

## Limitations and risks
- File size conflates length with complexity and is affected by formatting/exhibits.
- As filings move to structured formats (XBRL/HTML), byte-size proxies need re-validation.

## Key references
- Loughran, T. & McDonald, B. (2014) — *Measuring Readability in Financial Disclosures* — Journal of Finance
- Loughran, T. & McDonald, B. (2011) — *When Is a Liability Not a Liability?* — Journal of Finance
- Li, F. (2008) — *Annual Report Readability, Current Earnings, and Earnings Persistence* — Journal of Accounting and Economics
"""

WIKIS["46c3bff7-d577-41ce-bb57-c49c54607e37"] = """\
# Firm-Level Political Risk: Measurement and Effects

**Source:** Hassan, T. A., Hollander, S., van Lent, L. & Tahoun, A. (2019). *Quarterly Journal of
Economics* 134(4), 2135–2202.

## TL;DR
Uses **computational linguistics on earnings-call transcripts** to construct a firm-level measure of
**political risk** — the share of a call devoted to political topics, weighted by surrounding
risk/uncertainty language. Firms facing high political risk **invest and hire less**, **lobby and
donate more**, and have **higher stock volatility**. A landmark in turning unstructured text into a
firm-specific risk measure.

## What it documents
That meaningful, firm-level risk exposures can be **measured from text** rather than prices, and that
the resulting political-risk measure has real consequences for corporate behavior and asset prices.

## How it is measured
- Build a library of political bigrams from a political-science textbook vs. a non-political corpus.
- For each earnings call, count political bigrams near risk/uncertainty words to score political risk
  (and adjacent measures of political sentiment and exposure to specific topics).

## Evidence
- High political risk → **lower investment and employment**, more **lobbying and PAC contributions**,
  and **higher idiosyncratic volatility**.
- Most variation is **firm-specific**, not aggregate — political risk is heterogeneous across firms in
  the same period.

## Why it matters
A model example of text-as-data done rigorously: transparent, replicable construction; validation
against behavior and prices; and an openly shared dataset. Directly relevant to NLP feature
engineering and risk measurement from disclosures/calls.

## Limitations and risks
- Dictionary/bigram construction involves judgment; calls are managed communications.
- The measure captures discussed risk, which may differ from realized exposure.

## Key references
- Hassan, T., Hollander, S., van Lent, L. & Tahoun, A. (2019) — *Firm-Level Political Risk* — Quarterly Journal of Economics
- Baker, S., Bloom, N. & Davis, S. (2016) — *Measuring Economic Policy Uncertainty* — Quarterly Journal of Economics
- Loughran, T. & McDonald, B. (2011) — *When Is a Liability Not a Liability?* — Journal of Finance
"""

WIKIS["9f984e33-fac3-4bd6-8ac1-5094d1d2f2bd"] = """\
# Stock Return Characteristics, Skew Laws, and the Differential Pricing of Individual Equity Options

**Source:** Bakshi, G., Kapadia, N. & Madan, D. (2003). *Review of Financial Studies* 16(1), 101–143.

## TL;DR
Derives **model-free formulas** for the risk-neutral **variance, skewness, and kurtosis** of returns
from a cross-section of option prices, and uses them to show that **index** options are priced with
much more negative skewness than **individual-stock** options. Risk-neutral skewness varies
systematically with stock characteristics and the market's risk premium.

## What it documents
A method to extract higher moments of the return distribution implied by option prices without
assuming a pricing model, and empirical "skew laws" linking those moments to firm characteristics and
to the index-vs-single-name difference.

## How it is measured
- Use spanning results to write risk-neutral variance, skew, and kurtosis as portfolios of
  out-of-the-money calls and puts (model-free, from the option cross-section).
- Compute these moments for the index and individual stocks; relate skewness to systematic risk and
  characteristics.

## Evidence
- **Index** risk-neutral skewness is strongly negative; **individual-stock** skewness is much less
  negative (even positive) — the index's crash fear is a market-level, not firm-level, phenomenon.
- Risk-neutral skewness covaries with beta and other characteristics in predictable "skew laws."

## Why it matters
Foundational for option-implied moment measures now widely used as forward-looking signals (implied
skew/kurtosis), and for understanding the index volatility skew as priced crash risk.

## Limitations and risks
- Estimates require a dense option cross-section and clean prices; OTM options are illiquid.
- Risk-neutral moments mix expectations with risk premia and cannot be read as physical probabilities.

## Key references
- Bakshi, G., Kapadia, N. & Madan, D. (2003) — *Stock Return Characteristics, Skew Laws...* — Review of Financial Studies
- Carr, P. & Madan, D. (2001) — *Towards a Theory of Volatility Trading* — (volatility spanning)
- Bakshi, G., Cao, C. & Chen, Z. (1997) — *Empirical Performance of Alternative Option Pricing Models* — Journal of Finance
"""

WIKIS["df1f8243-9929-406f-a018-7bf59b2e9f84"] = """\
# Responsible Investing: The ESG-Efficient Frontier

**Source:** Pedersen, L. H., Fitzgibbons, S. & Pomorski, L. (2021). *Journal of Financial Economics*
142(2), 572–597.

## TL;DR
Provides a framework for thinking about ESG and returns at once. ESG scores can **help** returns (when
they predict future profitability or risk) or **hurt** them (when investors accept lower returns for
their values). The paper derives the **ESG-efficient frontier** — the highest attainable Sharpe ratio
for each level of average ESG — and shows how different investor types choose along it.

## What it documents (models)
A portfolio-choice model with three investor types: those who ignore ESG, those who use ESG only as a
**signal** about fundamentals, and those who have an ESG **preference** (taste). The trade-off between
the Sharpe ratio and portfolio ESG is made explicit and tradable.

## Framework
- **ESG-efficient frontier:** for each target ESG level, the maximum Sharpe ratio achievable — a
  generalization of the mean-variance frontier with an ESG dimension.
- An ESG-aware investor picks the tangency-like point given their ESG preference; the **cost of ESG**
  is the Sharpe sacrificed relative to the unconstrained optimum.
- If ESG forecasts profitability/risk, incorporating it can *raise* the Sharpe ratio — ESG as alpha,
  not just constraint.

## Why it matters
A foundational, decision-theoretic treatment of responsible investing that quantifies the return cost
(or benefit) of ESG constraints — directly relevant to portfolio construction under values-based
constraints and to the ethics discussion (companion to Hong-Kacperczyk and Bolton-Kacperczyk).

## Limitations and risks
- Requires reliable ESG data and a view on whether ESG predicts fundamentals — both contested.
- The frontier is an ex-ante construct; realized ESG-return relations vary over time and by definition.

## Key references
- Pedersen, L., Fitzgibbons, S. & Pomorski, L. (2021) — *Responsible Investing: The ESG-Efficient Frontier* — Journal of Financial Economics
- Pástor, Ľ., Stambaugh, R. & Taylor, L. (2021) — *Sustainable Investing in Equilibrium* — Journal of Financial Economics
- Hong, H. & Kacperczyk, M. (2009) — *The Price of Sin* — Journal of Financial Economics
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
