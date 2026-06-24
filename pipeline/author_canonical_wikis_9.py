"""
author_canonical_wikis_9.py — ninth batch: the modern machine-learning asset-pricing canon.

Covers IPCA (Kelly-Pruitt-Su), Shrinking the Cross-Section (Kozak-Nagel-Santosh), nonparametric
characteristic selection (Freyberger-Neuhierl-Weber), the three-pass omitted-factor risk premium
(Giglio-Xiu), conditional autoencoders (Gu-Kelly-Xiu), asset-pricing trees (Bryzgalova-Pelger-Zhu),
the factor-zoo test (Feng-Giglio-Xiu), and the GAN/deep-SDF (Chen-Pelger-Zhu).

Several of these were seeded from working-paper DOIs, so this script also sets the published year
explicitly and refreshes citation_count from OpenAlex (first result that passes a title-overlap gate,
to avoid grabbing an unrelated blockbuster) so the record and significance ranking are correct.
Public, paper-focused content only.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_canonical_wikis_9.py --dry-run
    ...                                          python pipeline/author_canonical_wikis_9.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, time, urllib.parse, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
OPENALEX = "https://api.openalex.org/works"
UA = "convexpi-lab/wikis (mailto:research@convexpi.ai)"

# id -> (canonical published title for OpenAlex re-lookup, markdown)
WIKIS = {}

WIKIS["2572cee5-20d8-462e-b876-fedd52acabef"] = ("Characteristics are covariances: A unified model of risk and return", 2019, """\
# Characteristics Are Covariances: A Unified Model of Risk and Return (IPCA)

**Source:** Kelly, B. T., Pruitt, S. & Su, Y. (2019). *Journal of Financial Economics* 134(3),
501–524.

## TL;DR
Introduces **Instrumented Principal Components Analysis (IPCA)** — a latent-factor model in which a
stock's factor *loadings* are linear functions of its observable **characteristics**. The provocative
claim in the title: characteristics predict returns mainly because they proxy for **risk exposures
(covariances/betas)**, not because they earn anomalous **alpha**. A handful of latent factors with
characteristic-driven loadings explains the cross-section, leaving little residual mispricing.

## What it documents (models)
A unified, estimable bridge between the "characteristics" view (firm attributes predict returns) and
the "covariances" view (risk exposures earn premia), turning the sprawling factor zoo into a
low-dimensional conditional factor model.

## Method
- Latent factors **f_t** with time-varying loadings **β_{i,t} = Z_{i,t} Γ**, where Z are characteristics
  and Γ maps characteristics to loadings.
- Estimate factors and Γ jointly by an instrumented PCA; test the restriction that characteristics
  enter only through loadings (risk) vs. also through intercepts (alpha).

## Main findings
- A small number of factors (≈5–6) with characteristic-instrumented loadings prices the cross-section.
- The **alpha** (anomaly intercept) terms are largely insignificant once loadings are conditioned on
  characteristics — consistent with risk compensation over mispricing.

## Why it matters
A foundational ML asset-pricing model: it tames the factor zoo by dimensionality reduction and recasts
"anomalies" as conditional risk, influencing the autoencoder and SDF-shrinkage literatures.

## Limitations and risks
- Loadings are restricted to be *linear* in characteristics (relaxed later by autoencoders).
- Latent factors are statistical, not economically labeled; results depend on the characteristic set.

## Key references
- Kelly, B., Pruitt, S. & Su, Y. (2019) — *Characteristics Are Covariances* — Journal of Financial Economics
- Kozak, S., Nagel, S. & Santosh, S. (2020) — *Shrinking the Cross-Section* — Journal of Financial Economics
- Gu, S., Kelly, B. & Xiu, D. (2021) — *Autoencoder Asset Pricing Models* — Journal of Econometrics
""")

WIKIS["f6421c91-d5a9-4895-9d5a-03eef7fadf29"] = ("Shrinking the cross-section", 2020, """\
# Shrinking the Cross-Section

**Source:** Kozak, S., Nagel, S. & Santosh, S. (2020). *Journal of Financial Economics* 135(2),
271–292.

