"""
author_canonical_wikis_8.py — eighth batch of hand-authored wikis for canonical papers.

Covers law & finance (La Porta et al.), tail-dependence of international markets (Longin-Solnik),
experience-based risk taking (Malmendier-Nagel), disclosure & cost of capital (Lambert-Leuz-
Verrecchia), the network origins of aggregate fluctuations (Acemoglu et al.), decision-making under
ambiguity (Klibanoff-Marinacci-Mukerji), affine term-structure models (Dai-Singleton), and panels
with a multifactor error structure (Pesaran). Public, paper-focused content only.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_canonical_wikis_8.py --dry-run
    ...                                          python pipeline/author_canonical_wikis_8.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

WIKIS = {}

WIKIS["a1f1939f-4747-4963-9446-126d0d63ec49"] = """\
# Legal Determinants of External Finance

**Source:** La Porta, R., Lopez-de-Silanes, F., Shleifer, A. & Vishny, R. W. (1997). *Journal of
Finance* 52(3), 1131–1150.

## TL;DR
The founding paper of the "law and finance" literature. Countries with stronger **legal protection
of outside investors** — and, by extension, common-law rather than French-civil-law legal origins —
have **larger and more developed capital markets**: more external equity and debt finance, more
listed firms, and more IPOs. Law shapes finance.

## What it documents
That the size and depth of a country's financial markets is not just a function of wealth or growth,
but of the **rules and enforcement** that protect minority shareholders and creditors from
expropriation by insiders.

## Methodology
Assemble cross-country indices of shareholder and creditor rights, rule of law, and legal origin for
~49 countries, then relate them to measures of capital-market development (market capitalization to
GNP, number of listed firms per capita, IPO activity, debt).

## Main findings
- **Stronger investor protection → larger external-finance markets** (equity and debt).
- **Common-law countries** protect investors most and have the deepest markets; **French-civil-law**
  countries the least.
- Enforcement (rule of law) matters as much as the laws on the books.

## Why it matters
A foundational result connecting institutions to financial development, launching the "law and
finance" and investor-protection literatures and influencing corporate-governance research (e.g. the
governance/return work of Gompers-Ishii-Metrick) and emerging-market investing.

## Limitations and risks
- Legal-origin classifications and rights indices are coarse and debated; endogeneity (law and
  finance co-evolve) complicates causal claims.
- Later work questioned the robustness of some indices and the common-law advantage.

## Key references
- La Porta, R., Lopez-de-Silanes, F., Shleifer, A. & Vishny, R. (1997) — *Legal Determinants of External Finance* — Journal of Finance
- La Porta, R. et al. (1998) — *Law and Finance* — Journal of Political Economy
- Gompers, P., Ishii, J. & Metrick, A. (2003) — *Corporate Governance and Equity Prices* — Quarterly Journal of Economics
"""

WIKIS["2a088b27-fbad-4385-aac1-5bf3612df49b"] = """\
# Extreme Correlation of International Equity Markets

**Source:** Longin, F. & Solnik, B. (2001). *Journal of Finance* 56(2), 649–676.

## TL;DR
Uses **extreme value theory** to study how international equity-market correlations behave in the
tails, and finds a stark asymmetry: correlation rises sharply in **bear markets** (large joint
*losses*) but **not** in bull markets. Diversification across countries fails exactly when you need
it most — markets crash together.

## What it documents
That the comforting low average correlation between national equity markets is misleading for risk
management: dependence is **state-dependent and asymmetric**, concentrating in the left tail.

## Methodology
- Model the tails of return distributions with **extreme value theory** (not the Gaussian, which
  understates joint extremes).
- Estimate the correlation of exceedances conditional on large positive vs large negative returns,
  testing whether tail correlation differs from the multivariate-normal benchmark.

## Main findings
- **Correlation increases with the size of negative returns** but is roughly flat or falling for
  positive returns — a pronounced bear-market correlation increase.
- The pattern is inconsistent with multivariate normality and with simple GARCH; it reflects genuine
  asymmetric **tail dependence**.

## Why it matters
A foundational result for international diversification and risk management: it shows that
correlations used in portfolio construction must account for tail dependence, motivating copulas,
extreme-value methods, and stress testing.

## Limitations and risks
- Extreme-tail estimation is data-hungry and sensitive to threshold choices.
- Documents the phenomenon more than its cause (contagion vs common shocks).

