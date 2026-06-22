"""
author_canonical_wikis_2.py — second batch of hand-authored wikis for canonical papers.

Covers volatility modelling (Glosten-Jagannathan-Runkle, Schwert, Andersen-Bollerslev-Diebold-Labys),
behavioural finance (Barberis-Shleifer-Vishny, Hong-Stein, Barber-Odean x2), text/attention as data
(Tetlock, Da-Engelberg-Gao), liquidity (Brunnermeier-Pedersen), out-of-sample prediction
(Campbell-Thompson), and consumption-based asset pricing (Campbell-Cochrane). Public, paper-focused.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_canonical_wikis_2.py --dry-run
    ...                                          python pipeline/author_canonical_wikis_2.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["bcf2adc4-03b9-44c9-b33a-340251a2bc76"] = """\
# On the Relation between the Expected Value and the Volatility of the Nominal Excess Return on Stocks

**Source:** Glosten, L. R., Jagannathan, R. & Runkle, D. E. (1993). *Journal of Finance* 48(5),
1779–1801.

## TL;DR
Introduces what is now known as the **GJR-GARCH** model — a volatility model that lets bad news raise
future volatility more than good news of the same size (the leverage/asymmetry effect) — and uses it
to study the risk-return trade-off. Once asymmetry and the nominal interest rate are allowed for, the
relation between conditional mean and conditional volatility can actually be *negative*, contradicting
the simple intuition that higher risk must mean higher expected return.

## What it addresses
Standard GARCH treats positive and negative return shocks symmetrically, yet equity volatility rises
much more after market declines. The paper asks how this asymmetry affects the estimated relationship
between expected returns and risk.

## The model
GJR augments GARCH(1,1) with a term that activates only for negative shocks:
σ²_t = ω + α·ε²_{t-1} + γ·ε²_{t-1}·I(ε_{t-1}<0) + β·σ²_{t-1}, where I(·) is an indicator and a
positive γ captures the larger impact of negative returns. It is the asymmetric counterpart to
Nelson's EGARCH.

## Evidence
- A positive, significant asymmetry term γ: negative shocks drive volatility far more than positive ones.
- After modelling this asymmetry (and controlling for the nominal rate), the estimated relation
  between the conditional mean and conditional variance of excess returns is weak or negative — a
  caution against naive "more volatility, more return" reasoning.

## Why it matters
GJR-GARCH is a staple of volatility forecasting and risk management, sitting alongside GARCH and
EGARCH as the standard way to capture the leverage effect in daily return series.

## Limitations and risks
- A parametric daily model: it cannot exploit intraday information (see realized volatility).
- Asymmetry parameters can be unstable across regimes; the risk-return result is specification-sensitive.

## Key references
- Glosten, L., Jagannathan, R. & Runkle, D. (1993) — *On the Relation between the Expected Value and the Volatility of the Nominal Excess Return on Stocks* — Journal of Finance
- Bollerslev, T. (1986) — *Generalized Autoregressive Conditional Heteroskedasticity* — Journal of Econometrics
- Nelson, D. (1991) — *Conditional Heteroskedasticity in Asset Returns (EGARCH)* — Econometrica
"""

WIKIS["329043d3-99c5-4d00-ab64-d8673f5ace01"] = """\
# Modeling and Forecasting Realized Volatility

**Source:** Andersen, T. G., Bollerslev, T., Diebold, F. X. & Labys, P. (2003). *Econometrica* 71(2),
579–625.

## TL;DR
Shows that volatility, usually treated as a latent variable to be filtered with GARCH-type models,
can instead be **measured directly** by summing squared high-frequency intraday returns — "realized
volatility." Treated as observable, realized volatility has clean, robust time-series properties
(approximately log-normal, with long-memory persistence) and simple models of it forecast future
volatility better than traditional daily GARCH.

## What it addresses
Daily GARCH/stochastic-volatility models infer volatility from a single return per day and impose
strong parametric structure. With intraday data, volatility over a day can be estimated almost
directly, side-stepping much of that machinery.

## Method
- **Realized volatility:** sum the squared (or use the quadratic variation of) intraday returns over
  fixed sampling intervals to estimate each day's integrated variance.
- Model the resulting daily realized-volatility series with long-memory time-series models (e.g.
  fractionally integrated / log-VAR), exploiting its near-Gaussian behaviour in logs.

