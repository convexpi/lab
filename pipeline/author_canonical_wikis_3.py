"""
author_canonical_wikis_3.py — third batch of hand-authored wikis for canonical papers.

Covers text/NLP (Loughran-McDonald), cross-asset factors (Asness-Moskowitz-Pedersen), information
microstructure (Easley-O'Hara), information diffusion and momentum (Hong-Lim-Stein,
Jegadeesh-Titman 2001), return predictability (Campbell-Shiller), volatility asymmetry (Engle-Ng),
governance (Gompers-Ishii-Metrick), social norms / ESG (Hong-Kacperczyk), the IPO long-run anomaly
(Ritter), American-option numerics (Longstaff-Schwartz), and accounting valuation (Ohlson). Public,
paper-focused content only.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_canonical_wikis_3.py --dry-run
    ...                                          python pipeline/author_canonical_wikis_3.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["8ef67078-4004-4d1b-8ed2-ffb81935b9a9"] = """\
# When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks

**Source:** Loughran, T. & McDonald, B. (2011). *Journal of Finance* 66(1), 35–65.

## TL;DR
Shows that the general-purpose Harvard-IV psychosocial dictionary — then standard for measuring tone
in financial text — badly misclassifies finance language: roughly three-quarters of its "negative"
words (tax, cost, liability, capital, vice, depreciation) are not negative in a business context.
The authors build **finance-specific word lists** (negative, positive, uncertainty, litigious, modal)
that have since become the default lexicon for textual analysis in finance.

## What it documents
A measurement problem and its fix. Using the wrong dictionary injects systematic noise — and bias —
into sentiment measures because common, neutral business terms are counted as negative.

## How it is constructed
- Parse the universe of 10-K filings and count word frequencies.
- Show that Harvard-IV "negative" words are dominated by terms that are neutral in finance.
- Build curated finance dictionaries (the "Loughran-McDonald" lists), and weight words by inverse
  document frequency (tf-idf) rather than raw counts to downweight ubiquitous terms.

## Evidence
- The finance negative-word measure relates to filing-period returns, return volatility, trading
  volume, and subsequent earnings more cleanly than the Harvard measure.
- Proper weighting (tf-idf) and the finance lexicon materially change which filings look "negative."

## Why it matters
The foundational reference for dictionary-based NLP in finance: it established that domain-specific
lexicons matter and supplied the word lists used in thousands of later studies, and it frames the
trade-offs that embeddings and LLM-based approaches must still beat.

## Limitations and risks
- Bag-of-words ignores context, negation, and sarcasm — limitations addressed by later embedding/LLM
  methods.
- Dictionaries drift as corporate language evolves; results depend on parsing and filing-date alignment.

## Key references
- Loughran, T. & McDonald, B. (2011) — *When Is a Liability Not a Liability?* — Journal of Finance
- Tetlock, P. (2007) — *Giving Content to Investor Sentiment* — Journal of Finance
- Loughran, T. & McDonald, B. (2016) — *Textual Analysis in Accounting and Finance: A Survey* — Journal of Accounting Research
"""

WIKIS["b6991b10-0612-4b0f-8073-0051507d5161"] = """\
# Value and Momentum Everywhere

**Source:** Asness, C. S., Moskowitz, T. J. & Pedersen, L. H. (2013). *Journal of Finance* 68(3),
929–985.

## TL;DR
Value and momentum are not equity quirks: both earn premia **consistently across eight markets and
asset classes** — individual stocks in the US, UK, Europe and Japan, plus country equity indices,
government bonds, currencies, and commodities. Value and momentum are **negatively correlated**, so a
combined value-plus-momentum portfolio diversifies beautifully, and both load on common global
factors, including funding-liquidity risk.

## What anomaly it documents
A unified, global factor structure: value (cheap minus expensive) and momentum (recent winners minus
losers) appear everywhere, with correlated value strategies across asset classes and correlated
momentum strategies across asset classes — pointing to common drivers rather than asset-specific stories.

## How to construct it
- **Value signal:** an asset-class-appropriate cheapness measure (book-to-market for stocks, 5-year
  reversal / real yields / spot-relative measures for other classes).
- **Momentum signal:** the past ~12-month return (skipping the most recent month).
- Form long-short value and momentum portfolios within each market, then combine; the 50/50
  value+momentum mix has a far higher Sharpe than either alone.

## Evidence and replication
| Strategy | Result | Source |
|----------|--------|--------|
| Value or momentum, single class | Positive but volatile | this paper |
| Combined value+momentum, global | Much higher Sharpe; value-momentum correlation strongly negative | this paper |

