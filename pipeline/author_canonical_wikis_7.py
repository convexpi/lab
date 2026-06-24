"""
author_canonical_wikis_7.py — seventh batch of hand-authored wikis for canonical papers.

Covers uncertainty (Baker-Bloom-Davis EPU, Bloom uncertainty shocks), the economic foundation of the
size/value factors (Fama-French 1995), realized volatility of individual stocks (Andersen-Bollerslev-
Diebold-Ebens), macro-finance / systemic amplification (Brunnermeier-Sannikov), fund-performance
decomposition (Wermers), limited attention (Hirshleifer-Teoh), emerging-market integration
(Bekaert-Harvey), financial-constraints risk (Whited-Wu), accruals-quality pricing (Francis et al.),
and market timing (Baker-Wurgler). Public, paper-focused content only.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_canonical_wikis_7.py --dry-run
    ...                                          python pipeline/author_canonical_wikis_7.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["2f6fa9b0-e543-456e-a669-9cb28e6a6558"] = """\
# Measuring Economic Policy Uncertainty

**Source:** Baker, S. R., Bloom, N. & Davis, S. J. (2016). *Quarterly Journal of Economics* 131(4),
1593–1636.

## TL;DR
Builds the **Economic Policy Uncertainty (EPU) index** — a text-based measure of how uncertain the
economic-policy environment is — and shows it spikes around elections, wars, and crises, and that
high policy uncertainty foreshadows lower investment and employment and higher stock-market
volatility. A landmark in turning newspaper text into a widely used macro-finance indicator.

## What it documents (constructs)
A reproducible, real-time index of policy uncertainty assembled from multiple signals, validated
against human readings and economic outcomes.

## How it is measured
- **News component:** the frequency of newspaper articles containing terms about the economy,
  policy, *and* uncertainty (across ~10 major US papers).
- **Tax component:** the dollar value of federal tax-code provisions set to expire.
- **Forecaster disagreement:** dispersion in CPI and government-spending forecasts.
- Combined and normalized into monthly (and daily) EPU indices, now produced for many countries.

## Evidence
- EPU rises sharply around the debt-ceiling standoffs, the 2008 crisis, Brexit, etc.
- Firm- and macro-level: higher EPU is associated with **reduced investment and hiring** (especially
  in policy-sensitive sectors) and **higher stock-price volatility**.

## Why it matters
A foundational "text as data" macro-finance measure used in thousands of studies and in practice as a
risk overlay; it complements the option-implied (VIX) and policy-risk literatures (Pástor-Veronesi).

## Limitations and risks
- The news measure depends on the term lists and newspaper set; media coverage ≠ true uncertainty.
- EPU is correlated with volatility and recessions, so isolating a causal policy-uncertainty channel
  is hard.

## Key references
- Baker, S., Bloom, N. & Davis, S. (2016) — *Measuring Economic Policy Uncertainty* — Quarterly Journal of Economics
- Bloom, N. (2009) — *The Impact of Uncertainty Shocks* — Econometrica
- Pástor, Ľ. & Veronesi, P. (2012) — *Uncertainty about Government Policy and Stock Prices* — Journal of Finance
"""

WIKIS["23541c08-2b92-4723-a506-32ebedcf0a46"] = """\
# The Impact of Uncertainty Shocks

**Source:** Bloom, N. (2009). *Econometrica* 77(3), 623–685.

## TL;DR
Shows that spikes in uncertainty — measured by jumps in stock-market volatility (the VIX) around
events like 9/11, wars, and crises — cause sharp, short **drops and rebounds in investment, hiring,
and output**. Faced with more uncertainty, firms adopt a "wait-and-see" posture (real-options
effect), pausing investment and hiring until the fog clears.

## What it documents (models)
A structural link from financial-market uncertainty to real economic activity, combining a model with
non-convex adjustment costs and empirical evidence from volatility shocks.

