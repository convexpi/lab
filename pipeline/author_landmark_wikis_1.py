"""
author_landmark_wikis_1.py — wikis for the foundational asset-pricing & factor landmarks.

Keyed by DOI (the landmark rows were seeded by seed_landmark_papers.py). Covers CAPM (Sharpe,
Lintner), APT (Ross), Markowitz portfolio selection, the efficient-markets hypothesis (Fama),
Merton's ICAPM, the Fama-French 1993/1996/2015 factor models, Carhart, Hou-Xue-Zhang q-factors,
Jensen's alpha, and Grinold's fundamental law of active management. Public, paper-focused.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_landmark_wikis_1.py --dry-run
    ...                                          python pipeline/author_landmark_wikis_1.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.parse, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["10.2307/2977928"] = """\
# Capital Asset Prices: A Theory of Market Equilibrium under Conditions of Risk

**Source:** Sharpe, W. F. (1964). *Journal of Finance* 19(3), 425–442.

## TL;DR
Derives the **Capital Asset Pricing Model (CAPM)**: in equilibrium, the expected return on any asset
is the risk-free rate plus its **beta** (its covariance with the market, scaled by market variance)
times the market risk premium. Only **systematic** (non-diversifiable) risk is priced; idiosyncratic
risk earns nothing. It is the foundation of modern asset pricing and of the very idea of risk-adjusted
return.

## What it documents (models)
Building on Markowitz's mean-variance investors, Sharpe shows that when everyone holds mean-variance-
efficient portfolios, all hold the same risky **market portfolio** levered up or down with the
risk-free asset (the separation theorem). Equilibrium then forces the linear risk-return relation.

## The model
E[Rᵢ] = R_f + βᵢ (E[R_m] − R_f), with βᵢ = Cov(Rᵢ, R_m) / Var(R_m). The **security market line**
plots expected return against beta; assets off the line are mispriced.

## Why it matters
- Defines **beta**, the market risk premium, and alpha (return beyond CAPM) — the vocabulary of the
  whole field.
- The benchmark every factor model (Fama-French and beyond) is measured against.
- Underlies index investing, the cost of equity, and performance evaluation.

## Limitations and risks
- Empirically the security market line is **too flat**: low-beta stocks earn more, high-beta less than
  CAPM predicts (the basis for betting-against-beta).
- Size, value, momentum, and other anomalies are CAPM "alphas" the model cannot explain.
- Strong assumptions (single period, homogeneous beliefs, frictionless markets, mean-variance utility).

## Key references
- Sharpe, W. (1964) — *Capital Asset Prices* — Journal of Finance
- Lintner, J. (1965) — *The Valuation of Risk Assets...* — Review of Economics and Statistics
- Fama, E. & French, K. (1992) — *The Cross-Section of Expected Stock Returns* — Journal of Finance
- Black, F., Jensen, M. & Scholes, M. (1972) — *The Capital Asset Pricing Model: Some Empirical Tests*
"""

WIKIS["10.2307/1924119"] = """\
# The Valuation of Risk Assets and the Selection of Risky Investments in Stock Portfolios and Capital Budgets

**Source:** Lintner, J. (1965). *Review of Economics and Statistics* 47(1), 13–37.

## TL;DR
Derives the **Capital Asset Pricing Model** independently of Sharpe, and works out the corporate-finance
implications: how firms should evaluate risky investments (capital budgeting) when investors price risk
through diversification. Together with Sharpe (1964) and Mossin (1966), it establishes the CAPM as the
equilibrium theory of risk and return.

## What it documents (models)
Mean-variance investors combining risky assets with risk-free borrowing/lending hold the market
portfolio; in equilibrium expected returns are linear in beta. Lintner emphasizes the **valuation** and
**investment-decision** side: the required return on a project depends on its contribution to portfolio
risk, not its standalone variance.

## The model
The same security-market-line relation as Sharpe, E[Rᵢ] = R_f + βᵢ(E[R_m] − R_f), reached via a
detailed treatment of investor optimization and of how risky cash flows should be discounted.

## Why it matters
- Co-founds the CAPM, giving the cost-of-capital rule used in corporate finance and capital budgeting.
- Lintner's careful aggregation and valuation arguments complement Sharpe's portfolio derivation.
- His later work on dividends ("Lintner model") is itself a classic.

## Limitations and risks
- Shares CAPM's empirical failings (flat SML, anomalies) and strong assumptions.
- The single-period, mean-variance framing abstracts from multi-period and higher-moment concerns.