The combined factor's strength comes from the negative value-momentum correlation; both also carry
liquidity-risk exposure that partly explains their returns.

## Why it might work
- **Common global risks** (notably funding-liquidity risk) plus behavioural underreaction/overreaction.
- The negative value-momentum correlation suggests they capture complementary mispricings.

## Limitations and risks
- Implementation costs and shorting constraints differ sharply across asset classes.
- Both strategies have crash risk; the combination mitigates but does not eliminate it.

## Key references
- Asness, C., Moskowitz, T. & Pedersen, L. (2013) — *Value and Momentum Everywhere* — Journal of Finance
- Fama, E. & French, K. (1992) — *The Cross-Section of Expected Stock Returns* — Journal of Finance
- Jegadeesh, N. & Titman, S. (1993) — *Returns to Buying Winners and Selling Losers* — Journal of Finance
"""

WIKIS["63e13856-b68d-4ff0-9bdb-7e988a3132c1"] = """\
# Information and the Cost of Capital

**Source:** Easley, D. & O'Hara, M. (2004). *Journal of Finance* 59(4), 1553–1583.

## TL;DR
Shows that the **composition of information** — how much is private versus public — affects a firm's
cost of capital. Investors require higher expected returns to hold stocks with more
private-information risk, because the privately informed trade against the uninformed in a way the
uninformed cannot diversify away. It links market microstructure (informed trading) to asset pricing.

## What it documents (models)
A rational-expectations model in which the quantity and quality of information, and the split between
public and private signals, determine the systematic risk borne by uninformed investors and hence
required returns.

## Mechanism
- Privately informed traders profit at the expense of the uninformed; this informed-trading risk is
  priced because uninformed investors hold portfolios tilted by their information disadvantage.
- More public disclosure (and less private information) lowers this risk premium — a channel from
  transparency to the cost of capital.

## Predictions / evidence
- Stocks with a higher **probability of informed trading (PIN)** — a microstructure estimate from
  order flow — should command higher expected returns, an empirically testable implication explored
  in related work by the authors.

## Why it matters
A foundational bridge from microstructure to asset pricing: it gives a theoretical reason that
information asymmetry and order-flow toxicity should be priced, motivating PIN and later toxicity
measures (e.g. VPIN) and the disclosure-and-cost-of-capital literature.

## Limitations and risks
- PIN estimation is noisy and debated; whether information risk is truly priced is contested.
- A stylised model; identifying the public/private information split empirically is hard.

## Key references
- Easley, D. & O'Hara, M. (2004) — *Information and the Cost of Capital* — Journal of Finance
- Easley, D., Kiefer, N., O'Hara, M. & Paperman, J. (1996) — *Liquidity, Information, and Infrequently Traded Stocks (PIN)* — Journal of Finance
- Glosten, L. & Milgrom, P. (1985) — *Bid, Ask and Transaction Prices in a Specialist Market* — Journal of Financial Economics
"""

WIKIS["2e8b463d-39b4-40c9-8e4f-cfe1dbe365a5"] = """\
# Bad News Travels Slowly: Size, Analyst Coverage, and the Profitability of Momentum Strategies

**Source:** Hong, H., Lim, T. & Stein, J. C. (2000). *Journal of Finance* 55(1), 265–295.

## TL;DR
A direct test of the gradual-information-diffusion theory of momentum (Hong & Stein, 1999). Holding
size fixed, **momentum is much stronger among stocks with low analyst coverage**, and the effect is
concentrated in **past losers** — bad news diffuses especially slowly because firms and analysts are
reluctant to publicise it. Momentum looks like an information-diffusion phenomenon, not just a risk premium.

## What anomaly it documents
The cross-sectional structure of momentum: where information spreads slowly (small firms, thin analyst
coverage), past returns predict future returns more strongly, and the asymmetry (stronger for losers)
fits the idea that negative information is released most reluctantly.

## How it is measured
- Sort stocks by **residual analyst coverage** (coverage orthogonalised to size) and by size.
- Within these groups, measure the profitability of standard 6-month/6-month momentum strategies, and
  decompose into winner and loser legs.

## Evidence
- Momentum profits **decline with analyst coverage** after controlling for size.
- The coverage effect is driven mainly by the **loser** portfolio (low-coverage losers keep falling),
  consistent with slow diffusion of bad news.