## Mechanism
- **Real options:** when uncertainty is high, the option value of waiting rises, so firms freeze
  irreversible investment and hiring.
- After the shock passes, pent-up demand drives a **rebound and overshoot** in activity.
- Higher-order: uncertainty also reduces the effectiveness of policy (firms are less responsive).

## Evidence
- Identify uncertainty shocks as large VIX spikes; a vector-autoregression shows output and
  employment **fall ~1% then recover** within ~6 months — a distinctive drop-rebound pattern.
- A calibrated heterogeneous-firm model reproduces the dynamics.

## Why it matters
The foundational paper linking measured volatility/uncertainty to macro fluctuations; it motivated the
EPU index, the macro-uncertainty literature, and the use of the VIX as a real-economy signal.

## Limitations and risks
- Volatility spikes conflate uncertainty with first-moment (bad-news) shocks; disentangling them is
  contested.
- The real-options channel is one of several; financial-frictions channels also matter.

## Key references
- Bloom, N. (2009) — *The Impact of Uncertainty Shocks* — Econometrica
- Baker, S., Bloom, N. & Davis, S. (2016) — *Measuring Economic Policy Uncertainty* — Quarterly Journal of Economics
- Bloom, N. et al. (2018) — *Really Uncertain Business Cycles* — Econometrica
"""

WIKIS["8ea387f9-c386-4a6f-b5fc-40ef8e489d24"] = """\
# Size and Book-to-Market Factors in Earnings and Returns

**Source:** Fama, E. F. & French, K. R. (1995). *Journal of Finance* 50(1), 131–155.

## TL;DR
Asks *why* size and book-to-market predict returns by looking at firm **fundamentals**. It finds that
the same size and value factors that appear in stock returns also appear in **earnings**: small and
high-book-to-market firms are persistently less profitable. This common factor structure in earnings
supports a **risk-based (distress)** interpretation of the Fama-French three-factor model.

## What it documents
That SMB and HML are not just return patterns — they mirror common variation in profitability. High-
book-to-market signals relative distress (low, persistently weak earnings); low-book-to-market signals
sustained high profitability.

## Methodology
Track the earnings (return on book equity) of portfolios formed on size and book-to-market around
their formation, and relate the common factors in earnings to the SMB/HML return factors via
time-series regressions.

## Main findings
- High-BM (value) firms have **persistently low earnings**; low-BM (growth) firms have persistently
  high earnings — a distress/profitability story.
- Common factors in earnings line up with the SMB and HML **return** factors, though the link is
  imperfect (the market reacts before fundamentals fully play out).

## Implications for factor investing
- Lends a fundamentals-based, risk interpretation to value and size — a counterpoint to pure
  mispricing stories (Lakonishok-Shleifer-Vishny).
- Foreshadows the role of profitability, later formalized in the five-factor model.

## Key references
- Fama, E. & French, K. (1995) — *Size and Book-to-Market Factors in Earnings and Returns* — Journal of Finance
- Fama, E. & French, K. (1993) — *Common Risk Factors in the Returns on Stocks and Bonds* — Journal of Financial Economics
- Fama, E. & French, K. (2015) — *A Five-Factor Asset Pricing Model* — Journal of Financial Economics
"""

WIKIS["ea39ee52-108e-45a5-8478-b65a28196a1d"] = """\
# The Distribution of Realized Stock Return Volatility

**Source:** Andersen, T. G., Bollerslev, T., Diebold, F. X. & Ebens, H. (2001). *Journal of Financial
Economics* 61(1), 43–76.

## TL;DR
Applies the **realized-volatility** approach (summing high-frequency intraday squared returns) to
individual Dow Jones stocks and documents its distributional properties: realized variances and
correlations are highly persistent (long memory), realized volatility is right-skewed but its
**logarithm is approximately normal**, and daily returns **standardized by realized volatility are
nearly Gaussian**.