## Key references
- Longin, F. & Solnik, B. (2001) — *Extreme Correlation of International Equity Markets* — Journal of Finance
- Ang, A. & Chen, J. (2002) — *Asymmetric Correlations of Equity Portfolios* — Journal of Financial Economics
- Embrechts, P., McNeil, A. & Straumann, D. (2002) — *Correlation and Dependence in Risk Management* — (copulas)
"""

WIKIS["17520769-0ab6-4d7b-ad4c-a61017b93af4"] = """\
# Depression Babies: Do Macroeconomic Experiences Affect Risk Taking?

**Source:** Malmendier, U. & Nagel, S. (2011). *Quarterly Journal of Economics* 126(1), 373–416.

## TL;DR
Personally-lived macroeconomic history shapes financial risk-taking. Individuals who experienced
**low stock-market returns over their lifetimes** are subsequently **less willing to take financial
risk** — less likely to participate in the stock market and, if they do, allocate less to equities.
Recent experiences weigh more heavily. Beliefs are formed by what you've lived through, not just the
full historical record.

## What it documents
"Experience effects": risk attitudes and return expectations depend on the realizations a person has
actually experienced, with greater weight on recent decades — a departure from rational expectations
that use all available data.

## Methodology
- Use decades of the U.S. Survey of Consumer Finances to relate each household's stock-market
  participation and equity share to the **stock returns experienced over its lifetime** (age-weighted).
- Repeat for bond returns and inflation experiences; estimate the recency weighting.

## Main findings
- Higher **lifetime-experienced** stock returns → higher participation and equity allocation;
  lower experienced returns ("depression babies") → more caution.
- The effect is stronger for **younger** households (a given experience is a larger share of their
  short history) and decays with how long ago it occurred.

## Why it matters
A landmark in behavioral/experience-based learning: it explains persistent cohort differences in
risk-taking and informs models of belief formation, the equity-premium puzzle, and household finance.

## Limitations and risks
- Survey-based; separating experience from cohort/time effects requires structure.
- The experience-weighting is estimated, not micro-founded.

## Key references
- Malmendier, U. & Nagel, S. (2011) — *Depression Babies* — Quarterly Journal of Economics
- Malmendier, U. & Nagel, S. (2016) — *Learning from Inflation Experiences* — Quarterly Journal of Economics
- Vissing-Jorgensen, A. (2003) — *Perspectives on Behavioral Finance* — NBER Macroeconomics Annual
"""

WIKIS["ef8c76d7-65f3-45c9-8dcb-75cca982668e"] = """\
# Accounting Information, Disclosure, and the Cost of Capital

**Source:** Lambert, R., Leuz, C. & Verrecchia, R. E. (2007). *Journal of Accounting Research* 45(2),
385–420.