## Why it matters
Provides the cross-sectional fingerprint predicted by behavioural/information-diffusion theories of
momentum, helping distinguish them from purely risk-based explanations, and motivating attention/news
signals in quantitative research.

## Limitations and risks
- Analyst coverage proxies information environment imperfectly and has changed since 2000.
- Like all momentum, the strategy carries crash risk and trading costs.

## Key references
- Hong, H., Lim, T. & Stein, J. (2000) — *Bad News Travels Slowly* — Journal of Finance
- Hong, H. & Stein, J. (1999) — *A Unified Theory of Underreaction, Momentum Trading and Overreaction* — Journal of Finance
- Jegadeesh, N. & Titman, S. (1993) — *Returns to Buying Winners and Selling Losers* — Journal of Finance
"""

WIKIS["11d7a437-c6d4-452b-b908-82ab56c0b2ad"] = """\
# Stock Prices, Earnings, and Expected Dividends

**Source:** Campbell, J. Y. & Shiller, R. J. (1988). *Journal of Finance* 43(3), 661–676.

## TL;DR
Develops the log-linear present-value framework that makes valuation ratios interpretable and
testable, and shows that **dividend-price and (smoothed) earnings-price ratios forecast long-horizon
returns**: when prices are high relative to dividends or earnings, subsequent returns tend to be low.
A cornerstone of the return-predictability literature.

## What it documents
The dynamic Gordon-growth (log-linear) decomposition: the log dividend-price ratio equals the
discounted sum of expected future returns minus expected future dividend growth. Because dividend
growth is hard to forecast, variation in the dividend-price ratio must reflect variation in **expected
returns** — i.e. predictability.

## Methodology
- Log-linearise the present-value identity to relate the dividend-price ratio to future returns and
  dividend growth.
- Run long-horizon predictive regressions of returns on dividend-price and smoothed (10-year)
  earnings-price ratios; use VARs to assess the present-value relations.

## Main findings
- Valuation ratios have little power to forecast dividend growth but substantial power to forecast
  **returns**, especially at multi-year horizons.
- Prices vary far more than warranted by future dividends alone — the excess-volatility theme.

## Implications for factor investing
- Valuation-ratio predictability is a **long-horizon, low-frequency** phenomenon — easy to overstate
  in-sample (see Welch-Goyal) and sensitive to persistent-regressor bias (Stambaugh bias).
- The framework underlies the dividend-yield, CAPE, and book-to-market predictability literatures.

## Key references
- Campbell, J. & Shiller, R. (1988) — *Stock Prices, Earnings, and Expected Dividends* — Journal of Finance
- Campbell, J. & Shiller, R. (1988) — *The Dividend-Price Ratio and Expectations of Future Dividends and Discount Factors* — Review of Financial Studies
- Cochrane, J. (2008) — *The Dog That Did Not Bark: A Defense of Return Predictability* — Review of Financial Studies
"""

WIKIS["56f96fd0-c532-4754-ad2a-cdea391b6664"] = """\
# Measuring and Testing the Impact of News on Volatility

**Source:** Engle, R. F. & Ng, V. K. (1993). *Journal of Finance* 48(5), 1749–1778.

## TL;DR
Introduces the **news impact curve** — the mapping from a return shock to next-period conditional
volatility — as a way to characterise and compare volatility models, and provides diagnostic tests for
asymmetry. Confirms that negative shocks raise volatility more than positive shocks of equal size, and
that asymmetric models (GJR-GARCH, EGARCH) capture this better than symmetric GARCH.

## What it addresses
Different volatility models imply different responses to good vs bad news. Engle and Ng give a common
yardstick (the news impact curve) and formal tests so models can be compared on how they translate
shocks into volatility.

## Method
- **News impact curve:** plot next-period conditional variance as a function of the current shock,
  holding the past constant.
- **Diagnostic tests:** the sign-bias, negative-size-bias, and positive-size-bias tests detect
  misspecified responses to the sign and magnitude of shocks.
- Propose a partially nonparametric (PNP) model to estimate the curve flexibly.

## Evidence
- Japanese (and US) equity data show a pronounced **asymmetry**: bad news increases volatility more.
- Symmetric GARCH fails the bias tests; GJR-GARCH and EGARCH fit the asymmetry well.

## Why it matters
The news impact curve and the bias tests became standard tools for building and validating volatility
models, formalising the leverage effect that GJR-GARCH and EGARCH were designed to capture.

## Limitations and risks
- A daily, parametric framework; it predates high-frequency realized-volatility methods.
- Estimated curves are sensitive to the conditioning information and sample.