## What it documents
The empirical "stylized facts" of volatility once it is measured directly from intraday data — the
single-stock companion to Andersen-Bollerslev-Diebold-Labys (2003), which covered indices and FX.

## Method
- Construct daily **realized variance** for each stock from intraday returns; realized correlations
  similarly.
- Characterize the unconditional distributions of realized vol, log realized vol, and returns
  standardized by realized vol.

## Main findings
- **Log realized volatility ≈ normal**; realized correlations are roughly normal too.
- Returns divided by realized volatility are **close to standard normal** — fat tails come from
  time-varying volatility, not from non-normal shocks.
- Volatilities and correlations show **long memory** (slowly decaying dependence).

## Why it matters
These facts justify modeling and forecasting volatility in logs, underpin realized-volatility risk
models (and the later HAR model), and explain why returns look fat-tailed unconditionally yet
near-Gaussian once standardized by volatility.

## Limitations and risks
- Microstructure noise biases naive realized variance at very fine sampling (corrected by later
  estimators).
- Requires clean high-frequency data; jumps and overnight gaps need separate treatment.

## Key references
- Andersen, T., Bollerslev, T., Diebold, F. & Ebens, H. (2001) — *The Distribution of Realized Stock Return Volatility* — Journal of Financial Economics
- Andersen, T., Bollerslev, T., Diebold, F. & Labys, P. (2003) — *Modeling and Forecasting Realized Volatility* — Econometrica
- Corsi, F. (2009) — *A Simple Approximate Long-Memory Model of Realized Volatility (HAR)* — Journal of Financial Econometrics
"""

WIKIS["5c158e6b-eadf-4492-81d0-a42b2002aba0"] = """\
# A Macroeconomic Model with a Financial Sector

**Source:** Brunnermeier, M. K. & Sannikov, Y. (2014). *American Economic Review* 104(2), 379–421.

## TL;DR
A continuous-time macro-finance model in which a leveraged **financial intermediary sector** drives
the economy. Near the steady state the system is stable, but adverse shocks can push it into
**occasional violent crises** with fire sales and amplification. A central insight is the **volatility
paradox**: low measured volatility encourages leverage, which sows the seeds of future instability.

## What it documents (models)
How financial frictions turn modest shocks into large, nonlinear downturns through the net worth of
constrained intermediaries — endogenous risk that standard log-linearized models miss.

## Mechanism
- Intermediaries hold risky capital with leverage; their net worth is the key state variable.
- A negative shock erodes net worth → they delever and sell assets → prices fall → further losses
  (a **loss/amplification spiral**), generating endogenous volatility far above fundamental shocks.
- **Volatility paradox:** in calm times intermediaries lever up, so the system is most fragile exactly
  when measured risk is lowest.

## Why it matters
A foundational post-2008 model of systemic risk and crisis dynamics; it formalizes amplification,
fire sales, and the danger of leverage built up during quiet periods — complementing CoVaR and the
market/funding-liquidity literature.

## Limitations and risks
- Highly stylized (single intermediary sector, specific frictions); quantitative calibration is hard.
- Solves a fully nonlinear model — analytically demanding and sensitive to assumptions.

## Key references
- Brunnermeier, M. & Sannikov, Y. (2014) — *A Macroeconomic Model with a Financial Sector* — American Economic Review
- Brunnermeier, M. & Pedersen, L. (2009) — *Market Liquidity and Funding Liquidity* — Review of Financial Studies
- He, Z. & Krishnamurthy, A. (2013) — *Intermediary Asset Pricing* — American Economic Review
"""

WIKIS["a4dc375b-7f4c-4718-8d02-f2e93be6e0cb"] = """\
# Mutual Fund Performance: An Empirical Decomposition into Stock-Picking Talent, Style, Transactions Costs, and Expenses

**Source:** Wermers, R. (2000). *Journal of Finance* 55(4), 1655–1703.