## TL;DR
Estimates the **stochastic discount factor (SDF)** from a large set of characteristic-sorted
portfolios using **economically-motivated shrinkage**. The central message reconciles the factor zoo
with no-arbitrage: a **sparse** SDF in terms of a *few characteristics* does **not** exist — you can't
summarize expected returns with a handful of anomalies — but a **low-dimensional** SDF in terms of a
few **principal components** of the characteristic portfolios *does*. Many characteristics are priced;
their information just concentrates in dominant common components.

## What it documents (models)
That naive selection ("which 3 anomalies matter?") fails, while the right regularization recovers a
robust, low-dimensional SDF.

## Method
- Build the SDF from many characteristic portfolios; impose a **Bayesian prior** that penalizes SDFs
  implying implausibly high Sharpe ratios (near-arbitrage) — equivalent to **ridge (L2)** shrinkage,
  optionally with **L1** sparsity, applied in principal-component space.
- Select the penalty by out-of-sample cross-validation.

## Main findings
- Robust SDFs load on the **leading PCs** of the characteristic portfolios; sparsity in raw
  characteristics is rejected.
- Heavy shrinkage is essential for out-of-sample performance — unregularized SDFs overfit badly.

## Why it matters
A foundational treatment of high-dimensional SDF estimation: it shows how to use *all* the anomalies
without overfitting and frames the zoo as a low-rank, not sparse, phenomenon.

## Limitations and risks
- PCs are statistical and rotate with the input portfolios; the prior is a modeling choice.
- Linear SDF in the chosen portfolios (nonlinear extensions follow in later deep-learning work).

## Key references
- Kozak, S., Nagel, S. & Santosh, S. (2020) — *Shrinking the Cross-Section* — Journal of Financial Economics
- Kozak, S., Nagel, S. & Santosh, S. (2018) — *Interpreting Factor Models* — Journal of Finance
- Kelly, B., Pruitt, S. & Su, Y. (2019) — *Characteristics Are Covariances* — Journal of Financial Economics
""")

WIKIS["48f9875c-ad56-439e-9234-85b333539f20"] = ("Dissecting characteristics nonparametrically", 2020, """\
# Dissecting Characteristics Nonparametrically

**Source:** Freyberger, J., Neuhierl, A. & Weber, M. (2020). *Review of Financial Studies* 33(5),
2326–2377.

## TL;DR
Asks which firm characteristics provide **independent**, incremental predictive power for returns —
allowing for **nonlinear** effects and interactions — using an **adaptive group LASSO** for
model selection. Out of the dozens of candidates, a relatively small set (around a dozen) survive as
robust independent predictors; many popular characteristics are **subsumed** by others, and several
effects are materially **nonlinear**.

## What it documents
A disciplined, nonparametric pruning of the characteristic zoo: which signals matter *on their own*
once you let the data choose functional form and control for the rest.

## Method
- Model expected returns as an additive, nonparametric function of characteristics (spline basis per
  characteristic).
- Apply the **adaptive group LASSO** to simultaneously select relevant characteristics and estimate
  their nonlinear shapes, with out-of-sample validation.

## Main findings
- A parsimonious set (e.g. variants of momentum, profitability, value, size-related, and a few
  others) retains independent predictive power; the rest add little once these are included.
- Several characteristics predict returns **nonlinearly**, which linear cross-sectional regressions
  miss.

## Why it matters
A cornerstone of the model-selection approach to the factor zoo, complementary to SDF shrinkage and
IPCA, and an early demonstration that nonlinearity is economically relevant in the cross-section.

## Limitations and risks
- Additive structure limits the interaction effects later captured by trees/neural nets.
- Selection is sensitive to the candidate set and the validation scheme.

## Key references
- Freyberger, J., Neuhierl, A. & Weber, M. (2020) — *Dissecting Characteristics Nonparametrically* — Review of Financial Studies
- Green, J., Hand, J. & Zhang, X. F. (2017) — *The Characteristics that Provide Independent Information about Average Returns* — Review of Financial Studies
- Gu, S., Kelly, B. & Xiu, D. (2020) — *Empirical Asset Pricing via Machine Learning* — Review of Financial Studies
""")

WIKIS["a7a04b5d-df18-4afc-9015-af2639b6bc38"] = ("Asset pricing with omitted factors", 2021, """\
# Asset Pricing with Omitted Factors