## Key references
- Engle, R. & Ng, V. (1993) — *Measuring and Testing the Impact of News on Volatility* — Journal of Finance
- Glosten, L., Jagannathan, R. & Runkle, D. (1993) — *On the Relation between the Expected Value and the Volatility...* — Journal of Finance
- Nelson, D. (1991) — *Conditional Heteroskedasticity in Asset Returns (EGARCH)* — Econometrica
"""

WIKIS["c53a5efa-b126-4d87-aa6e-4bc99e6f954f"] = """\
# Profitability of Momentum Strategies: An Evaluation of Alternative Explanations

**Source:** Jegadeesh, N. & Titman, S. (2001). *Journal of Finance* 56(2), 699–720.

## TL;DR
Revisits momentum nearly a decade after Jegadeesh & Titman (1993), in effect an **out-of-sample test**
on 1990s data. Momentum profits persisted in the new period, ruling out the worry that the original
result was data-snooping. Crucially, momentum portfolio returns **reverse over the following 2–5
years**, which favours behavioural (overreaction / delayed-correction) explanations over risk-based ones.

## What anomaly it documents
The robustness and the longer-run dynamics of cross-sectional momentum: short-horizon continuation
followed by long-horizon reversal — the signature of mispricing that eventually corrects.

## How it is constructed
- Standard momentum: rank on past 6-month returns, hold 6 months, long winners / short losers.
- Examine post-holding-period returns out to five years to look for reversal, and test whether profits
  line up with risk-model exposures or firm characteristics.

## Evidence and replication
| Period / horizon | Result | Source |
|------------------|--------|--------|
| 1990–1998 (post-original-sample) | Momentum remains profitable | this paper |
| Years 2–5 after formation | Returns reverse | this paper |

The persistence out of sample and the subsequent reversal are hard to reconcile with risk
compensation and fit behavioural underreaction-then-overreaction.

## Why it might work
- **Behavioural:** initial underreaction to news, later overreaction that reverses — consistent with
  Barberis-Shleifer-Vishny and Hong-Stein.
- Risk-based stories struggle to explain the long-run reversal.

## Limitations and risks
- Momentum's crash risk and transaction costs remain; the reversal complicates holding periods.
- Out-of-sample here means the 1990s; later decades show further decay and the 2009 crash.

## Key references
- Jegadeesh, N. & Titman, S. (2001) — *Profitability of Momentum Strategies* — Journal of Finance
- Jegadeesh, N. & Titman, S. (1993) — *Returns to Buying Winners and Selling Losers* — Journal of Finance
- Daniel, K. & Moskowitz, T. (2016) — *Momentum Crashes* — Journal of Financial Economics
"""

WIKIS["2f8410ce-4ed9-4d46-ad59-fd94177315fe"] = """\
# Corporate Governance and Equity Prices

**Source:** Gompers, P. A., Ishii, J. L. & Metrick, A. (2003). *Quarterly Journal of Economics*
118(1), 107–156.

## TL;DR
Builds a **Governance Index (the "G-index")** from 24 antitakeover and shareholder-rights provisions
and shows that, during the 1990s, firms with strong shareholder rights (low G, "Democracies")
outperformed firms with weak rights (high G, "Dictatorships") by about **8.5% per year** on a
risk-adjusted basis, while also having higher valuations and better operating performance.

## What anomaly it documents
A governance-based return spread: weaker shareholder rights were associated with lower subsequent
abnormal returns, suggesting the market did not fully price the agency costs of poor governance.

## How it is constructed
- **G-index:** add one point for each of 24 governance provisions that restrict shareholder rights
  (a higher score = weaker rights / more management entrenchment).
- Form a long Democracy (low G) / short Dictatorship (high G) portfolio and measure abnormal returns
  against standard factor models; relate G to Tobin's Q and operating performance.

## Evidence and replication
| Period | Result | Source |
|--------|--------|--------|
| 1990–1999 | Democracy-minus-Dictatorship ≈ 8.5%/yr risk-adjusted | this paper |
| Post-2000 (later work) | The return spread largely disappeared | subsequent literature |

The headline alpha is an in-sample 1990s result; later studies found it weakened or vanished out of
sample — a textbook example of an anomaly that may have been learned and arbitraged away.

## Why it might work
- **Mispricing of agency costs:** investors underappreciated how entrenchment erodes value.
- Alternatively, an omitted risk factor or a 1990s-specific correlation (e.g. with the takeover wave).