## TL;DR
Decomposes mutual-fund returns using both **holdings** and **net returns**. The stocks funds hold beat
the market by about **1.3% per year** — evidence of genuine stock-picking skill — but funds'
**net returns underperform** by roughly 1% per year once transaction costs, expenses, and the drag
from non-stock holdings (cash) are subtracted. Skill exists in the portfolio; it does not survive
costs for the investor.

## What it documents
A reconciliation of two literatures: holdings-based studies that find skill and net-return studies
that find underperformance. Both are right — the gap is costs.

## Methodology
- Use quarterly **holdings** to measure the gross performance of funds' stock selections and style
  tilts (characteristic-based benchmarks).
- Compare to **net returns** to attribute the difference to expenses, trading costs, and cash drag.

## Main findings
- Funds' holdings outperform by ~1.3%/yr (≈0.75% selection + ≈0.55% style).
- **Net returns lag** the market by ~1%/yr; the ~2.3-point swing is expenses (~0.8%), transaction
  costs (~0.8%), and the cash/non-stock drag.
- High-turnover funds hold better stocks but pay it back in costs.

## Implications for factor investing
- Distinguish **gross skill** (in holdings) from **net delivery** (to investors) — a recurring lesson
  about costs eating an edge, and why net-of-cost evaluation is essential.

## Key references
- Wermers, R. (2000) — *Mutual Fund Performance: An Empirical Decomposition* — Journal of Finance
- Carhart, M. (1997) — *On Persistence in Mutual Fund Performance* — Journal of Finance
- Fama, E. & French, K. (2010) — *Luck versus Skill in the Cross-Section of Mutual Fund Returns* — Journal of Finance
"""

WIKIS["9ab5586c-e528-494e-a729-f60d98050cc4"] = """\
# Limited Attention, Information Disclosure, and Financial Reporting

**Source:** Hirshleifer, D. & Teoh, S. H. (2003). *Journal of Accounting and Economics* 36(1–3),
337–386.

## TL;DR
A model in which investors have **limited attention**, so the *form* of disclosure — not just its
content — moves prices. When relevant information is less salient (buried in footnotes, presented as
GAAP vs pro-forma, recognized vs merely disclosed), inattentive investors under-weight it, producing
mispricing. The framework explains under-reaction and accounting-driven anomalies.

## What it documents (models)
That presentation matters: with attention-constrained investors, the same economic facts lead to
different prices depending on how prominently they are reported.

## Mechanism
- A fraction of investors are inattentive and take reported numbers at face value, neglecting
  less-salient items (e.g. the cash-flow implications of accruals).
- Firms can exploit this through disclosure choices; markets then under-react to non-salient
  information and over-react to salient framing.

## Predictions
- **Under-reaction** to information that is disclosed but not salient (helping explain the accruals
  anomaly and post-earnings drift).
- Effects of **pro-forma vs GAAP** framing, recognition vs disclosure, and the timing/format of news.

## Why it matters
A foundational behavioral model of attention in markets, linking accounting/disclosure choices to
mispricing — the theoretical backdrop for the attention-and-prices literature (Barber-Odean,
Da-Engelberg-Gao) and for accruals/earnings anomalies.

## Limitations and risks
- "Attention" is modeled simply (a fraction of naive investors); measuring it empirically is hard.
- Predictions overlap with other behavioral biases, complicating identification.

## Key references
- Hirshleifer, D. & Teoh, S. H. (2003) — *Limited Attention, Information Disclosure, and Financial Reporting* — Journal of Accounting and Economics
- Sloan, R. (1996) — *Do Stock Prices Fully Reflect Information in Accruals and Cash Flows?* — The Accounting Review
- DellaVigna, S. & Pollet, J. (2009) — *Investor Inattention and Friday Earnings Announcements* — Journal of Finance
"""

WIKIS["c223e035-be0f-4fd3-8753-a1680a6a1ddf"] = """\
# Foreign Speculators and Emerging Equity Markets

**Source:** Bekaert, G. & Harvey, C. R. (2000). *Journal of Finance* 55(2), 565–613.