**Source:** Giglio, S. & Xiu, D. (2021). *Journal of Political Economy* 129(7), 1947–1990.

## TL;DR
Provides a **three-pass** method to estimate the **risk premium of any observed factor** that is
robust to two chronic problems: **omitted factors** (you can't control for everything) and
**measurement error** in the factor. The estimate is **invariant** to which other factors are
included — solving the long-standing issue that estimated risk premia flip sign depending on the
controls.

## What it documents (method)
A consistent, rotation-invariant way to ask "is this factor priced, and by how much?" without needing
the *correct, complete* model — a major obstacle in factor evaluation.

## Method
1. **PCA** on a large panel of test-asset returns to recover the latent factor space spanned by all
   priced sources of risk.
2. Cross-sectional regression to estimate the risk premia of those latent factors.
3. Project the **observed candidate factor** onto the latent space; its risk premium is the implied
   combination — consistent even if the candidate is observed with error or correlated with omitted
   factors.

## Why it matters
A foundational tool for the empirical evaluation of proposed factors, used to settle debates over
whether macro and traded factors carry premia, and complementary to the factor-zoo selection tests.

## Limitations and risks
- Requires a large cross-section of test assets so PCA recovers the true factor space.
- Assumes the priced risks are spanned by the test assets (strong-factor structure).

## Key references
- Giglio, S. & Xiu, D. (2021) — *Asset Pricing with Omitted Factors* — Journal of Political Economy
- Feng, G., Giglio, S. & Xiu, D. (2020) — *Taming the Factor Zoo* — Journal of Finance
- Kelly, B., Pruitt, S. & Su, Y. (2019) — *Characteristics Are Covariances* — Journal of Financial Economics
""")

WIKIS["7c47ad7f-2c99-4d63-9b3c-3dfed1016855"] = ("Autoencoder asset pricing models", 2021, """\
# Autoencoder Asset Pricing Models

**Source:** Gu, S., Kelly, B. T. & Xiu, D. (2021). *Journal of Econometrics* 222(1), 429–450.

## TL;DR
A **nonlinear conditional latent-factor model** built as a neural-network **autoencoder**. It
generalizes IPCA: both the latent factors *and* the characteristic-conditioned **loadings** are
learned by neural networks, while the architecture enforces the **no-arbitrage (beta-pricing)**
structure. Allowing loadings to be nonlinear functions of characteristics improves out-of-sample
pricing over linear factor models, PCA, and IPCA.

## What it documents (models)
That the mapping from firm characteristics to risk exposures is **nonlinear**, and that embedding
asset-pricing restrictions inside a deep model yields better, economically-disciplined factors.

## Method
- A "conditional autoencoder": one network maps characteristics → factor **loadings** (betas); the
  factors themselves are latent and estimated from returns.
- Returns are reconstructed as loadings × factors (the no-arbitrage restriction), trained end-to-end;
  reduces to IPCA when the networks are linear.

## Main findings
- Nonlinear loadings deliver higher out-of-sample Sharpe ratios and lower pricing errors than linear
  conditional models.
- A few latent factors suffice; the gains come from the **functional form** of the loadings.

## Why it matters
A bridge between the factor-model tradition and deep learning, showing how to impose economic
structure on neural networks — influential for the deep-SDF literature.

## Limitations and risks
- Neural estimation needs care (regularization, ensembling) and is less interpretable than IPCA.
- Latent factors remain statistical constructs.

## Key references
- Gu, S., Kelly, B. & Xiu, D. (2021) — *Autoencoder Asset Pricing Models* — Journal of Econometrics
- Gu, S., Kelly, B. & Xiu, D. (2020) — *Empirical Asset Pricing via Machine Learning* — Review of Financial Studies
- Kelly, B., Pruitt, S. & Su, Y. (2019) — *Characteristics Are Covariances* — Journal of Financial Economics
""")

WIKIS["c764521e-046b-4575-8d64-c3f4d32ddefc"] = ("Forest through the trees building cross-sections of stock returns", 2025, """\
# Forest Through the Trees: Building Cross-Sections of Stock Returns

**Source:** Bryzgalova, S., Pelger, M. & Zhu, J. (2025). *Journal of Finance* (forthcoming/early
view).

## TL;DR
Uses **decision trees** to build better **test-asset portfolios** for asset pricing. Instead of the
usual one- or two-way characteristic sorts, "Asset-Pricing Trees" sort stocks on **many
characteristics jointly and nonlinearly**, then prune to a parsimonious set of basis portfolios that
**span the SDF**. The result is a set of test assets that capture interaction effects standard sorts
miss, giving sharper estimates and tougher tests of factor models.

## What it documents (method)
That the *choice of test assets* is first-order: nonlinear, conditional portfolios reveal pricing
information invisible to univariate sorts, and trees are a natural, interpretable way to construct them.

## Method
- Grow decision trees that recursively split the stock universe on characteristics, forming
  conditional portfolios at the leaves.
- **Prune** (regularize) the forest so the retained portfolios maximize the spanned SDF / Sharpe ratio
  out-of-sample, yielding a small, robust cross-section.

## Why it matters
Reframes a foundational design choice in empirical asset pricing — *which* portfolios to price —
through machine learning, complementing the SDF-estimation work that takes test assets as given.

## Limitations and risks
- Tree construction and pruning involve tuning that affects results.
- Like all test-asset choices, conclusions about factor models can depend on the basis built.

## Key references
- Bryzgalova, S., Pelger, M. & Zhu, J. (2025) — *Forest Through the Trees* — Journal of Finance
- Kozak, S., Nagel, S. & Santosh, S. (2020) — *Shrinking the Cross-Section* — Journal of Financial Economics
- Chen, L., Pelger, M. & Zhu, J. (2024) — *Deep Learning in Asset Pricing* — Management Science
""")

WIKIS["8563ccfc-ff3d-43c2-9aa8-30c7e1fceee9"] = ("Taming the factor zoo: A test of new factors", 2020, """\
# Taming the Factor Zoo: A Test of New Factors

**Source:** Feng, G., Giglio, S. & Xiu, D. (2020). *Journal of Finance* 75(3), 1327–1370.

## TL;DR
Provides a rigorous, **model-selection-based test** for whether a **newly proposed factor** adds
explanatory power for the cross-section of returns **beyond the hundreds of factors already proposed**.
It disciplines the "factor zoo": a new factor must earn its keep controlling for the existing zoo, and
the method delivers **valid inference** despite the high-dimensional control set.

## What it documents (method)
A statistically honest answer to "is this *new* factor useful?" — accounting for the fact that, with
so many candidate factors, naive tests over-reject.

## Method
- Treat the existing factors as high-dimensional controls and the new factor as the variable of
  interest in a cross-sectional pricing regression.
- Use **double-selection LASSO** (select controls for both the returns and the new factor, then
  estimate) to remove omitted-variable and model-selection bias, giving valid standard errors on the
  new factor's premium.

## Main findings
- Most newly proposed factors contribute **little** once the zoo is controlled for; only a handful add
  robust incremental explanatory power.
- Proper double-selection materially changes which factors look significant versus naive tests.

## Why it matters
A foundational methodological check that raised the bar for proposing factors and is now standard in
factor evaluation, paired with the omitted-factor risk-premium estimator.

## Limitations and risks
- Conclusions depend on the assembled set of control factors.
- Linear pricing framework; interactions/nonlinearities are out of scope.

## Key references
- Feng, G., Giglio, S. & Xiu, D. (2020) — *Taming the Factor Zoo* — Journal of Finance
- Harvey, C., Liu, Y. & Zhu, H. (2016) — *…and the Cross-Section of Expected Returns* — Review of Financial Studies
- Giglio, S. & Xiu, D. (2021) — *Asset Pricing with Omitted Factors* — Journal of Political Economy
""")

WIKIS["fdb09448-42f7-460d-92b4-503f41cc1ad2"] = ("Deep learning in asset pricing", 2024, """\
# Deep Learning in Asset Pricing

**Source:** Chen, L., Pelger, M. & Zhu, J. (2024). *Management Science* 70(2), 714–750.

## TL;DR
Estimates the **stochastic discount factor (SDF)** with **deep neural networks**, imposing the
no-arbitrage condition that the SDF must price *all* assets — including conditionally, in every
economic state. The design is adversarial (a **GAN-style** "discriminator" hunts for the most
**mispriced** portfolios to form the hardest moment conditions) and uses a recurrent network (**LSTM**)
to summarize macro state dynamics. The resulting nonlinear SDF delivers strong out-of-sample Sharpe
ratios and ranks characteristic importance.

## What it documents (models)
A general, fully nonlinear SDF that uses both firm characteristics and macroeconomic states, with
asset-pricing theory built into the loss function rather than bolted on.

## Method
- **No-arbitrage moment conditions**: the SDF must make pricing errors zero for test-asset returns
  interacted with conditioning instruments.
- A **generative-adversarial** setup: one network learns the SDF weights; an adversary chooses the
  conditioning portfolios that maximize mispricing, so the SDF is trained against its hardest tests.
- An **LSTM** compresses the macro time series into hidden states used as conditioning variables.

## Main findings
- The deep SDF substantially outperforms linear factor models and simpler ML benchmarks
  out-of-sample.
- Both nonlinearity and macro-state conditioning contribute; a ranking of characteristics by
  importance emerges.

## Why it matters
A leading example of theory-guided deep learning in finance — embedding no-arbitrage into a neural SDF
— and a capstone of the ML asset-pricing program alongside IPCA, autoencoders, and SDF shrinkage.

## Limitations and risks
- GAN/RNN training is delicate and computationally heavy; results require careful regularization.
- Interpretability is limited relative to linear/IPCA models.

## Key references
- Chen, L., Pelger, M. & Zhu, J. (2024) — *Deep Learning in Asset Pricing* — Management Science
- Gu, S., Kelly, B. & Xiu, D. (2020) — *Empirical Asset Pricing via Machine Learning* — Review of Financial Studies
- Kozak, S., Nagel, S. & Santosh, S. (2020) — *Shrinking the Cross-Section* — Journal of Financial Economics
""")


def _get(url):
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read())


def _toks(s):
    return {t for t in "".join(c.lower() if c.isalnum() else " " for c in (s or "")).split()
            if len(t) > 2}


def refresh_citation(title):
    """First OpenAlex result whose title closely matches -> citation_count, else None.

    Respects relevance order and gates on token overlap so we don't grab an unrelated
    blockbuster paper that merely shares a few words.
    """
    try:
        q = urllib.parse.quote(title)
        data = _get(f"{OPENALEX}?search={q}&per-page=5&mailto=research@convexpi.ai")
        want = _toks(title)
        for w in data.get("results", []):
            got = _toks(w.get("display_name") or w.get("title") or "")
            if want and len(want & got) / len(want) >= 0.6:
                oa = (w.get("open_access") or {}).get("oa_url")
                return w.get("cited_by_count"), oa
        return None
    except Exception as e:  # noqa: BLE001
        print(f"   openalex error: {e}")
        return None


def patch(pid, fields):
    body = json.dumps(fields).encode()
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
    for pid, (title, year, md) in WIKIS.items():
        cite = refresh_citation(title)
        time.sleep(0.3)
        name = md.splitlines()[0].lstrip("# ")
        fields = {"wiki_markdown": md, "year": year,
                  "wiki_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        if cite and cite[0]:
            fields["citation_count"] = cite[0]
            if cite[1]:
                fields["open_access_url"] = cite[1]
            extra = f"  [{year}, cit={cite[0]}]"
        else:
            extra = f"  [{year}, cit unchanged]"
        print(f"[{'dry' if args.dry_run else 'write'}] {len(md):>5} chars  {name[:50]}{extra}")
        if not args.dry_run:
            patch(pid, fields)
    print(f"\n{len(WIKIS)} wikis " + ("previewed (dry run)." if args.dry_run else "written."))


if __name__ == "__main__":
    main()