## Key references
- Lintner, J. (1965) — *The Valuation of Risk Assets...* — Review of Economics and Statistics
- Sharpe, W. (1964) — *Capital Asset Prices* — Journal of Finance
- Mossin, J. (1966) — *Equilibrium in a Capital Asset Market* — Econometrica
"""

WIKIS["10.1016/0022-0531(76)90046-6"] = """\
# The Arbitrage Theory of Capital Asset Pricing

**Source:** Ross, S. A. (1976). *Journal of Economic Theory* 13(3), 341–360.

## TL;DR
Introduces **Arbitrage Pricing Theory (APT)**: if returns are driven by a few common **factors**, then
**no-arbitrage** alone implies expected returns are linear in the assets' factor loadings — without
needing the market portfolio, mean-variance preferences, or the strong assumptions of the CAPM. APT is
the theoretical license for **multi-factor** models.

## What it documents (models)
Assume Rᵢ = E[Rᵢ] + βᵢ₁f₁ + … + βᵢₖfₖ + εᵢ with diversifiable idiosyncratic ε. A well-diversified
portfolio with zero net investment and zero factor exposure must, by no-arbitrage, earn zero — which
forces E[Rᵢ] ≈ R_f + Σ βᵢⱼ λⱼ, where λⱼ are factor risk premia.

## The model
Expected return = risk-free rate + a linear combination of factor betas times factor premia. The
identity of the factors is left **unspecified** — they can be macroeconomic (Chen-Roll-Ross) or
statistical/characteristic-based.

## Why it matters
- The foundation for **all multi-factor pricing** (Fama-French, q-factor, and the "factor zoo").
- Replaces CAPM's restrictive equilibrium assumptions with a far weaker, more general no-arbitrage
  argument.
- Frames performance/risk as exposures to priced factors.

## Limitations and risks
- APT does not say **what** the factors are or how many — leaving the door open to data-mined factors.
- "Approximate" no-arbitrage holds only for well-diversified portfolios; small-sample factor
  identification is fragile.

## Key references
- Ross, S. (1976) — *The Arbitrage Theory of Capital Asset Pricing* — Journal of Economic Theory
- Chen, N.-F., Roll, R. & Ross, S. (1986) — *Economic Forces and the Stock Market* — Journal of Business
- Fama, E. & French, K. (1993) — *Common Risk Factors in the Returns on Stocks and Bonds* — Journal of Financial Economics
"""

WIKIS["10.2307/2975974"] = """\
# Portfolio Selection

**Source:** Markowitz, H. (1952). *Journal of Finance* 7(1), 77–91.

## TL;DR
Founds **modern portfolio theory**. Markowitz reframes investing as a trade-off between **expected
return and variance**, shows that what matters for a portfolio is not each asset's risk in isolation but
its **covariance** with the rest, and derives the **efficient frontier** — the set of portfolios with
the highest expected return for each level of variance. Diversification is given a rigorous foundation.

## What it documents (models)
Investors should not simply maximize expected return (that puts everything in one asset); they should
balance return against risk. Because portfolio variance depends on covariances, combining imperfectly
correlated assets reduces risk for a given return.

## The framework
- Portfolio return = weighted mean of asset returns; portfolio variance = wᵀΣw (Σ = covariance matrix).
- The **efficient frontier** is traced by minimizing variance subject to a target return; rational
  mean-variance investors hold a frontier portfolio.

## Why it matters
- The conceptual and mathematical basis for the CAPM, risk budgeting, and essentially all quantitative
  portfolio construction.
- Establishes covariance/diversification as the heart of risk management.

## Limitations and risks
- Mean-variance optimization is **extremely sensitive to estimation error** in expected returns and
  covariances (DeMiguel et al. show naive 1/N often beats it out of sample).
- Variance penalizes upside symmetrically and ignores fat tails; inputs are hard to estimate.

## Key references
- Markowitz, H. (1952) — *Portfolio Selection* — Journal of Finance
- Sharpe, W. (1964) — *Capital Asset Prices* — Journal of Finance
- DeMiguel, V., Garlappi, L. & Uppal, R. (2009) — *Optimal Versus Naive Diversification* — Review of Financial Studies
"""

WIKIS["10.2307/2325486"] = """\
# Efficient Capital Markets: A Review of Theory and Empirical Work