## TL;DR
Studies what happens when emerging equity markets **liberalize** — open to foreign investors. Market
integration **lowers the cost of capital** (dividend yields fall modestly), raises correlation with
world markets, and has only a small effect on local volatility. Opening up makes capital cheaper
without dramatically destabilizing prices.

## What it documents
The asset-pricing consequences of moving from a **segmented** market (priced by local risk) toward an
**integrated** one (priced by global risk), using the timing of liberalization reforms.

## Methodology
- Date capital-market liberalizations across emerging markets.
- Examine changes in dividend yields (a cost-of-capital proxy), return volatility, world-market
  correlation, and capital flows around these dates, with regime-switching models of integration.

## Main findings
- Liberalization **reduces the cost of capital** (dividend yields decline, on the order of tens of
  basis points), consistent with improved risk sharing.
- **Correlation with the world market rises**; the effect on volatility is small.
- Integration is gradual and partial, not a one-time switch.

## Why it matters
A foundational study of market integration/segmentation and the price of global vs local risk,
central to international asset pricing and emerging-market investing.

## Limitations and risks
- Liberalization dates are imprecise and coincide with other reforms (endogeneity).
- Cost-of-capital inference from dividend yields is indirect.

## Key references
- Bekaert, G. & Harvey, C. (2000) — *Foreign Speculators and Emerging Equity Markets* — Journal of Finance
- Bekaert, G. & Harvey, C. (1995) — *Time-Varying World Market Integration* — Journal of Finance
- Henry, P. B. (2000) — *Stock Market Liberalization, Economic Reform, and Emerging Market Equity Prices* — Journal of Finance
"""

WIKIS["ad60b9ed-ce8a-4afa-802c-a9b97e48b7a2"] = """\
# Financial Constraints Risk

**Source:** Whited, T. M. & Wu, G. (2006). *Review of Financial Studies* 19(2), 531–559.

## TL;DR
Builds an index of **financial constraints** (the "Whited-Wu index") from a structural investment
model rather than ad hoc proxies, and shows that financially constrained firms' returns **move
together** — there is a common constraints factor — though it carries only a modest, time-varying
risk premium.

## What it documents
That financing frictions are a systematic, priced-ish dimension of the cross-section: constrained
firms share exposure to a common factor tied to the tightness of external finance.

## How it is constructed
- Estimate a structural model of investment under financing constraints via GMM; the Lagrange
  multiplier on the financing constraint yields a firm-level **constraints index** (a function of
  cash flow, dividends, leverage, size, sales growth, industry growth).
- Form portfolios on the index and test for a common return factor and its premium.

## Evidence
- Constrained-firm returns **comove** (a constraints factor exists).
- The factor earns a **small, not robustly large** premium — constraints risk is real but not a
  dominant priced factor; the premium varies with macro conditions.

## Why it matters
A rigorous, model-based alternative to the Kaplan-Zingales index for measuring financial constraints,
widely used in corporate finance and asset pricing to study how financing frictions affect investment
and returns.

## Limitations and risks
- The index depends on the structural model's assumptions; alternative constraint measures disagree.
- Whether constraints risk is genuinely *priced* (vs proxying size/distress) is debated.

## Key references
- Whited, T. & Wu, G. (2006) — *Financial Constraints Risk* — Review of Financial Studies
- Kaplan, S. & Zingales, L. (1997) — *Do Investment-Cash Flow Sensitivities Provide Useful Measures of Financing Constraints?* — Quarterly Journal of Economics
- Lamont, O., Polk, C. & Saá-Requejo (2001) — *Financial Constraints and Stock Returns* — Review of Financial Studies
"""

WIKIS["599797d6-2158-4353-a2fe-e5d8b4b94939"] = """\
# The Market Pricing of Accruals Quality

**Source:** Francis, J., LaFond, R., Olsson, P. & Schipper, K. (2005). *Journal of Accounting and
Economics* 39(2), 295–327.