## Evidence
- Realized volatilities and correlations are approximately log-normal and display **long-range
  dependence** (slowly decaying autocorrelation).
- Reduced-form forecasts built on realized volatility **outperform daily GARCH** out of sample.

## Why it matters
Realized volatility turned volatility into something close to an observable, enabling the
high-frequency volatility literature, the HAR model (Corsi), realized-covariance estimation, and
modern risk forecasting.

## Limitations and risks
- **Microstructure noise** (bid-ask bounce, discreteness) biases naive realized variance at very fine
  sampling; later estimators (realized kernels, pre-averaging) correct for it.
- Requires clean high-frequency data; jumps and overnight gaps need separate handling.

## Key references
- Andersen, T., Bollerslev, T., Diebold, F. & Labys, P. (2003) — *Modeling and Forecasting Realized Volatility* — Econometrica
- Barndorff-Nielsen, O. & Shephard, N. (2002) — *Econometric Analysis of Realized Volatility* — JRSS B
- Corsi, F. (2009) — *A Simple Approximate Long-Memory Model of Realized Volatility (HAR)* — Journal of Financial Econometrics
"""

WIKIS["133ed86c-c802-4f3f-a1d9-5bbe35fa162d"] = """\
# Why Does Stock Market Volatility Change Over Time?

**Source:** Schwert, G. W. (1989). *Journal of Finance* 44(5), 1115–1153.

## TL;DR
A foundational empirical study documenting that aggregate stock-market volatility varies substantially
over time and asking what drives it. Volatility is higher during recessions and financial crises and
around major macro events, but — strikingly — its links to the volatility of underlying macroeconomic
fundamentals (inflation, output, money growth) are surprisingly weak.

## What it addresses
Before this paper, time-varying volatility was modelled statistically (ARCH) but its economic drivers
were not well documented. Schwert assembles long monthly series back to the 19th century and relates
stock volatility to real and nominal macro variables, leverage, and trading activity.

## Main findings
- Stock volatility is **countercyclical**: markedly higher in recessions and during crises (e.g. the
  Great Depression, 1987).
- It comoves with financial **leverage** and with bond-market and macro volatility, but these explain
  only a modest share of its variation.
- Much of the time-variation in volatility remains **unexplained** by observable fundamentals — a
  puzzle that still motivates research.

## Methodology
Constructs monthly realized volatility from daily returns over a very long sample and regresses it on
macroeconomic volatility measures, leverage, recession indicators, and trading volume.

## Why it matters
It set the empirical agenda for understanding volatility dynamics, established the countercyclical
volatility fact, and framed the still-open question of how much volatility reflects fundamentals
versus market behaviour.

## Limitations and risks
- Pre-dates high-frequency realized volatility; relies on monthly aggregates of daily data.
- Associations are largely correlational, not causal identification.

## Key references
- Schwert, G. W. (1989) — *Why Does Stock Market Volatility Change Over Time?* — Journal of Finance
- Engle, R. (1982) — *Autoregressive Conditional Heteroskedasticity (ARCH)* — Econometrica
- Bloom, N. (2009) — *The Impact of Uncertainty Shocks* — Econometrica
"""

WIKIS["988afb8a-a515-42cd-a72f-1c4c0fefc3f3"] = """\
# A Model of Investor Sentiment

**Source:** Barberis, N., Shleifer, A. & Vishny, R. (1998). *Journal of Financial Economics* 49(3),
307–343.

## TL;DR
A behavioural model that reconciles two facts that seem to contradict each other: short-horizon
**underreaction** to news (which produces momentum and post-earnings drift) and long-horizon
**overreaction** (which produces value and long-run reversal). A single representative investor,
prone to two well-documented psychological biases, generates both.

## What it documents (models)
The investor wrongly believes earnings follow one of two regimes — mean-reverting or trending —
switching between them based on recent data. **Conservatism** makes beliefs update too slowly to news
(underreaction → drift and momentum), while **representativeness** makes the investor over-extrapolate
streaks (overreaction → reversal and the value premium).

## Mechanism
- Earnings actually follow a random walk, but the investor models them with a regime-switching process.
- After a single surprise, beliefs adjust sluggishly → prices underreact and drift.
- After a long run of like-signed news, the investor concludes a trend exists and overreacts → prices
  overshoot and later reverse.

