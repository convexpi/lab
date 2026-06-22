"""
author_canonical_wikis_5.py — fifth batch of hand-authored wikis for canonical papers.

Covers deep learning in finance (Fischer-Krauss LSTM), rare-disaster asset pricing (Barro),
default/credit (Vassalou-Xing), overconfidence (Odean), international factors (Fama-French 2012),
search-based sentiment (Da-Engelberg-Gao FEARS), accrual quality (Dechow-Dichev), option-model
comparison (Bakshi-Cao-Chen), idiosyncratic-volatility trends (Campbell-Lettau-Malkiel-Xu), the
buyback anomaly (Ikenberry-Lakonishok-Vermaelen), innovation and returns (Kogan-Papanikolaou-Seru-
Stoffman), and policy uncertainty (Pastor-Veronesi). Public, paper-focused content only.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_canonical_wikis_5.py --dry-run
    ...                                          python pipeline/author_canonical_wikis_5.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["a9359785-0188-4789-94be-148543f608e0"] = """\
# Deep Learning with Long Short-Term Memory Networks for Financial Market Predictions

**Source:** Fischer, T. & Krauss, C. (2018). *European Journal of Operational Research* 270(2),
654–669.

## TL;DR
Applies **LSTM recurrent neural networks** to predict the directional movement of S&P 500 constituents
and finds they **outperform** random forests, standard deep nets, and logistic regression. A daily
long-short strategy on the predictions earns large returns before costs — but, tellingly,
profitability **decays over time**, largely vanishing after ~2010 as markets grew more efficient.

## What it documents
A clean benchmark of sequence models versus tree/linear baselines on a real cross-sectional
prediction task, and an honest account of how a machine-learning edge erodes once it is widely
discoverable — the book's thesis applied to deep learning.

## How it is constructed
- **Features:** sequences of standardized daily returns for each stock.
- **Model:** an LSTM trained to classify whether a stock will out- or under-perform the
  cross-sectional median over the next day.
- **Strategy:** each day, go long the highest-probability outperformers and short the lowest, equal-
  weighted; compare against random forest, deep MLP, and logistic-regression baselines.

## Evidence
- LSTM beats the baselines in predictive accuracy and (gross) strategy returns over 1992–2015.
- Returns are very high early in the sample and **decline sharply after 2010**; transaction costs
  further erode the post-2010 edge.

## Why it matters
A widely cited demonstration that sequence models can extract structure from financial time series,
paired with the sober reality that the edge is largest before the method is common and shrinks as
markets adapt — exactly the discipline the course emphasizes.

## Limitations and risks
- Pre-cost results overstate tradability; turnover is high.
- Susceptible to look-ahead in feature construction and to regime change; the decay warns against
  extrapolating backtest performance.

## Key references
- Fischer, T. & Krauss, C. (2018) — *Deep Learning with LSTM Networks for Financial Market Predictions* — European Journal of Operational Research
- Gu, S., Kelly, B. & Xiu, D. (2020) — *Empirical Asset Pricing via Machine Learning* — Review of Financial Studies
- Krauss, C., Do, X. A. & Huck, N. (2017) — *Deep Neural Networks, Gradient-Boosted Trees, Random Forests: Statistical Arbitrage on the S&P 500* — European Journal of Operational Research
"""

WIKIS["4a0fe8c9-08f7-4464-b2de-b19b1e79407c"] = """\
# Rare Disasters and Asset Markets in the Twentieth Century

**Source:** Barro, R. J. (2006). *Quarterly Journal of Economics* 121(3), 823–866.

## TL;DR
Revives the idea that **low-probability economic disasters** — large, rare contractions in output and
consumption — can explain the equity-premium puzzle. Calibrating disaster frequency and size from
twentieth-century international data (wars, depressions), Barro shows a consumption-based model with
*reasonable* risk aversion can match the high equity premium, the low risk-free rate, and high return
volatility.

## What it documents (models)
The Mehra-Prescott equity-premium puzzle: standard models need implausibly high risk aversion to
explain why stocks out-earn bonds so much. Barro adds a small annual probability of a severe disaster,
which makes equities genuinely risky in the states investors fear most.

## Mechanism
- Add a Rietz-style disaster: each year a small chance of a large drop in consumption/output.
- Even with moderate risk aversion, the threat of catastrophic losses raises the required equity
  premium and depresses the risk-free rate (precautionary saving).