## TL;DR
Provides a rigorous model of **how accounting information and disclosure affect a firm's cost of
capital**. Better information lowers the cost of capital, but the paper makes a key distinction: part
of the effect is **non-diversifiable** (information changes investors' assessment of the *covariance*
of a firm's cash flows with the market) and so cannot be diversified away, while some is.

## What it documents (models)
That the quality of disclosure is priced through assessed cash-flow covariances, and — in imperfect
markets — through the firm's real decisions, giving a precise channel from accounting to required
returns.

## Mechanism
- In a CAPM-style economy, expected returns depend on the **covariance** of a firm's cash flows with
  the aggregate; better information sharpens those covariance assessments.
- Higher-quality disclosure can **lower** the assessed covariance (and hence cost of capital), a
  component that is *not* diversifiable, contradicting the intuition that firm-specific information
  effects always wash out in a large economy.

## Why it matters
A foundational theoretical underpinning for the disclosure/cost-of-capital literature, clarifying when
and why information quality is priced — relevant to the accruals-quality and information-risk results
(Francis et al.; Easley-O'Hara) and to corporate disclosure policy.

## Limitations and risks
- A stylized model; mapping "information quality" to measurable disclosure is hard.
- Empirically separating the diversifiable and non-diversifiable channels is challenging.

## Key references
- Lambert, R., Leuz, C. & Verrecchia, R. (2007) — *Accounting Information, Disclosure, and the Cost of Capital* — Journal of Accounting Research
- Easley, D. & O'Hara, M. (2004) — *Information and the Cost of Capital* — Journal of Finance
- Francis, J., LaFond, R., Olsson, P. & Schipper, K. (2005) — *The Market Pricing of Accruals Quality* — Journal of Accounting and Economics
"""

WIKIS["b78abad4-0f5a-4b48-838d-826601ec74a4"] = """\
# The Network Origins of Aggregate Fluctuations

**Source:** Acemoglu, D., Carvalho, V. M., Ozdaglar, A. & Tahbaz-Salehi, A. (2012). *Econometrica*
80(5), 1977–2016.

## TL;DR
Shows that **microeconomic shocks need not wash out in the aggregate** when the economy's production
network is asymmetric. If some sectors are central — supplying inputs to many others — then
idiosyncratic shocks to those hubs **propagate through the network** and generate aggregate
fluctuations, decaying far more slowly than the standard 1/√n diversification argument predicts.

## What it documents (models)
A network/input-output foundation for macro volatility: the structure of inter-sectoral linkages, not
just the number of sectors, determines whether granular shocks aggregate up.

## Mechanism
- In a balanced network (every sector equally connected), independent sectoral shocks average out at
  rate 1/√n — aggregate volatility vanishes as the economy grows.
- With **heavy-tailed** connectivity (a few hub suppliers), the effective rate of diversification is
  much slower, so idiosyncratic shocks to hubs drive aggregate fluctuations.
- "Second-order" interconnections (suppliers of suppliers) amplify this further.

## Why it matters
A foundational result linking network topology to systemic risk and the "granular" origins of
business cycles (complementing Gabaix's granularity). For finance, it formalizes why diversification
can fail at the system level and why concentrated linkages create non-diversifiable risk — central to
systemic-risk thinking.

## Limitations and risks
- Requires good input-output data; the mapping from sectoral to firm-level networks is nontrivial.
- A real-side model; financial-network amplification (interbank, funding) is a separate channel.

## Key references
- Acemoglu, D., Carvalho, V., Ozdaglar, A. & Tahbaz-Salehi, A. (2012) — *The Network Origins of Aggregate Fluctuations* — Econometrica
- Gabaix, X. (2011) — *The Granular Origins of Aggregate Fluctuations* — Econometrica
- Billio, M., Getmansky, M., Lo, A. & Pelizzon, L. (2012) — *Econometric Measures of Connectedness and Systemic Risk* — Journal of Financial Economics
"""

WIKIS["be95fb74-c1d9-475d-a843-cecd5e344495"] = """\
# A Smooth Model of Decision Making under Ambiguity

**Source:** Klibanoff, P., Marinacci, M. & Mukerji, S. (2005). *Econometrica* 73(6), 1849–1892.

## TL;DR
Provides a tractable decision-theoretic model that cleanly separates **risk** (known probabilities)
from **ambiguity** (unknown/uncertain probabilities), and separates an agent's **ambiguity attitude**
from the ambiguity they face. It does so with a *smooth* (differentiable) function applied to expected
utilities computed under different priors — making ambiguity aversion as analytically convenient as
risk aversion.

## What it documents (models)
A representation in which the agent evaluates an act by (1) computing its expected utility under each
possible probability model, then (2) taking a **concave transformation** of those expected utilities
before averaging over models. Concavity of that transformation = ambiguity aversion.

## Why it matters
- Gives finance a workable way to model **model uncertainty / Knightian uncertainty** — distinct from
  risk — with smooth, differentiable preferences (unlike the kinked max-min of Gilboa-Schmeidler).
- Underpins asset-pricing work on ambiguity (e.g. ambiguity premia, robust portfolio choice,
  participation puzzles) and connects to robust control approaches.

## Mechanism
- Risk attitude is captured by the utility over outcomes; **ambiguity attitude** by the curvature of
  the second-stage transformation φ.
- φ linear ⇒ ambiguity neutrality (reduces to expected utility); φ concave ⇒ aversion to spread in
  expected utilities across models.

## Limitations and risks
- Requires specifying a set of priors and a second-order distribution over them — modeling choices
  that drive results.
- Empirically separating ambiguity aversion from risk aversion is difficult.

## Key references
- Klibanoff, P., Marinacci, M. & Mukerji, S. (2005) — *A Smooth Model of Decision Making under Ambiguity* — Econometrica
- Gilboa, I. & Schmeidler, D. (1989) — *Maxmin Expected Utility with Non-Unique Prior* — Journal of Mathematical Economics
- Hansen, L. & Sargent, T. (2008) — *Robustness* — Princeton University Press
"""

WIKIS["92db80cc-faa8-4716-b754-05fe9cff8b1d"] = """\
# Specification Analysis of Affine Term Structure Models

**Source:** Dai, Q. & Singleton, K. J. (2000). *Journal of Finance* 55(5), 1943–1978.

## TL;DR
Provides a complete **classification of affine term-structure models (ATSMs)** — the workhorse class
for pricing bonds and interest-rate derivatives, in which yields are affine (linear) functions of a
few latent state variables. It organizes N-factor models by how many factors drive volatility, shows
which sub-families are admissible (well-defined), and finds that matching the data requires models
that allow **both flexible factor correlations and time-varying volatility** — features that trade off
within the affine class.

## What it documents
A canonical taxonomy (the A_m(N) classification: N factors, m of which drive the conditional variance)
and the trade-offs each sub-family imposes between correlation structure and stochastic volatility.

## Methodology
- Characterize the conditions under which an N-factor affine model is **admissible** and identify a
  maximal, identified canonical form for each sub-family.
- Estimate representative models on U.S. swap/yield data and compare their fit.

## Main findings
- Affine models face an inherent **tension**: the more factors allowed to drive volatility, the more
  restricted the admissible correlations among factors become.
- The best empirical fit needs both time-varying volatility and rich correlations — pushing toward
  particular sub-families and motivating later extensions.

## Why it matters
The reference framework for term-structure modeling, central to fixed-income pricing, interest-rate
risk management, and macro-finance yield-curve research.

## Limitations and risks
- Affine structure, chosen for tractability, can be too rigid (motivating quadratic and non-affine
  models).
- Latent factors are hard to interpret; estimation is sensitive to identification choices.

## Key references
- Dai, Q. & Singleton, K. (2000) — *Specification Analysis of Affine Term Structure Models* — Journal of Finance
- Duffie, D. & Kan, R. (1996) — *A Yield-Factor Model of Interest Rates* — Mathematical Finance
- Vasicek, O. (1977) — *An Equilibrium Characterization of the Term Structure* — Journal of Financial Economics
"""

WIKIS["d2bcf254-fc54-4a78-a658-45b2f03a2615"] = """\
# Estimation and Inference in Large Heterogeneous Panels with a Multifactor Error Structure

**Source:** Pesaran, M. H. (2006). *Econometrica* 74(4), 967–1012.

## TL;DR
Introduces the **Common Correlated Effects (CCE)** estimator for panel-data models where units are
**cross-sectionally dependent** through unobserved common factors (e.g. an unobserved market or macro
factor that affects every firm/country). The trick is simple and powerful: include **cross-sectional
averages** of the dependent and explanatory variables as proxies for the latent common factors,
yielding consistent slope estimates without having to estimate the factors themselves.

## What it documents (method)
A way to handle the cross-sectional correlation that pervades financial and macro panels — where
standard fixed-effects estimators are biased because shocks are not independent across units.

## Method
- Model each unit's outcome as depending on regressors plus **unobserved common factors** with
  heterogeneous loadings.
- Augment the regression with cross-sectional averages of the variables; under general conditions
  these span the space of the latent factors, so the **CCE (mean-group / pooled) estimators** are
  consistent and asymptotically normal.

## Why it matters
A foundational, widely used econometric tool for empirical finance and macro: it makes panel
inference valid when an unobserved common factor (a market, a global cycle) drives co-movement —
exactly the setting of cross-country and cross-firm return panels.

## Limitations and risks
- Assumes the common factors are captured by cross-sectional averages (a finite number of strong
  factors); weak or many factors complicate this.
- Requires reasonably large N and T.

## Key references
- Pesaran, M. H. (2006) — *Estimation and Inference in Large Heterogeneous Panels with a Multifactor Error Structure* — Econometrica
- Bai, J. (2009) — *Panel Data Models with Interactive Fixed Effects* — Econometrica
- Pesaran, M. H. (2007) — *A Simple Panel Unit Root Test in the Presence of Cross-Section Dependence* — Journal of Applied Econometrics
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