## Why it matters
It provides a unified, parsimonious behavioural foundation for momentum/drift and value/reversal,
which had been treated as separate anomalies, and helped launch the formal behavioural-finance
modelling literature.

## Limitations and risks
- A stylised single-agent model; it abstracts from arbitrage, heterogeneity, and equilibrium price
  formation.
- It rationalises known anomalies rather than predicting new ones, and the biases are imposed rather
  than derived.

## Key references
- Barberis, N., Shleifer, A. & Vishny, R. (1998) — *A Model of Investor Sentiment* — Journal of Financial Economics
- Daniel, K., Hirshleifer, D. & Subrahmanyam, A. (1998) — *Investor Psychology and Security Market Under- and Overreactions* — Journal of Finance
- Hong, H. & Stein, J. (1999) — *A Unified Theory of Underreaction, Momentum Trading and Overreaction* — Journal of Finance
"""

WIKIS["cb6d2fe8-7b12-4434-bd42-693e98104c2d"] = """\
# A Unified Theory of Underreaction, Momentum Trading and Overreaction in Asset Markets

**Source:** Hong, H. & Stein, J. C. (1999). *Journal of Finance* 54(6), 2143–2184.

## TL;DR
Explains momentum and long-run reversal with two types of boundedly rational traders interacting in a
market — "newswatchers" and "momentum traders" — rather than with individual psychology. Gradual
diffusion of information causes initial underreaction; momentum traders then chase the resulting trend
and push prices to overreact, which later reverses.

## What it documents (models)
- **Newswatchers** trade on private fundamental signals but ignore prices; information diffuses slowly
  across them, so prices underreact at first.
- **Momentum traders** trade on past price changes with simple strategies; they arbitrage the
  underreaction but, because they can only use simple rules, they overshoot.
- The interaction yields underreaction at short horizons (momentum) followed by overreaction and
  reversal at long horizons.

## Mechanism / predictions
- Momentum should be stronger where information diffuses more slowly — e.g. among small firms and
  stocks with low analyst coverage. Hong, Lim & Stein (2000) confirm this empirically.

## Why it matters
It grounds momentum in market microstructure and information diffusion rather than in a single
investor's biases, and generates testable cross-sectional predictions about where momentum is strongest.

## Limitations and risks
- Boundedly rational behaviour and the restriction to simple momentum rules are assumptions.
- Like other behavioural models, it interprets existing anomalies; the trader types are stylised.

## Key references
- Hong, H. & Stein, J. (1999) — *A Unified Theory of Underreaction, Momentum Trading and Overreaction* — Journal of Finance
- Hong, H., Lim, T. & Stein, J. (2000) — *Bad News Travels Slowly* — Journal of Finance
- Barberis, N., Shleifer, A. & Vishny, R. (1998) — *A Model of Investor Sentiment* — Journal of Financial Economics
"""

WIKIS["9239c3c3-1896-42c3-8544-cd84725438c7"] = """\
# All That Glitters: The Effect of Attention and News on the Buying Behavior of Individual and Institutional Investors

**Source:** Barber, B. M. & Odean, T. (2008). *Review of Financial Studies* 21(2), 785–818.

## TL;DR
Individual investors are **net buyers of attention-grabbing stocks** — those in the news, with
abnormally high trading volume, or with extreme one-day returns. Because investors can short only what
they own but can buy from thousands of candidates, attention solves their *search problem on the buy
side*. Institutions, who search more systematically, show much weaker attention-driven buying.

## What anomaly it documents
An asymmetry in how attention shapes trading: attention drives buying far more than selling for
retail investors, producing temporary price pressure in high-attention stocks.

## How it is measured
- **Attention proxies:** daily news coverage, abnormal trading volume, and extreme (high or low)
  prior-day returns.
- Compare net buying (buy-minus-sell imbalance) of individual vs institutional investors conditional
  on these proxies.

## Evidence
- Individuals are strong net buyers of high-attention stocks regardless of whether the news is good or
  bad; the effect is robust across the three attention measures.
- Institutional buying is far less sensitive to attention.

## Why it matters
A cornerstone of the "attention as data" literature: it motivates using news flow, volume spikes, and
later search/social signals to predict retail order flow and short-horizon price pressure — directly
relevant to text-based and alternative-data signals.

## Limitations and risks
- The buying pressure is largely transient; turning it into a tradable edge runs into costs and
  reversal.