- The model also rationalizes the high volatility of returns and the level of the price-dividend ratio.

## Evidence
- Empirical disaster distributions from 35 countries over the 20th century imply premia in line with
  the data, resolving the puzzle without extreme preferences.

## Why it matters
A foundational rare-disasters reference, reframing the equity premium as compensation for tail risk
that is hard to observe in short samples — a recurring caution about peso problems and the limits of
historical backtests.

## Limitations and risks
- Results hinge on the assumed disaster probability and size, which are hard to estimate from rare events.
- Distinguishing rare-disaster risk from behavioral explanations is empirically difficult.

## Key references
- Barro, R. (2006) — *Rare Disasters and Asset Markets in the Twentieth Century* — Quarterly Journal of Economics
- Rietz, T. (1988) — *The Equity Risk Premium: A Solution* — Journal of Monetary Economics
- Gabaix, X. (2012) — *Variable Rare Disasters* — Quarterly Journal of Economics
"""

WIKIS["60c81b79-39c4-4e0a-aac4-0cec7ecb56ac"] = """\
# Default Risk in Equity Returns

**Source:** Vassalou, M. & Xing, Y. (2004). *Journal of Finance* 59(2), 831–868.

## TL;DR
Computes firm-level **default likelihood** from a Merton-style option model and asks whether default
risk is priced in equities. It finds default risk is **systematic and priced**, that the size and
book-to-market effects are partly proxies for default risk, and that high default risk earns higher
returns — but mainly concentrated among **small, high-book-to-market** firms.

## What anomaly it documents
A link between credit/default risk and the equity cross-section: rather than a pure puzzle, Vassalou-
Xing argue some of the value and size premia compensate for default risk, with the effect strongest
where small and value characteristics coincide with high default likelihood.

## How it is constructed
- Estimate each firm's **default likelihood indicator (DLI)** from a Merton model (asset value and
  volatility backed out from equity), giving the probability assets fall below debt.
- Sort stocks on DLI and within size / book-to-market groups; run cross-sectional return tests.

## Evidence and replication
| Result | Source |
|--------|--------|
| Default risk is systematic and priced | this paper |
| High default risk → higher returns, concentrated in small / high-BM stocks | this paper |
| Size & BM premia partly reflect default-risk exposure | this paper |

Note the contrast with Campbell-Hilscher-Szilagyi (2008), who find the *most* distressed stocks earn
*low* returns — the sign of the distress-return relation is sensitive to the failure measure and
sample, and remains debated.

## Why it might work
- A rational default-risk premium: investors demand compensation for systematic bankruptcy risk.
- The size/value link suggests these characteristics partly capture distress exposure.

## Limitations and risks
- Default measures are model-dependent (Merton assumptions); the result conflicts with later distress-
  puzzle findings.
- Concentrated in illiquid small caps where costs and shorting frictions bite.

## Key references
- Vassalou, M. & Xing, Y. (2004) — *Default Risk in Equity Returns* — Journal of Finance
- Campbell, J., Hilscher, J. & Szilagyi, J. (2008) — *In Search of Distress Risk* — Journal of Finance
- Merton, R. (1974) — *On the Pricing of Corporate Debt* — Journal of Finance
"""

WIKIS["2f7133d9-f12f-48a6-9b92-a8d9722f34aa"] = """\
# Volume, Volatility, Price, and Profit When All Traders Are Above Average

**Source:** Odean, T. (1998). *Journal of Finance* 53(6), 1887–1934.

## TL;DR
A theoretical model of **overconfident traders** — investors who overestimate the precision of their
own information. Overconfidence raises **trading volume**, increases **volatility**, can push prices
away from fundamentals, and **lowers** the overconfident traders' own expected utility. It supplies
the mechanism behind the empirical finding that active individual traders underperform.

## What it documents (models)
How a specific, well-documented psychological bias maps into market-level outcomes. Different agents
(price-takers, insiders, market makers) are modeled as overconfident to varying degrees, and the
comparative statics on volume, volatility, and welfare are derived.

## Mechanism
- Overconfident traders treat noisy signals as more precise than they are, so they trade more
  aggressively on them.
- This **excess trading** raises volume and volatility and degrades price efficiency in some settings.
- Overconfident traders earn lower profits/utility than rational ones — they trade themselves into losses.

