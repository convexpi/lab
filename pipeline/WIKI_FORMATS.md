# Paper-wiki formats & the grounding pass

Wikis are auto-generated summaries of finance papers, grounded in the paper (full
text when we have it, else abstract + metadata). **Not every paper is an anomaly.**
Forcing the cross-sectional in-sample/out-of-sample template ("predictor →
construction → IS/OOS evidence → OSAP name") onto a volatility model, an option
pricer, or an econometric method produces nonsense. Pick the format that fits.

## 0. Relevance gate

Only write a wiki if the paper is in scope for the platform: empirical asset
pricing, factor/anomaly research, market microstructure, derivatives & volatility,
portfolio construction, and the econometric/ML **methods** used in those. If a
paper is off-topic (a generic ML paper with no finance application, an unrelated
macro paper), skip the wiki (leave `wiki_markdown` null; optionally mark
`curation_status='rejected'`). When borderline, prefer a short `concept` wiki over
forcing detail.

## 1. Choose the format

| Format | Use when the paper is… | Examples |
|---|---|---|
| **anomaly** | a cross-sectional return predictor / factor / premium with a sortable signal | momentum, value, accruals, BAB, profitability |
| **model** | a model of a process (esp. volatility / return dynamics) | ARCH/GARCH/EGARCH, stochastic vol, realized vol |
| **pricing** | a derivative or asset **valuation** model/formula | Black–Scholes, LSM American options, affine term structure |
| **theory** | an equilibrium / asset-pricing **theory** | CAPM, ICAPM, consumption-CAPM, rare disasters, long-run risk, habit |
| **method** | an econometric / statistical / portfolio-construction **method** | Newey–West, GMM, Fama–MacBeth, panel methods, Markowitz, Black–Litterman, deflated Sharpe, ML asset pricing |
| **concept** | a survey, conceptual, or efficiency/replication paper | EMH, factor zoo, McLean–Pontiff, excess volatility |

Selection heuristics (topic tags / title / abstract keywords):
- volatility, ARCH/GARCH, stochastic/realized volatility → **model**
- option, derivative, term structure, valuation formula → **pricing**
- equilibrium, utility, consumption, disaster, CAPM, risk premium theory → **theory**
- estimator, covariance matrix, standard errors, GMM, optimization, Sharpe-ratio statistic, ML estimator → **method**
- a cross-sectional predictor formed by sorting → **anomaly**
- review / efficiency / "does X survive" / multiple testing → **concept**

## 2. Section skeletons

All formats start with `# Title`, a `**Source:** Author (Year) · Journal · DOI` line,
and a `## TL;DR`, and end with `## Key references` + the provenance footer (§4).

- **anomaly** — `## What anomaly it documents` (Predictor / Direction / Shape / OSAP predictor) · `## How to construct it` · `## Evidence and replication` (IS/OOS table) · `## Why it might work` · `## Limitations and risks`
- **model** — `## What it models` · `## Specification` (the equation) · `## Estimation` · `## What it captures` (stylized facts: vol clustering, leverage effect, fat tails…) · `## Use & extensions` · `## Limitations`
- **pricing** — `## What it prices` · `## Setup & assumptions` · `## Key result` (the formula/result) · `## Inputs & implementation` · `## Limitations`
- **theory** — `## The question` · `## The model` · `## Key predictions` · `## Empirical status` · `## Limitations`
- **method** — `## Problem it solves` · `## The method` · `## Assumptions & inputs` · `## How to use it` · `## Limitations & pitfalls`
- **concept** — `## The idea` · `## Evidence` · `## Why it matters` · `## Caveats`

## 3. The grounding / verification / enhancement pass

For each paper that has full text on disk (`~/convexpi-data/pdf/<id>.pdf`, extract in
`/tmp/ft/<id>.txt`):

1. **Pick the format** (§1). If the existing wiki is in the *wrong* format
   (e.g. the anomaly template on a volatility model), regenerate it in the right one.
2. **Verify** every specific claim against the full text — sample period, magnitudes,
   t-stats, equations, sign/direction. Fix anything wrong.
3. **Enhance**: add accurate specifics the abstract-only version lacked — the key
   equation, the exact sample, headline numbers *with t-stats* — grounded in the text.
4. Keep it tight; don't pad.
5. **Provenance footer** (§4) reflecting the grounding.

## 4. Provenance footer (always last line, after a `---`)

- full text: `*Provenance: verified/generated from the paper's full text.*`
- abstract only: `*Provenance: generated from the paper's abstract and metadata, not full text; sample periods and replication notes are indicative — verify against the source.*`

## 5. Don't

- Don't put IS/OOS "Evidence and replication" or an "OSAP predictor" line on a
  non-anomaly paper.
- Don't invent numbers — only quote figures that appear in the text.
- Don't generate anomaly-construction sections for methods / models / theory.