- Attention proxies are noisy and have shifted with the rise of online/retail platforms since 2008.

## Key references
- Barber, B. & Odean, T. (2008) — *All That Glitters* — Review of Financial Studies
- Da, Z., Engelberg, J. & Gao, P. (2011) — *In Search of Attention* — Journal of Finance
- Tetlock, P. (2007) — *Giving Content to Investor Sentiment* — Journal of Finance
"""

WIKIS["d30eec30-b243-498c-845f-729cd527d7cb"] = """\
# Trading Is Hazardous to Your Wealth: The Common Stock Investment Performance of Individual Investors

**Source:** Barber, B. M. & Odean, T. (2000). *Journal of Finance* 55(2), 773–806.

## TL;DR
Using the accounts of tens of thousands of individual investors at a discount broker, the paper shows
that those who **trade the most earn the lowest net returns**. Gross returns are similar across
investors, but transaction costs from frequent trading destroy performance — the average household
underperforms the market net of costs, and the most active quintile underperforms badly.

## What it documents
A direct, account-level demonstration that excessive trading — consistent with overconfidence — is
costly. It connects a behavioural bias to a measurable wealth loss.

## How it is measured
- Analyse ~66,000 households' trades and positions (1991–1996) at a large discount broker.
- Compute gross and net returns, sorted by turnover, and benchmark against market and characteristic
  models.

## Evidence
- Average household's gross return ≈ market; **net** return underperforms after costs.
- The **highest-turnover** quintile underperforms the lowest by several percentage points per year,
  driven almost entirely by trading costs rather than bad stock selection.

## Why it matters
Foundational evidence for the costs of overtrading and overconfidence, and a sober reminder that an
apparent gross edge can be entirely consumed by turnover and costs — the same lesson that
cost-aware backtesting enforces for systematic strategies.

## Limitations and risks
- One broker, one period (mid-1990s); generalisation to other investors/eras is assumed.
- It documents costs of trading, not whether any active strategy can overcome them.

## Key references
- Barber, B. & Odean, T. (2000) — *Trading Is Hazardous to Your Wealth* — Journal of Finance
- Odean, T. (1999) — *Do Investors Trade Too Much?* — American Economic Review
- Barber, B. & Odean, T. (2001) — *Boys Will Be Boys: Gender, Overconfidence, and Common Stock Investment* — Quarterly Journal of Economics
"""

WIKIS["f9c5a120-6fed-417e-ac7b-26689a8a7d6b"] = """\
# Giving Content to Investor Sentiment: The Role of Media in the Stock Market

**Source:** Tetlock, P. C. (2007). *Journal of Finance* 62(3), 1139–1168.

## TL;DR
One of the first papers to turn **news text into a quantitative trading signal**. Tetlock measures the
pessimism of the Wall Street Journal's daily "Abreast of the Market" column using a content-analysis
dictionary and shows that high media pessimism predicts downward pressure on the market followed by a
reversion to fundamentals, and that unusually high or low pessimism predicts elevated trading volume.

## What anomaly it documents
Media tone carries information (or sentiment) about near-term returns and volume beyond fundamentals —
a textual predictor of short-horizon market behaviour consistent with noise-trading/sentiment theories.

## How it is measured
- **Text source:** the WSJ "Abreast of the Market" column, daily.
- **Sentiment score:** word counts mapped through the Harvard-IV-4 psychosocial dictionary, reduced
  (via principal components) to a "pessimism" factor.
- Relate the pessimism factor to next-day and subsequent market returns and to trading volume in a VAR.

## Evidence
- High pessimism predicts **downward price pressure** that **reverts** over the following days,
  consistent with temporary sentiment-driven mispricing rather than new fundamental information.
- Both unusually high and unusually low pessimism predict **high trading volume**.

## Why it matters
The template for natural-language processing in finance: it established that systematically scored
text predicts markets, paving the way for dictionary methods (and the finance-specific Loughran-McDonald
lexicon), and later embedding- and LLM-based approaches.

## Limitations and risks
- General-purpose dictionaries misclassify finance language (motivating Loughran-McDonald 2011).
- A single column/era; effects are short-horizon and small relative to costs.
- **Timestamp/leakage care** is essential when aligning news with returns.