## Why it matters
The theoretical companion to Barber & Odean's empirical work ("Trading Is Hazardous to Your Wealth"):
it explains *why* overtrading happens and links a cognitive bias to the high volume and volatility that
rational-expectations models struggle to generate.

## Limitations and risks
- A stylized model; the degree of overconfidence is assumed, not derived.
- Predictions on volume/volatility are qualitative; mapping to specific markets requires care.

## Key references
- Odean, T. (1998) — *Volume, Volatility, Price, and Profit When All Traders Are Above Average* — Journal of Finance
- Barber, B. & Odean, T. (2000) — *Trading Is Hazardous to Your Wealth* — Journal of Finance
- Daniel, K., Hirshleifer, D. & Subrahmanyam, A. (1998) — *Investor Psychology and Security Market Under- and Overreactions* — Journal of Finance
"""

WIKIS["445eaa8a-af3b-4bb4-b8ff-c5baba728f6d"] = """\
# Size, Value, and Momentum in International Stock Returns

**Source:** Fama, E. F. & French, K. R. (2012). *Journal of Financial Economics* 105(3), 457–472.

## TL;DR
Examines size, value, and momentum premia across four regions — North America, Europe, Japan, and Asia
Pacific. Value premia exist everywhere and are **larger for small stocks**; momentum is strong
everywhere **except Japan**. Importantly, **global** factor models price regional portfolios poorly;
**local** (regional) factor models fit much better — evidence that markets are not fully integrated.

## What anomaly it documents
The international robustness (and limits) of the core factors: value and momentum generalize across
developed markets, but the right factor model is regional, not global.

## How it is constructed
- Build regional size, value (book-to-market), and momentum factors, plus global versions.
- Test local vs global three- and four-factor models on regional size-BM and size-momentum portfolios.

## Evidence and replication
| Finding | Source |
|---------|--------|
| Value premium everywhere, decreasing in size | this paper |
| Momentum everywhere except Japan | this paper |
| Local factor models >> global models for pricing regional returns | this paper |

## Why it might work
- Common behavioral/risk drivers of value and momentum across markets, but **segmented** pricing means
  regional factors capture local risks/sentiment better.
- Japan's weak momentum is a long-standing puzzle (possibly linked to its value-momentum correlation).

## Limitations and risks
- Implementation costs, currency effects, and data quality vary widely across regions.
- The integration question is sensitive to the test assets and sample period.

## Key references
- Fama, E. & French, K. (2012) — *Size, Value, and Momentum in International Stock Returns* — Journal of Financial Economics
- Asness, C., Moskowitz, T. & Pedersen, L. (2013) — *Value and Momentum Everywhere* — Journal of Finance
- Fama, E. & French, K. (1998) — *Value versus Growth: The International Evidence* — Journal of Finance
"""

WIKIS["5d7513dd-1a73-469a-b0de-b6d644510baa"] = """\
# The Sum of All FEARS: Investor Sentiment and Asset Prices

**Source:** Da, Z., Engelberg, J. & Gao, P. (2015). *Review of Financial Studies* 28(1), 1–32.

## TL;DR
Builds a daily, bottom-up **sentiment index (FEARS)** from the volume of household economic-anxiety
Google searches ("recession," "unemployment," "bankruptcy," etc.). High FEARS predicts **low same-day
market returns followed by a reversal** over the next days, higher volatility, and mutual-fund flows
**out of equities into bonds** — a clean, behavior-revealed measure of investor sentiment.

## What it documents
A direct, high-frequency sentiment proxy from search behavior (revealed worry), distinct from
attention measures: it captures the *direction* of household sentiment, not just its level.

## How it is measured
- Identify economically meaningful search terms and sign them by whether more searches reflect more
  anxiety; aggregate abnormal search volume into the daily **FEARS** index.
- Relate FEARS to next-day/next-week returns, realized volatility, and aggregate fund flows.

## Evidence
- High FEARS → **negative same-day returns that reverse** within days, consistent with temporary
  sentiment-driven mispricing.
- FEARS predicts **higher volatility** and flows from equity to bond funds — the footprint of a
  flight to safety.

## Why it matters
A landmark in search/alternative-data sentiment, complementing Da-Engelberg-Gao (2011) on attention:
it shows that aggregated household search behavior is a tradable-relevant, theory-consistent sentiment
signal.

## Limitations and risks
- Search-term selection and signing involve judgment; Google data is revised and regionally biased.
- Effects are short-horizon and reverse; costs limit exploitation.