## Limitations and risks
- The effect is concentrated in the 1990s and faded afterward; the Bebchuk-Cohen-Ferrell "E-index"
  argued a smaller set of provisions drives results.
- Governance provisions are sticky and endogenous to firm characteristics.

## Key references
- Gompers, P., Ishii, J. & Metrick, A. (2003) — *Corporate Governance and Equity Prices* — Quarterly Journal of Economics
- Bebchuk, L., Cohen, A. & Ferrell, A. (2009) — *What Matters in Corporate Governance? (E-index)* — Review of Financial Studies
- Cremers, M. & Nair, V. (2005) — *Governance Mechanisms and Equity Prices* — Journal of Finance
"""

WIKIS["1e6ab210-a72a-4ec0-8433-cfa3351e0ef7"] = """\
# The Price of Sin: The Effects of Social Norms on Markets

**Source:** Hong, H. & Kacperczyk, M. (2009). *Journal of Financial Economics* 93(1), 15–36.

## TL;DR
"Sin stocks" — publicly traded producers of alcohol, tobacco, and gaming — are shunned by
norm-constrained institutional investors, are under-covered by analysts, and consequently trade at
lower valuations and earn **higher expected returns** than comparable stocks. Social norms have a
measurable price: ethical exclusion leaves a premium on the table for investors willing to hold them.

## What anomaly it documents
A neglect/limited-arbitrage premium driven by norms: because many large institutions (pensions,
universities) avoid sin stocks, demand is depressed, prices are lower, and expected returns are higher.

## How it is measured
- Identify sin-industry stocks (alcohol, tobacco, gaming).
- Compare their institutional ownership, analyst coverage, valuation multiples, and risk-adjusted
  returns against matched comparison firms using standard factor models.

## Evidence
- Sin stocks have **lower institutional ownership and analyst coverage** and earn a positive
  risk-adjusted return (a "sin premium") relative to comparables.
- The effect is stronger where norm pressure is greater (e.g. more litigation-risk, more
  norm-constrained owners).

## Why it matters
A central reference for responsible/ESG investing: it quantifies the return cost of exclusionary
screening and frames the trade-off between values-based constraints and expected performance — directly
relevant to the ethics and constraints discussion in modern portfolio construction.

## Limitations and risks
- The premium may be compensation for litigation/headline risk rather than pure neglect.
- ESG flows and definitions have shifted substantially since 2009, plausibly changing the premium.

## Key references
- Hong, H. & Kacperczyk, M. (2009) — *The Price of Sin* — Journal of Financial Economics
- Merton, R. (1987) — *A Simple Model of Capital Market Equilibrium with Incomplete Information* — Journal of Finance
- Pástor, Ľ., Stambaugh, R. & Taylor, L. (2021) — *Sustainable Investing in Equilibrium* — Journal of Financial Economics
"""

WIKIS["584b68a4-ca41-435d-ab99-1de3a3351920"] = """\
# The Long-Run Performance of Initial Public Offerings

**Source:** Ritter, J. R. (1991). *Journal of Finance* 46(1), 3–27.

## TL;DR
Documents that IPOs **underperform** comparable seasoned firms over the three years following the
offering — roughly 17% lower returns than matched firms in the sample. Combined with well-known
first-day underpricing, this "new-issues puzzle" suggests firms time their offerings to windows of
investor over-optimism.

## What anomaly it documents
Long-run IPO underperformance: buying IPOs and holding for three years would have substantially
lagged matched non-issuers, a cross-sectional anomaly in the new-issues market.

## How it is measured
- Sample IPOs over 1975–1984 and track three-year buy-and-hold returns.
- Benchmark against firms matched on size and industry; examine variation by issue year and firm
  characteristics (younger, smaller, high-volume-year issuers fare worst).

## Evidence
- Three-year returns on IPOs are well below matched firms; underperformance is concentrated among
  young growth firms and in high-issuance ("hot") years.
- Consistent with **windows of opportunity** — issuers go public when sentiment and valuations are high.

## Why it matters
A foundational behavioural-corporate-finance result linking issuance to sentiment and mispricing, and
a caution that the same firms exhibiting first-day "underpricing" disappoint over the long run.

## Limitations and risks
- Long-run abnormal-return measurement is sensitive to the benchmark and to bad-model problems
  (Fama, 1998); results attenuate under some methods.
- Sample-period and survivorship considerations affect magnitudes.