**Source:** Fama, E. F. (1970). *Journal of Finance* 25(2), 383–417.

## TL;DR
The defining statement of the **efficient market hypothesis (EMH)**: prices "fully reflect" available
information, so consistently beating the market on a risk-adjusted basis is impossible. Fama organizes
efficiency into three nested forms — **weak** (past prices), **semi-strong** (all public information),
and **strong** (all information, including private) — and surveys the evidence.

## What it documents
A framework and a literature review that set the agenda for decades of empirical finance: a market is
efficient with respect to an information set if prices already incorporate it, so trading on that
information cannot earn abnormal returns.

## The three forms
- **Weak form:** prices reflect past prices → technical analysis cannot beat the market.
- **Semi-strong form:** prices reflect all public information → fundamental analysis of public data
  cannot beat the market; event studies test this.
- **Strong form:** prices reflect even private information → not even insiders can profit (empirically rejected).

## Why it matters
- The intellectual benchmark against which every anomaly and trading strategy is judged.
- Introduces the **joint-hypothesis problem**: any test of efficiency is simultaneously a test of an
  asset-pricing model, so "the market is inefficient" can never be cleanly separated from "the model is
  wrong" — central to honest evaluation.

## Limitations and risks
- The joint-hypothesis problem makes EMH effectively untestable in isolation.
- Behavioral finance and the documented anomalies (momentum, value, PEAD) challenge semi-strong
  efficiency; Fama (1991, 1998) revisits the debate.

## Key references
- Fama, E. (1970) — *Efficient Capital Markets: A Review of Theory and Empirical Work* — Journal of Finance
- Fama, E. (1991) — *Efficient Capital Markets: II* — Journal of Finance
- Grossman, S. & Stiglitz, J. (1980) — *On the Impossibility of Informationally Efficient Markets* — American Economic Review
"""

WIKIS["10.2307/1913811"] = """\
# An Intertemporal Capital Asset Pricing Model

**Source:** Merton, R. C. (1973). *Econometrica* 41(5), 867–887.

## TL;DR
Generalizes the CAPM to a **dynamic, multi-period** world. When investment opportunities change over
time, investors care not only about market risk but also about assets that **hedge adverse shifts** in
those opportunities. The result — the **Intertemporal CAPM (ICAPM)** — is a multi-factor model in which
**state variables** that forecast future returns/volatility are additional priced risks.

## What it documents (models)
In continuous time, investors maximizing lifetime utility hold the market portfolio **plus** hedging
portfolios that protect against changes in the investment opportunity set (e.g., shifts in interest
rates or expected returns). Those hedging demands generate extra risk premia.

## The model
E[Rᵢ] − R_f is linear in the asset's market beta **and** its betas with respect to the state variables
that describe time-varying opportunities — a theoretically grounded multi-factor pricing equation.

## Why it matters
- Provides the **theoretical justification** for multi-factor models distinct from APT: factors should
  be state variables that forecast the future investment opportunity set.