## Key references
- Da, Z., Engelberg, J. & Gao, P. (2015) — *The Sum of All FEARS* — Review of Financial Studies
- Da, Z., Engelberg, J. & Gao, P. (2011) — *In Search of Attention* — Journal of Finance
- Baker, M. & Wurgler, J. (2006) — *Investor Sentiment and the Cross-Section of Stock Returns* — Journal of Finance
"""

WIKIS["44e47831-a69d-43b0-bbd3-3cb665b3f832"] = """\
# The Quality of Accruals and Earnings: The Role of Accrual Estimation Errors

**Source:** Dechow, P. M. & Dichev, I. D. (2002). *The Accounting Review* 77(s-1), 35–59.

## TL;DR
Proposes a measure of **earnings (accrual) quality** based on how well a firm's working-capital
accruals map into realized cash flows. Accruals require estimates of future cash flows; **estimation
errors** reduce accrual quality. Firms with low accrual quality have **less persistent earnings**, and
accrual quality is a priced characteristic — the basis for an accrual-quality factor.

## What anomaly it documents
A quality dimension of earnings: accruals that don't convert into cash signal noisy or managed
earnings, which predict lower earnings persistence and (in later work) lower returns / higher cost of
capital.

## How it is constructed
- Regress current working-capital accruals on **prior, current, and future** operating cash flows.
- The **residual standard deviation** of this regression measures accrual estimation error — low
  fit = low accrual quality.
- Sort firms on accrual quality and relate it to earnings persistence and returns (the AQ factor of
  Francis et al., 2005).

## Evidence
- Larger accrual estimation errors are associated with **smaller, more volatile** firms, longer
  operating cycles, and **less persistent** earnings.
- Accrual quality is subsequently shown to be priced (a risk/quality factor).

## Why it matters
A foundational accounting-quality construct underlying the accruals anomaly (Sloan, 1996) and
quality-factor investing; it formalizes why "earnings you can't trace to cash" are lower quality.

## Limitations and risks
- The measure mixes intentional manipulation with innocent estimation noise.
- Whether accrual quality is a priced *risk* factor or a mispricing is debated.

## Key references
- Dechow, P. & Dichev, I. (2002) — *The Quality of Accruals and Earnings* — The Accounting Review
- Sloan, R. (1996) — *Do Stock Prices Fully Reflect Information in Accruals and Cash Flows?* — The Accounting Review
- Francis, J., LaFond, R., Olsson, P. & Schipper, K. (2005) — *The Market Pricing of Accruals Quality* — Journal of Accounting and Economics
"""

WIKIS["2ec2b651-90c1-4c29-9c6d-5148c53b7b66"] = """\
# Empirical Performance of Alternative Option Pricing Models

**Source:** Bakshi, G., Cao, C. & Chen, Z. (1997). *Journal of Finance* 52(5), 2003–2049.

## TL;DR
A systematic horse race of option-pricing models on S&P 500 index options, comparing Black-Scholes,
stochastic volatility (SV), SV with jumps (SVJ), and SV with stochastic interest rates. The verdict:
**adding stochastic volatility is by far the most important improvement**; **jumps** further help for
pricing and hedging **short-maturity** options; **stochastic interest rates** add little.

## What it addresses
Which extensions of Black-Scholes actually matter in practice — judged not only by in-sample fit but by
out-of-sample pricing and **hedging** performance, the test that matters for desks.

## Method
- Estimate each model's parameters from option prices.
- Compare on (i) in-sample fit, (ii) out-of-sample pricing errors, and (iii) hedging errors, across
  moneyness and maturity buckets.

## Evidence
- **Stochastic volatility** delivers the largest gains over Black-Scholes on every metric.
- **Jumps** matter most for short-dated options, improving pricing and hedging there.
- **Stochastic interest rates** contribute little to option pricing/hedging.
- Even the best models leave systematic, moneyness-related errors — no model is complete.

## Why it matters
The empirical reference establishing the practical ranking of option-model features, validating the
Heston (SV) and Bates (SVJ) directions and guiding model choice for pricing and risk management.

## Limitations and risks
- Index-options results may not transfer to single names or other underlyings/periods.
- Parameter estimates are unstable; remaining pricing errors signal model risk in the tails.