## TL;DR
Shows that **accruals quality** — how well a firm's accruals map into cash flows (the Dechow-Dichev
measure) — is **priced**: firms with poorer accruals quality face a higher cost of both debt and
equity. Poor accruals quality is treated by markets as **information risk** that investors require
compensation to bear.

## What it documents
That earnings quality is not just an accounting curiosity but a priced risk: low-quality (noisy,
hard-to-interpret) accruals raise a firm's cost of capital.

## How it is measured
- Compute **accruals quality (AQ)** as the standard deviation of the residuals from regressing
  working-capital accruals on past, current, and future cash flows (Dechow-Dichev).
- Relate AQ to costs of debt (interest rates, ratings) and equity (factor-model loadings, implied
  cost of capital), and form an **AQ factor**.

## Evidence
- Worse accruals quality → **higher cost of debt and equity**.
- Returns load on an **AQ factor**, and the loading carries a premium — consistent with AQ as priced
  information risk; the authors distinguish "innate" (business-driven) from "discretionary" AQ.

## Why it matters
Operationalizes earnings quality as a priced factor, bridging accounting and asset pricing and
underpinning the quality-investing literature (alongside profitability/RMW).

## Limitations and risks
- Whether AQ is a genuine priced *risk* factor or a mispricing/characteristic is contested (Core,
  Guay & Verdi 2008 challenge the pricing result).
- The AQ measure mixes manipulation with innocent estimation noise.

## Key references
- Francis, J., LaFond, R., Olsson, P. & Schipper, K. (2005) — *The Market Pricing of Accruals Quality* — Journal of Accounting and Economics
- Dechow, P. & Dichev, I. (2002) — *The Quality of Accruals and Earnings* — The Accounting Review
- Core, J., Guay, W. & Verdi, R. (2008) — *Is Accruals Quality a Priced Risk Factor?* — Journal of Accounting and Economics
"""

WIKIS["108767b3-e5f0-40a5-a610-f990db9aa013"] = """\
# Market Timing and Capital Structure

**Source:** Baker, M. & Wurgler, J. (2002). *Journal of Finance* 57(1), 1–32.

## TL;DR
Argues that a firm's **capital structure is the cumulative outcome of past attempts to time the equity
market** — issuing stock when it is overvalued and repurchasing or relying on debt when it is
undervalued. Leverage is strongly **negatively related to a firm's historical market valuations**, and
these timing effects on leverage are **persistent** for a decade or more.

## What it documents
That there is no stable target leverage ratio firms revert to; instead, low leverage today reflects a
history of issuing equity when market-to-book was high. Market timing leaves a long-lived imprint on
the balance sheet.

## How it is measured
- Build a **"external finance weighted-average" market-to-book** ratio that captures the valuations
  prevailing when a firm actually raised capital.
- Regress leverage on this historical timing measure plus standard capital-structure controls.

## Main findings
- Leverage falls with **historical** (timing-weighted) market-to-book — firms that issued equity in
  high-valuation periods carry lower leverage long afterward.
- The effect is **persistent** (10+ years), contradicting rapid rebalancing to a target ratio.

## Why it matters
A foundational behavioral-corporate-finance result: managers exploit windows of mispricing, and
capital structure is path-dependent rather than the result of a static trade-off — connecting market
(in)efficiency to corporate financing.

## Limitations and risks
- The persistence result is debated (some argue firms slowly rebalance; mechanical issues with the
  market-to-book measure).
- Distinguishing genuine timing from rational responses to investment opportunities is hard.

## Key references
- Baker, M. & Wurgler, J. (2002) — *Market Timing and Capital Structure* — Journal of Finance
- Baker, M. & Wurgler, J. (2006) — *Investor Sentiment and the Cross-Section of Stock Returns* — Journal of Finance
- Welch, I. (2004) — *Capital Structure and Stock Returns* — Journal of Political Economy
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