## Key references
- Ritter, J. (1991) — *The Long-Run Performance of Initial Public Offerings* — Journal of Finance
- Loughran, T. & Ritter, J. (1995) — *The New Issues Puzzle* — Journal of Finance
- Fama, E. (1998) — *Market Efficiency, Long-Term Returns, and Behavioral Finance* — Journal of Financial Economics
"""

WIKIS["af5ed095-7995-4510-bab9-3dbe95f54292"] = """\
# Valuing American Options by Simulation: A Simple Least-Squares Approach

**Source:** Longstaff, F. A. & Schwartz, E. S. (2001). *Review of Financial Studies* 14(1), 113–147.

## TL;DR
Introduces **Least-Squares Monte Carlo (LSM)**, a simple, general way to price American and Bermudan
options by simulation. At each potential exercise date it estimates the *continuation value* by
regressing discounted future payoffs on functions of the current state, then exercises whenever the
immediate payoff exceeds that estimate. LSM made early-exercise and high-dimensional options tractable
by simulation.

## What it solves
Standard Monte Carlo prices European (no early-exercise) options easily but struggles with American
options, where the holder may exercise at any time — a dynamic-programming problem traditionally solved
on lattices/PDEs that scale poorly in many dimensions.

## The method
- Simulate many paths of the underlying state.
- Working backward from maturity, at each exercise date regress realised discounted continuation
  payoffs on basis functions (e.g. polynomials) of the state to estimate the continuation value.
- Exercise on a path when the immediate payoff exceeds the estimated continuation value; otherwise hold.
- Average the resulting cash flows to price the option.

## Why it matters
LSM is the workhorse for pricing American-style and path-dependent derivatives, multi-asset options,
and real options — anywhere early exercise meets high dimensionality and lattices break down. It is
widely implemented in practice and in risk systems.

## Limitations and risks
- The price depends on the **choice of basis functions**; too few biases low, too many overfits.
- Regression on in-sample paths can bias the estimated exercise boundary (low-biased estimator);
  variants and dual/upper-bound methods address this.
- Computationally heavy for many exercise dates and high accuracy.

## Key references
- Longstaff, F. & Schwartz, E. (2001) — *Valuing American Options by Simulation* — Review of Financial Studies
- Tsitsiklis, J. & Van Roy, B. (2001) — *Regression Methods for Pricing Complex American-Style Options* — IEEE Trans. Neural Networks
- Boyle, P. (1977) — *Options: A Monte Carlo Approach* — Journal of Financial Economics
"""

WIKIS["11178ba0-cc74-4943-8879-f40b617bdaa6"] = """\
# Earnings, Book Values, and Dividends in Equity Valuation

**Source:** Ohlson, J. A. (1995). *Contemporary Accounting Research* 11(2), 661–687.

## TL;DR
Provides the **residual-income (Ohlson) valuation model**: a firm's market value equals its book value
plus the present value of expected future *abnormal* (residual) earnings — earnings above a normal
charge on book equity. It ties accounting numbers directly to value through the clean-surplus relation
and clarifies the roles of earnings, book value, and dividends.

## What it documents (models)
A rigorous accounting-based valuation framework. Under clean surplus (the change in book value equals
earnings minus dividends), discounting future dividends is equivalent to book value plus discounted
residual income, making accounting fundamentals the inputs to value.

## The model
- **Value = book value + PV(expected residual income)**, where residual income = earnings − r × (prior
  book value).
- A linear information dynamics assumption links current abnormal earnings (and "other information") to
  future abnormal earnings, yielding closed-form value as a function of book value, current earnings,
  and other information.
- **Dividends** reduce book value one-for-one but do not affect current earnings — dividend
  displacement, consistent with Miller-Modigliani irrelevance within the model.

## Why it matters
The theoretical backbone for fundamentals-based valuation and for empirical accounting research linking
prices to earnings and book values; it underpins residual-income models used by analysts and the value
literature's use of book-to-market.

## Limitations and risks
- Relies on **clean surplus**, which real accounting violates (dirty-surplus items).
- The linear information dynamics are an assumption; estimates of "other information" are difficult.
- Sensitive to the cost-of-capital and persistence parameters.

## Key references
- Ohlson, J. (1995) — *Earnings, Book Values, and Dividends in Equity Valuation* — Contemporary Accounting Research
- Feltham, G. & Ohlson, J. (1995) — *Valuation and Clean Surplus Accounting for Operating and Financial Activities* — Contemporary Accounting Research
- Frankel, R. & Lee, C. (1998) — *Accounting Valuation, Market Expectation, and Cross-Sectional Stock Returns* — Journal of Accounting and Economics
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