## Key references
- Bakshi, G., Cao, C. & Chen, Z. (1997) — *Empirical Performance of Alternative Option Pricing Models* — Journal of Finance
- Heston, S. (1993) — *A Closed-Form Solution for Options with Stochastic Volatility* — Review of Financial Studies
- Bates, D. (1996) — *Jumps and Stochastic Volatility* — Review of Financial Studies
"""

WIKIS["e4d8a9dc-9dc7-40ad-816d-e3f40e11b2e7"] = """\
# Have Individual Stocks Become More Volatile? An Empirical Exploration of Idiosyncratic Risk

**Source:** Campbell, J. Y., Lettau, M., Malkiel, B. G. & Xu, Y. (2001). *Journal of Finance* 56(1),
1–43.

## TL;DR
Decomposes total stock volatility into **market, industry, and firm-specific (idiosyncratic)**
components and finds that, from 1962 to 1997, **idiosyncratic volatility rose substantially** while
market and industry volatility stayed roughly flat. As a result, average stock correlations fell and
the number of stocks needed to diversify a portfolio increased.

## What it documents
A trend in the *composition* of risk: more of a typical stock's variance became firm-specific over
time, with direct consequences for diversification, arbitrage, and the interpretation of volatility.

## How it is measured
- A simple variance decomposition that requires no factor-model betas: aggregate market, industry-
  within-market, and firm-within-industry return variances over time.
- Track each component's trend and the implied average correlation and diversification needs.

## Evidence
- **Idiosyncratic volatility trended up**; market volatility did not.
- Average correlations **declined**, so achieving a given diversification required **more stocks**
  over the sample.

## Why it matters
A foundational reference on idiosyncratic risk and diversification, and important background for the
idiosyncratic-volatility anomaly (Ang et al., 2006) and for understanding limits to arbitrage (more
idiosyncratic risk = more costly arbitrage).

## Limitations and risks
- The documented uptrend partly reverses in later samples; the trend is sample-dependent.
- The decomposition is descriptive, not a risk model; causes (new listings, sectoral shifts) are debated.

## Key references
- Campbell, J., Lettau, M., Malkiel, B. & Xu, Y. (2001) — *Have Individual Stocks Become More Volatile?* — Journal of Finance
- Ang, A., Hodrick, R., Xing, Y. & Zhang, X. (2006) — *The Cross-Section of Volatility and Expected Returns* — Journal of Finance
- Bali, T., Cakici, N. & Whitelaw, R. (2011) — *Maxing Out* — Journal of Financial Economics
"""

WIKIS["13ecbf1b-97e4-470c-964a-3dcc879fead0"] = """\
# Market Underreaction to Open Market Share Repurchases

**Source:** Ikenberry, D., Lakonishok, J. & Vermaelen, T. (1995). *Journal of Financial Economics*
39(2–3), 181–208.

## TL;DR
Firms announcing **open-market share repurchases** earn positive **long-run abnormal returns** — about
12% over the four years following the announcement — concentrated in **value (high book-to-market)**
firms. The market underreacts to the buyback signal, treating it as if managers' implicit "our stock is
cheap" message is only slowly incorporated.

## What anomaly it documents
A post-event drift: buyback announcements predict positive future abnormal returns, especially for
value stocks where management's undervaluation signal is most credible — evidence of underreaction to a
corporate signal.

## How it is constructed
- Identify open-market repurchase announcements.
- Compute long-run (multi-year) buy-and-hold abnormal returns versus size/book-to-market-matched
  benchmarks; split by book-to-market.

## Evidence and replication
| Group | 4-year abnormal return | Source |
|-------|------------------------|--------|
| All repurchasing firms | ≈ +12% | this paper |
| Value (high-BM) repurchasers | Substantially higher | this paper |
| Growth (low-BM) repurchasers | Little or none | this paper |

## Why it might work
- **Underreaction** to a credible undervaluation signal from insiders.
- Concentration in value firms fits the signaling interpretation (cheap firms buy back when truly cheap).

## Limitations and risks
- Long-run abnormal-return measurement is sensitive to the benchmark and bad-model problems (Fama, 1998).
- Buyback motives have shifted (e.g., offsetting option dilution), possibly weakening the signal over time.

## Key references
- Ikenberry, D., Lakonishok, J. & Vermaelen, T. (1995) — *Market Underreaction to Open Market Share Repurchases* — Journal of Financial Economics
- Loughran, T. & Ritter, J. (1995) — *The New Issues Puzzle* — Journal of Finance
- Fama, E. (1998) — *Market Efficiency, Long-Term Returns, and Behavioral Finance* — Journal of Financial Economics
"""

WIKIS["89af6c4a-c4de-4073-aec6-0347bddfbc54"] = """\
# Technological Innovation, Resource Allocation, and Growth