- Underlies interpretations of value, term, and volatility factors as hedges against bad states.
- A pillar of continuous-time finance (alongside Merton's option and credit work).

## Limitations and risks
- The theory does not pin down **which** state variables matter — leaving empirical discretion.
- Continuous-trading, known-dynamics assumptions are idealizations.

## Key references
- Merton, R. (1973) — *An Intertemporal Capital Asset Pricing Model* — Econometrica
- Campbell, J. (1996) — *Understanding Risk and Return* — Journal of Political Economy
- Fama, E. & French, K. (1993) — *Common Risk Factors in the Returns on Stocks and Bonds* — Journal of Financial Economics
"""

WIKIS["10.1016/0304-405x(93)90023-5"] = """\
# Common Risk Factors in the Returns on Stocks and Bonds

**Source:** Fama, E. F. & French, K. R. (1993). *Journal of Financial Economics* 33(1), 3–56.

## TL;DR
The paper that operationalized the **three-factor model**. It introduces the tradable **SMB** (small
minus big) and **HML** (high minus low book-to-market) factors alongside the market, and shows that
together they explain most of the common variation in diversified stock returns — capturing the size
and value premia that the CAPM cannot. These factors became the workhorse benchmark of empirical finance.

## What it documents
Building the actual long-short factor portfolios (from 2×3 sorts on size and book-to-market) and
demonstrating, via time-series regressions, that market + SMB + HML price a wide cross-section of
stock (and, in part, bond) portfolios.

## How it is constructed
- **SMB:** average return of small-cap portfolios minus large-cap portfolios.
- **HML:** average return of high-book-to-market (value) minus low-book-to-market (growth) portfolios.
- Both from independent 2×3 size / book-to-market sorts of NYSE/AMEX/NASDAQ stocks, rebalanced annually.

## Evidence
- Market, SMB, and HML jointly produce high R² and small intercepts (alphas) across 25 size-BM
  portfolios — the size and value effects are systematic, factor-like risks.

## Why it matters
- Defines **HML and SMB**, the factors used (and extended) by virtually all subsequent cross-sectional
  research; the executable value and size strategies on this platform are built from these series.
- The empirical foundation for factor investing and for measuring "alpha" beyond size and value.

## Limitations and risks
- Whether size/value are **risk** premia or **mispricing** is unresolved; the size effect later weakened.
- The model misses momentum (added by Carhart) and profitability/investment (added in FF5).

## Key references
- Fama, E. & French, K. (1993) — *Common Risk Factors in the Returns on Stocks and Bonds* — Journal of Financial Economics
- Fama, E. & French, K. (1992) — *The Cross-Section of Expected Stock Returns* — Journal of Finance
- Carhart, M. (1997) — *On Persistence in Mutual Fund Performance* — Journal of Finance
"""

WIKIS["10.1111/j.1540-6261.1996.tb05202.x"] = """\
# Multifactor Explanations of Asset Pricing Anomalies

**Source:** Fama, E. F. & French, K. R. (1996). *Journal of Finance* 51(1), 55–84.

## TL;DR
Shows that the **three-factor model** (market, SMB, HML) explains most of the well-known CAPM
anomalies — the returns to long-term reversal, and sorts on earnings/price, cash-flow/price, and sales
growth all line up with loadings on size and value. The glaring exception is **momentum**, which the
three-factor model cannot explain and which remains an open anomaly.

## What it documents
That many seemingly separate "anomalies" are manifestations of the same underlying value/size factor
exposures — they are absorbed once you control for HML and SMB — strengthening the case for the
three-factor model as a description of average returns.

## Methodology
Run time-series three-factor regressions on portfolios formed from the various anomaly variables; if
the intercepts (alphas) are near zero, the factors explain the anomaly.

## Main findings
- Long-term reversal, E/P, C/P, and sales-growth sorts are **explained** by the three factors.
- **Momentum is not** — short-term continuation produces large alphas, a problem the authors flag
  explicitly (later addressed by Carhart's fourth factor).
- The authors discuss risk-based vs behavioral interpretations of the surviving value premium.

## Implications for factor investing
- Control for size and value before claiming a new anomaly — many vanish.
- Momentum is a genuinely distinct factor, motivating four-factor (and richer) models.

## Key references
- Fama, E. & French, K. (1996) — *Multifactor Explanations of Asset Pricing Anomalies* — Journal of Finance
- Fama, E. & French, K. (1993) — *Common Risk Factors...* — Journal of Financial Economics
- Carhart, M. (1997) — *On Persistence in Mutual Fund Performance* — Journal of Finance
"""

WIKIS["10.1016/j.jfineco.2014.10.010"] = """\
# A Five-Factor Asset Pricing Model

**Source:** Fama, E. F. & French, K. R. (2015). *Journal of Financial Economics* 116(1), 1–22.

## TL;DR
Extends the three-factor model with two factors motivated by the dividend-discount/q-theory logic:
**RMW** (robust minus weak **profitability**) and **CMA** (conservative minus aggressive **investment**).
The resulting **five-factor model** (market, SMB, HML, RMW, CMA) explains average returns better than
the three-factor model — and, strikingly, **HML becomes largely redundant** once profitability and
investment are included.

## What it documents
That profitability and investment carry independent premia predicted by valuation theory: holding
book-to-market fixed, more profitable firms and firms that invest less earn higher average returns.

## How it is constructed
- **RMW:** high-operating-profitability minus low-profitability portfolios.
- **CMA:** low-investment (conservative) minus high-investment (aggressive) portfolios.
- Built from size sorts interacted with profitability and investment, alongside the original SMB/HML.

## Evidence
- The five factors price most portfolios better than three; the biggest improvement is for
  profitability and investment sorts.
- **HML is redundant** in the presence of RMW and CMA in U.S. data — value is partly a combination of
  profitability and investment exposure.
- The model still struggles with small, low-profitability firms that invest aggressively.

## Why it matters
- The current Fama-French benchmark, and the bridge to investment-based ("q-factor") models.
- Reframes value as connected to profitability and investment fundamentals.

## Limitations and risks
- Does **not** include momentum (still needed separately).
- Factor redundancy (HML) and the model's microcap failures are ongoing debates; q-factors (Hou-Xue-
  Zhang) are a competing specification.

## Key references
- Fama, E. & French, K. (2015) — *A Five-Factor Asset Pricing Model* — Journal of Financial Economics
- Hou, K., Xue, C. & Zhang, L. (2015) — *Digesting Anomalies: An Investment Approach* — Review of Financial Studies
- Novy-Marx, R. (2013) — *The Other Side of Value: The Gross Profitability Premium* — Journal of Financial Economics
"""

WIKIS["10.1111/j.1540-6261.1997.tb03808.x"] = """\
# On Persistence in Mutual Fund Performance

**Source:** Carhart, M. M. (1997). *Journal of Finance* 52(1), 57–82.

## TL;DR
Introduces the **four-factor model** — Fama-French three factors plus a **momentum** factor (UMD/WML) —
and uses it to show that apparent **persistence in mutual-fund performance is mostly explained by
momentum and costs**, not skill. Funds that hold last year's winners look good until you adjust for the
momentum factor; persistent *under*performance, by contrast, is real and driven by expenses.

## What it documents
That the "hot hands" in fund returns largely reflect **mechanical exposure to momentum** (funds
accidentally holding winners) and expense differences — once you control for the four factors, little
genuine stock-picking skill remains.

## How it is constructed
- Add a **momentum factor** (UMD = up-minus-down, the return of past winners minus losers) to market,
  SMB, and HML.
- Regress fund returns on the four factors; attribute persistence to factor loadings, expenses, and
  turnover rather than to alpha.

## Evidence
- Short-term performance persistence is **subsumed** by the momentum factor and cost differences.
- The worst-performing funds persistently underperform, largely due to high expenses.
- Net-of-cost, the average fund does not beat its four-factor benchmark.

## Why it matters
- Defines the **fourth (momentum) factor** used throughout performance evaluation.
- A landmark in the active-vs-passive debate: most fund "skill" is factor exposure and luck, not alpha.

## Limitations and risks
- Attribution depends on the factor model; momentum itself is unexplained by risk theory.
- Survivorship and look-ahead in fund data must be handled carefully.

## Key references
- Carhart, M. (1997) — *On Persistence in Mutual Fund Performance* — Journal of Finance
- Jegadeesh, N. & Titman, S. (1993) — *Returns to Buying Winners and Selling Losers* — Journal of Finance
- Fama, E. & French, K. (2010) — *Luck versus Skill in the Cross-Section of Mutual Fund Returns* — Journal of Finance
"""

WIKIS["10.1093/rfs/hhu068"] = """\
# Digesting Anomalies: An Investment Approach

**Source:** Hou, K., Xue, C. & Zhang, L. (2015). *Review of Financial Studies* 28(3), 650–705.

## TL;DR
Proposes the **q-factor model** — market, size, **investment (I/A)**, and **profitability (ROE)** —
grounded in investment-based (q-theory) asset pricing. This four-factor model explains a large set of
anomalies (and many better than the Fama-French models), arguing that much of the cross-section reduces
to firms' investment and profitability.

## What it documents
That a parsimonious, theory-motivated set of factors derived from the firm's investment first-order
conditions captures the bulk of documented anomalies — momentum, value, profitability, investment,
distress, and more.

## How it is constructed
- **Investment factor (I/A):** low-investment minus high-investment firms.
- **Profitability factor (ROE):** high-ROE minus low-ROE firms.
- Combined with market and size, from a triple sort, motivated by q-theory: firms invest more when the
  cost of capital (expected return) is low, and high expected profitability implies high discount rates.

## Evidence
- The q-factors **subsume or shrink** the alphas of a wide range of anomalies in head-to-head tests.
- Competes directly with the Fama-French five-factor model; the two share the investment and
  profitability ideas but differ in construction and which anomalies they best explain.

## Why it matters
- A leading modern factor model and a key reference in the "how many factors?" debate.
- Frames the cross-section through real corporate investment decisions rather than risk factors per se.

## Limitations and risks
- Factor construction choices drive which model "wins"; the FF5-vs-q debate is unresolved.
- Like all factor models, vulnerable to the multiple-testing / replication critiques.

## Key references
- Hou, K., Xue, C. & Zhang, L. (2015) — *Digesting Anomalies: An Investment Approach* — Review of Financial Studies
- Fama, E. & French, K. (2015) — *A Five-Factor Asset Pricing Model* — Journal of Financial Economics
- Hou, K., Xue, C. & Zhang, L. (2020) — *Replicating Anomalies* — Review of Financial Studies
"""

WIKIS["10.2307/2325404"] = """\
# The Performance of Mutual Funds in the Period 1945–1964

**Source:** Jensen, M. C. (1968). *Journal of Finance* 23(2), 389–416.

## TL;DR
Introduces **Jensen's alpha** — the intercept from regressing a fund's excess returns on the market's
excess return (the CAPM). Applying it to 115 mutual funds, Jensen finds that on average funds **do not
outperform** a passive market benchmark net of fees, and show little ability to beat it even gross of
fees. The first rigorous, risk-adjusted verdict on active management.

## What it documents
A clean, model-based measure of skill: alpha is the return a manager earns **beyond** what their market
exposure (beta) would predict. Positive alpha = genuine outperformance; the average fund's alpha is
negative after costs.

## How it is measured
- Regress fund excess return on market excess return: Rₚ − R_f = α + β(R_m − R_f) + ε.
- The estimated **α** is the risk-adjusted performance; test whether it is reliably positive.

## Evidence
- The average fund alpha is **negative net of expenses** and roughly zero gross of expenses.
- Very few funds show statistically significant positive alpha — consistent with efficient markets.

## Why it matters
- Defines **alpha**, the central measure of active performance, used everywhere from fund evaluation to
  factor research (where alpha means return unexplained by the factor model).
- Early, influential evidence for indexing and against the average active manager.

## Limitations and risks
- Single-factor (CAPM) alpha conflates true skill with exposure to omitted factors (size, value,
  momentum) — later corrected by multi-factor alphas (Carhart).
- Survivorship bias in fund samples inflates measured performance.

## Key references
- Jensen, M. (1968) — *The Performance of Mutual Funds in the Period 1945-1964* — Journal of Finance
- Carhart, M. (1997) — *On Persistence in Mutual Fund Performance* — Journal of Finance
- Fama, E. & French, K. (2010) — *Luck versus Skill in the Cross-Section of Mutual Fund Returns* — Journal of Finance
"""

WIKIS["10.3905/jpm.1989.409211"] = """\
# The Fundamental Law of Active Management

**Source:** Grinold, R. C. (1989). *Journal of Portfolio Management* 15(3), 30–37.

## TL;DR
States the **fundamental law of active management**: a manager's information ratio (risk-adjusted active
return) is approximately the **skill per bet (information coefficient, IC)** times the **square root of
the number of independent bets (breadth, N)**: IR ≈ IC · √N. Small edges, applied widely and
independently, beat large edges applied narrowly.