## Key references
- Tetlock, P. (2007) — *Giving Content to Investor Sentiment* — Journal of Finance
- Loughran, T. & McDonald, B. (2011) — *When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks* — Journal of Finance
- Tetlock, P., Saar-Tsechansky, M. & Macskassy, S. (2008) — *More Than Words: Quantifying Language to Measure Firms' Fundamentals* — Journal of Finance
"""

WIKIS["ae7425d5-7271-43b1-8bfb-83b3e5d0f5fe"] = """\
# In Search of Attention

**Source:** Da, Z., Engelberg, J. & Gao, P. (2011). *Journal of Finance* 66(5), 1461–1499.

## TL;DR
Proposes **Google search volume (SVI)** as a direct, timely measure of *retail* investor attention,
rather than inferring attention from news or volume. Higher search interest predicts higher prices
over the next two weeks and an eventual reversal within the year, and predicts stronger first-day IPO
returns — confirming the price-pressure implications of attention theories with a clean proxy.

## What anomaly it documents
Retail attention, captured by search activity, drives temporary buying pressure: attention-grabbing
stocks rise then revert, an effect consistent with Barber & Odean's (2008) attention-induced buying.

## How it is measured
- **Attention proxy:** abnormal Google Search Volume Index (SVI) for stock tickers — a direct,
  high-frequency signal of retail interest that does not require the stock to already be in the news.
- Relate abnormal SVI to subsequent returns, reversals, and IPO first-day performance.

## Evidence
- A spike in SVI predicts **higher returns over the next ~2 weeks** and a **reversal within a year**.
- SVI leads, rather than lags, news and volume-based attention measures.
- High pre-IPO search interest predicts **larger first-day IPO returns** and subsequent
  underperformance.

## Why it matters
A landmark in alternative-data finance: it showed that web/search data is a measurable, predictive
attention signal, opening the door to social-media, app-usage, and other behavioural proxies now
common in quantitative research.

## Limitations and risks
- Search-data availability, revisions, and ticker ambiguity complicate real-time use.
- The effect is short-horizon and reverses; costs and capacity limit exploitation.

## Key references
- Da, Z., Engelberg, J. & Gao, P. (2011) — *In Search of Attention* — Journal of Finance
- Barber, B. & Odean, T. (2008) — *All That Glitters* — Review of Financial Studies
- Da, Z., Engelberg, J. & Gao, P. (2015) — *The Sum of All FEARS: Investor Sentiment and Asset Prices* — Review of Financial Studies
"""

WIKIS["fd023871-b78c-4cbd-bc27-483f1a14a068"] = """\
# Market Liquidity and Funding Liquidity

**Source:** Brunnermeier, M. K. & Pedersen, L. H. (2009). *Review of Financial Studies* 22(6),
2201–2238.

## TL;DR
A model connecting two kinds of liquidity: **market liquidity** (how easily an asset can be traded)
and **funding liquidity** (how easily traders can finance their positions). The two reinforce each
other, producing **liquidity spirals** that explain why liquidity can evaporate suddenly, why it is
correlated across assets, and why it dries up most for high-margin, volatile securities — a framework
that fits the 2007–2009 crisis closely.

## What it documents (models)
When speculators provide market liquidity but face funding constraints (margins, capital), a shock
that reduces funding forces them to cut positions, which widens spreads and raises volatility, which
in turn raises margins and tightens funding further — a self-reinforcing destabilising loop.

## Mechanism
- **Margin spiral:** falling prices raise margins, forcing deleveraging, lowering prices further.
- **Loss spiral:** mark-to-market losses erode capital, shrinking position capacity.
- Both link funding and market liquidity, generating commonality, flight-to-quality, and fragility.

## Predictions
- Liquidity is **fragile** (can collapse abruptly), **comoves across assets**, and is linked to
  volatility and margins; flights to quality occur when funding tightens.

## Why it matters
Provides the theoretical backbone for understanding liquidity crises and systemic risk, and explains
empirical regularities (commonality in liquidity, liquidity risk premia) documented by Amihud,
Pástor-Stambaugh, and others.

## Limitations and risks
- A stylised model; quantitative calibration to real markets is difficult.
- Focuses on funding-constrained intermediaries; other liquidity frictions are abstracted away.