**Source:** Kogan, L., Papanikolaou, D., Seru, A. & Stoffman, N. (2017). *Quarterly Journal of
Economics* 132(2), 665–712.

## TL;DR
Constructs a measure of the **economic value of patents** from the stock-market reaction to patent
grants, and uses it to study innovation, reallocation, and returns. Innovation predicts growth and
reallocation of resources, and creates **creative destruction**: a firm's value can fall when
*competitors* innovate. The patent-value measure links innovation to the cross-section of returns.

## What it documents
A market-based measure of innovation output (more informative than raw patent counts) and its
macroeconomic and asset-pricing consequences — bridging the intangibles/innovation literature with
factor pricing.

## How it is constructed
- For each patent grant, estimate its economic value from the **idiosyncratic stock return** of the
  patenting firm in a window around the grant (filtering market movements).
- Aggregate to firm and economy levels; relate to subsequent growth, reallocation, and returns.

## Evidence
- The patent-value measure forecasts **firm growth and productivity** and aggregate growth.
- **Creative destruction:** innovation by competitors predicts **lower** value for incumbents — a
  cross-firm spillover with cross-sectional return implications.

## Why it matters
A widely used, openly shared measure of innovation value that connects intangible capital to returns,
relevant to value/growth, intangibles-adjusted valuation, and the economics of technological change.

## Limitations and risks
- The market-reaction measure inherits noise from the event window and confounding news.
- Patents capture only part of innovation; sectors differ in patent propensity.

## Key references
- Kogan, L., Papanikolaou, D., Seru, A. & Stoffman, N. (2017) — *Technological Innovation, Resource Allocation, and Growth* — Quarterly Journal of Economics
- Hall, B., Jaffe, A. & Trajtenberg, M. (2005) — *Market Value and Patent Citations* — RAND Journal of Economics
- Cohen, L., Diether, K. & Malloy, C. (2013) — *Misvaluing Innovation* — Review of Financial Studies
"""

WIKIS["ae4f9ab8-51e7-4349-a68f-fc1f12ce9133"] = """\
# Uncertainty about Government Policy and Stock Prices

**Source:** Pástor, Ľ. & Veronesi, P. (2012). *Journal of Finance* 67(4), 1219–1264.

## TL;DR
A general-equilibrium model showing that **uncertainty about government policy** raises risk premia,
volatility, and correlations among stocks — especially in a weak economy. On average, stock prices
**fall when a policy change is announced**, and the policy-uncertainty risk premium is larger when the
economy is fragile and when policy uncertainty is high.

## What it documents (models)
Two kinds of policy-related uncertainty: **political uncertainty** (which policy will be chosen) and
**impact uncertainty** (what its effect will be). Both are partly non-diversifiable and command risk
premia, linking the political environment to asset prices.

## Mechanism
- Investors learn about the profitability impact of the current and prospective policies.
- A policy change resolves some uncertainty but introduces new uncertainty; on average the announcement
  effect is **negative**, and it raises volatility and cross-stock correlations.
- Effects are **stronger in weak economies**, where the option to change policy is more likely exercised.

## Predictions / evidence
- Higher policy uncertainty → higher risk premia, volatility, and correlations; negative average
  announcement returns — broadly consistent with evidence around elections and major policy events
  (and with the Baker-Bloom-Davis policy-uncertainty index).

## Why it matters
The theoretical foundation for the political/policy-uncertainty literature, explaining why
non-market, governmental risks are priced and why correlations spike around policy events — relevant to
macro overlays and risk management.

## Limitations and risks
- A stylized equilibrium model; mapping "policy uncertainty" to measurable variables is hard.
- Identification around policy events is confounded by concurrent economic news.

## Key references
- Pástor, Ľ. & Veronesi, P. (2012) — *Uncertainty about Government Policy and Stock Prices* — Journal of Finance
- Pástor, Ľ. & Veronesi, P. (2013) — *Political Uncertainty and Risk Premia* — Journal of Financial Economics
- Baker, S., Bloom, N. & Davis, S. (2016) — *Measuring Economic Policy Uncertainty* — Quarterly Journal of Economics
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