## What it documents (models)
A decomposition of investment value-add into **skill** and **breadth**, formalizing why diversification
across many independent forecasts is as important as forecast quality.

## The law
- **IC:** the cross-sectional correlation between forecasts and realized returns — how good the signal is.
- **Breadth (N):** the number of independent bets per period.
- **IR ≈ IC · √N**, with a transfer-coefficient adjustment for real-world constraints (Clarke, de Silva
  & Thorley) that captures how much of the theoretical IR survives long-only/turnover limits.

## Why it matters
- The intellectual basis for **systematic, breadth-driven** quantitative investing: a tiny IC (e.g.,
  0.05) becomes a respectable IR when applied across thousands of stocks and rebalances.
- Explains why broad cross-sectional strategies (momentum, value across the universe) can work despite
  weak per-name predictability — directly relevant to the low signal-to-noise of return forecasting.

## Limitations and risks
- Assumes bets are **independent**; correlated signals shrink effective breadth dramatically.
- Real constraints (long-only, costs, capacity) reduce the realized IR via the transfer coefficient;
  the law is an idealized upper bound.

## Key references
- Grinold, R. (1989) — *The Fundamental Law of Active Management* — Journal of Portfolio Management
- Grinold, R. & Kahn, R. (2000) — *Active Portfolio Management* — McGraw-Hill
- Clarke, R., de Silva, H. & Thorley, S. (2002) — *Portfolio Constraints and the Fundamental Law of Active Management* — Financial Analysts Journal
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