## Key references
- Brunnermeier, M. & Pedersen, L. (2009) — *Market Liquidity and Funding Liquidity* — Review of Financial Studies
- Amihud, Y. (2002) — *Illiquidity and Stock Returns* — Journal of Financial Markets
- Pástor, Ľ. & Stambaugh, R. (2003) — *Liquidity Risk and Expected Stock Returns* — Journal of Political Economy
"""

WIKIS["5ff81be5-0f08-4509-a0be-467e5130e4a0"] = """\
# Predicting Excess Stock Returns Out of Sample: Can Anything Beat the Historical Average?

**Source:** Campbell, J. Y. & Thompson, S. B. (2008). *Review of Financial Studies* 21(4), 1509–1531.

## TL;DR
A constructive reply to Welch & Goyal (2008). Predictor variables fail out of sample when used naively,
but imposing simple, **economically motivated restrictions** — forcing regression coefficients to have
the theoretically sensible sign and equity-premium forecasts to be non-negative — produces small but
genuine out-of-sample predictability that is **economically meaningful** for a mean-variance investor.

## The problem it addresses
Welch & Goyal showed that equity-premium predictors do not beat the historical-average benchmark out
of sample. Campbell & Thompson ask whether disciplined use of prior knowledge can recover usable
predictability.

## Main findings
- With sign and non-negativity restrictions, several predictors deliver **positive out-of-sample R²**,
  on the order of **~0.5% per month**.
- Though tiny in R² terms, this translates into a worthwhile improvement in portfolio Sharpe ratio —
  they show how a small R² maps to a meaningful certainty-equivalent gain.

## Methodology
Out-of-sample predictive regressions for standard valuation ratios and rates, with theory-based
constraints, benchmarked against the prevailing mean and evaluated by out-of-sample R² and the implied
portfolio utility gain.

## Implications for factor investing
- **Even a tiny but real OOS R² can be valuable** once converted into position sizing.
- Imposing **economic priors and constraints** stabilises forecasts and beats unconstrained estimation.
- Always evaluate predictability out of sample and translate it into the decision it will drive.

## Key references
- Campbell, J. & Thompson, S. (2008) — *Predicting Excess Stock Returns Out of Sample* — Review of Financial Studies
- Welch, I. & Goyal, A. (2008) — *A Comprehensive Look at the Empirical Performance of Equity Premium Prediction* — Review of Financial Studies
- Rapach, D., Strauss, J. & Zhou, G. (2010) — *Out-of-Sample Equity Premium Prediction* — Review of Financial Studies
"""

WIKIS["55d1f52f-83fe-4da2-afb4-718c610b9be7"] = """\
# By Force of Habit: A Consumption-Based Explanation of Aggregate Stock Market Behavior

**Source:** Campbell, J. Y. & Cochrane, J. H. (1999). *Journal of Political Economy* 107(2), 205–251.

## TL;DR
A consumption-based asset-pricing model in which investors form a slow-moving **habit** — a reference
level of consumption — so that effective risk aversion rises when consumption falls toward habit in
bad times. This single mechanism generates a high and time-varying equity premium, volatile and
countercyclical Sharpe ratios, return predictability, and excess volatility, helping resolve the
equity-premium and related puzzles.

## What it documents (models)
Standard consumption-based models (power utility) cannot match the high equity premium or the
volatility and predictability of returns. Campbell-Cochrane add an external habit that makes the
representative agent far more risk-averse in downturns.

## Mechanism
- Utility depends on consumption **relative to a habit** that adjusts slowly to past consumption.
- In recessions, consumption nears the habit, **risk aversion spikes**, raising required returns.
- This makes the price-dividend ratio procyclical and expected returns countercyclical — producing
  predictability and volatility from a smooth consumption process.

## Why it matters
A benchmark model for time-varying risk premia and a rational counterpart to behavioural explanations
of predictability: it shows that countercyclical risk aversion alone can generate many of the
"anomalous" features of aggregate returns.

## Limitations and risks
- The habit specification is engineered to fit moments; its micro-foundations are debated.
- A representative-agent, aggregate model; it does not address the cross-section directly.

## Key references
- Campbell, J. & Cochrane, J. (1999) — *By Force of Habit* — Journal of Political Economy
- Mehra, R. & Prescott, E. (1985) — *The Equity Premium: A Puzzle* — Journal of Monetary Economics
- Bansal, R. & Yaron, A. (2004) — *Risks for the Long Run* — Journal of Finance
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
