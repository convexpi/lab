#!/usr/bin/env python3
"""
generate_factor_wiki.py — Generate structured wiki pages for finance papers.

Reads papers without wikis from the Supabase `papers` table, generates a
structured markdown wiki per paper using Claude (or another LLM), and
writes output to CONVEXPI_DATA_DIR/wiki/{paper_id}.md.

Run import_wikis.py afterwards to push the generated files back to Supabase.

Adapted from DoOperator's generate_wiki.py. Key change: finance-specific
wiki prompt covering factor construction, IS/OOS evidence, and trading rules
rather than the self-experiment / causal-methods format.

Usage:
    python pipeline/generate_factor_wiki.py
    python pipeline/generate_factor_wiki.py --topic momentum
    python pipeline/generate_factor_wiki.py --paper-id <uuid>
    python pipeline/generate_factor_wiki.py --limit 20
    python pipeline/generate_factor_wiki.py --force          # regenerate existing
    python pipeline/generate_factor_wiki.py --model haiku    # override model

Model shortcuts:
    haiku    → claude-haiku-4-5-20251001   (~$0.005/wiki, default)
    sonnet   → claude-sonnet-4-6           (~$0.025/wiki)
    opus     → claude-opus-4-8             (~$0.10/wiki)
    gemini   → gemini-2.0-flash            (~$0.001/wiki)
    deepseek → deepseek-chat               (~$0.002/wiki)

Env vars:
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key
    ANTHROPIC_API_KEY     for Claude models (default model)
    GEMINI_API_KEY        for Gemini models
    DEEPSEEK_API_KEY      for DeepSeek models
    CONVEXPI_DATA_DIR     data root (default: /Users/smc77/convexpi-data)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR  = Path(os.environ.get("CONVEXPI_DATA_DIR", "/Users/smc77/convexpi-data"))
WIKI_DIR  = DATA_DIR / "wiki"
INDEX_PATH = DATA_DIR / "wiki_index.json"

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# ---------------------------------------------------------------------------
# Finance factor wiki prompt
# ---------------------------------------------------------------------------

FACTOR_WIKI_PROMPT = """\
You are building a structured research wiki for ConvexPi, a platform where students \
and researchers study quantitative finance through the experimental method. \
Given the full text (or abstract) of a finance paper, write a wiki page \
in the exact format below.

Rules:
- Write for a technically literate reader: finance PhD student, quant researcher, \
  or sophisticated practitioner. Assume knowledge of Sharpe ratios, factor models, \
  long-short portfolios, and regression analysis.
- Be specific about numbers. Never say "significantly positive" without giving the \
  Sharpe ratio, t-statistic, or annualised return.
- Distinguish clearly between in-sample (IS) and out-of-sample (OOS) evidence. \
  If the paper only reports IS results, flag this explicitly.
- The "How to construct it" section must be actionable: exact sorting variable, \
  portfolio formation date, rebalancing frequency, long/short legs, weighting scheme.
- The "Evidence and replication" section must cite actual numbers from the paper \
  (IS Sharpe, OOS Sharpe, t-stat, sample period) and note whether the anomaly \
  appears in the OSAP / Chen-Zimmermann database.
- Use plain markdown only. No HTML. Tables are allowed (they help present IS/OOS numbers).
- Complete ALL sections. Target ~2,000 words total. Never stop mid-section.

---

# {TITLE}

**Source:** {SOURCE_LINE}

## TL;DR
[One or two sentences: what anomaly or factor does this paper document, and what is \
the claimed edge? Include the headline Sharpe ratio or alpha if available.]

## What anomaly it documents
[Plain-English description of the factor or anomaly. What variable predicts returns? \
In which direction? Over what horizon? Why might it exist (risk or mispricing)?]

## How to construct it
[Exact construction rules a practitioner would need to replicate:]
- Sorting variable and data source
- Universe (all US stocks / NYSE / large-cap / etc.)
- Portfolio formation date (fiscal-year end + 6-month lag, etc.)
- Rebalancing frequency (monthly / annually / at announcements)
- Long leg / short leg (top / bottom quintile, decile, etc.)
- Weighting (equal-weighted / value-weighted)
- Any filters (price > $5, market cap > NYSE 20th percentile, etc.)

## Evidence and replication
Provide a table of IS vs OOS evidence:

| Period | Sharpe | Ann. Return | T-stat | Source |
|--------|--------|-------------|--------|--------|
| IS (original sample) | | | | this paper |
| OOS (post-publication) | | | | (if available) |
| OSAP replication | | | | Chen & Zimmermann 2022 |

Note if the anomaly is classified as 1_clear / 2_likely / 4_not in the OSAP dataset.
Cite the McLean-Pontiff (2016) decay estimate if known.

## Why it might work
[Economic explanation(s): risk-based (compensation for a systematic risk), \
behavioural (investor under/over-reaction), structural (limits to arbitrage). \
Present both sides of the debate if contested.]

## Limitations and risks
[What weakens this strategy in practice:]
- Transaction costs and turnover
- Capacity constraints (how many $B before the edge disappears?)
- Crash risk or tail events
- Data requirements (licensed data, point-in-time issues)
- Publication / overfitting risk: was the sample period mined?

## Key references
[3–7 foundational papers. Format each as: Author (year) — *Title* — Journal — DOI if known.]

---

Now write the wiki page for the paper below.

TITLE: {TITLE}
AUTHORS: {AUTHORS}
JOURNAL: {JOURNAL}
YEAR: {YEAR}
TOPICS: {TOPICS}

FULL TEXT / ABSTRACT:
{FULL_TEXT}
"""

# Prompt for meta / replication papers (factor zoo, multiple testing, etc.)
META_WIKI_PROMPT = """\
You are building a structured research wiki for ConvexPi, a platform where students \
and researchers study quantitative finance through the experimental method. \
This paper is a meta-study, survey, or methodological paper about the \
replication crisis, factor proliferation, or multiple testing in finance. \
Write a wiki page in the exact format below.

Rules:
- Write for a technically literate reader. Be precise about statistical claims.
- Be specific about numbers (decay rates, false discovery rates, sample sizes).
- Use plain markdown only. Tables are allowed and encouraged.
- Complete ALL sections. Target ~2,000 words total. Never stop mid-section.

---

# {TITLE}

**Source:** {SOURCE_LINE}

## TL;DR
[One sentence: the main finding and its implication for practitioners.]

## The problem it addresses
[What pathology in the empirical finance literature does this paper diagnose? \
P-hacking, data mining, overfitting, spurious factor discovery?]

## Main findings
[Bullet-point results with actual numbers. Include effect sizes, survival rates, \
false discovery rates, or decay estimates. Distinguish primary from secondary claims.]

## Methodology
[How do the authors reach their conclusions? What data, what tests, what identification strategy?]

## Implications for factor investing
[What should practitioners do differently based on this paper? \
How should OOS evaluation be set up? What multiple-testing corrections are recommended?]

## Key references
[3–7 foundational papers. Format: Author (year) — *Title* — Journal — DOI if known.]

---

Now write the wiki page for the paper below.

TITLE: {TITLE}
AUTHORS: {AUTHORS}
JOURNAL: {JOURNAL}
YEAR: {YEAR}
TOPICS: {TOPICS}

FULL TEXT / ABSTRACT:
{FULL_TEXT}
"""

_META_TOPICS = frozenset({"meta", "replication", "factor_zoo"})


def _pick_prompt(topics: list[str]) -> str:
    if set(topics) & _META_TOPICS:
        return META_WIKI_PROMPT
    return FACTOR_WIKI_PROMPT


# ---------------------------------------------------------------------------
# Wiki index (tracks hash → skip regeneration unless --force)
# ---------------------------------------------------------------------------

def load_index() -> dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text())
    return {}


def save_index(index: dict) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2))


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Model dispatch
# ---------------------------------------------------------------------------

MODEL_MAP = {
    "haiku":    ("anthropic", "claude-haiku-4-5-20251001"),
    "sonnet":   ("anthropic", "claude-sonnet-4-6"),
    "opus":     ("anthropic", "claude-opus-4-8"),
    "gemini":   ("gemini",    "gemini-2.0-flash"),
    "deepseek": ("deepseek",  "deepseek-chat"),
}


def generate_wiki(paper: dict, full_text: str, model: str = "haiku") -> str:
    """Call the LLM and return the generated wiki markdown."""
    provider, model_id = MODEL_MAP.get(model, ("anthropic", model))

    authors = ", ".join(
        (a.get("name") or a) if isinstance(a, dict) else a
        for a in (paper.get("authors") or [])
    )[:200]
    topics = ", ".join(paper.get("topics") or [])
    source_line = f"{paper.get('journal', 'arXiv')} {paper.get('year', '')}"
    if paper.get("doi"):
        source_line += f" · doi:{paper['doi']}"
    elif paper.get("arxiv_id"):
        source_line += f" · arXiv:{paper['arxiv_id']}"

    prompt = _pick_prompt(paper.get("topics") or []).format(
        TITLE=paper["title"],
        SOURCE_LINE=source_line,
        AUTHORS=authors,
        JOURNAL=paper.get("journal") or "arXiv preprint",
        YEAR=paper.get("year") or "n/a",
        TOPICS=topics or "finance",
        FULL_TEXT=full_text[:12_000],  # keep within context limits
    )

    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model=model_id,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        m = genai.GenerativeModel(model_id)
        resp = m.generate_content(prompt)
        return resp.text

    if provider == "deepseek":
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com",
        )
        resp = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
        return resp.choices[0].message.content

    raise ValueError(f"Unknown provider: {provider}")


# ---------------------------------------------------------------------------
# Supabase fetch
# ---------------------------------------------------------------------------

def _headers() -> dict:
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }


async def fetch_papers_without_wiki(
    topic: str | None,
    paper_id: str | None,
    limit: int,
    force: bool,
) -> list[dict]:
    """Fetch papers from Supabase that don't yet have a wiki (or force=True)."""
    url = f"{SUPABASE_URL}/rest/v1/papers"
    params: dict = {"select": "id,title,authors,year,journal,doi,arxiv_id,abstract,topics,open_access_url"}

    if paper_id:
        params["id"] = f"eq.{paper_id}"
    else:
        if not force:
            params["wiki_markdown"] = "is.null"
        params["order"]  = "quality_score.desc"
        params["limit"]  = str(limit)
        if topic:
            params["topics"] = f"cs.[\"{topic}\"]"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=_headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Load full text from disk (written by fetch_full_text.py) or fall back to abstract
# ---------------------------------------------------------------------------

def load_full_text(paper: dict) -> str:
    paper_id = paper["id"]
    # Try saved full-text file first
    for ext in (".txt", ".md"):
        p = DATA_DIR / "fulltext" / f"{paper_id}{ext}"
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")[:20_000]
    # Fall back to abstract
    return paper.get("abstract") or ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    index = load_index()

    papers = await fetch_papers_without_wiki(
        topic=args.topic,
        paper_id=args.paper_id,
        limit=args.limit,
        force=args.force,
    )
    print(f"Found {len(papers)} papers to process")

    for i, paper in enumerate(papers, 1):
        paper_id = paper["id"]
        out_path = WIKI_DIR / f"{paper_id}.md"

        full_text = load_full_text(paper)
        if not full_text:
            print(f"  [{i}/{len(papers)}] SKIP (no text): {paper['title'][:60]}")
            continue

        text_hash = content_hash(full_text + args.model)
        if not args.force and index.get(paper_id) == text_hash and out_path.exists():
            print(f"  [{i}/{len(papers)}] CACHED: {paper['title'][:60]}")
            continue

        print(f"  [{i}/{len(papers)}] Generating ({args.model}): {paper['title'][:60]}")
        try:
            wiki = generate_wiki(paper, full_text, model=args.model)
        except Exception as exc:
            print(f"    ERROR: {exc}")
            continue

        out_path.write_text(wiki, encoding="utf-8")
        index[paper_id] = text_hash
        save_index(index)
        print(f"    → {out_path} ({len(wiki)} chars)")

        time.sleep(0.5)  # avoid hammering the API

    print(f"\nDone. Wikis saved to {WIKI_DIR}")
    print("Run `python pipeline/import_wikis.py` to push them to Supabase.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate finance paper wikis")
    p.add_argument("--topic",     help="Filter to papers with this topic tag")
    p.add_argument("--paper-id",  help="Generate wiki for a single paper UUID")
    p.add_argument("--limit",     type=int, default=50)
    p.add_argument("--model",     default="haiku", choices=list(MODEL_MAP),
                   help="LLM to use (default: haiku)")
    p.add_argument("--force",     action="store_true", help="Regenerate existing wikis")
    args = p.parse_args()
    asyncio.run(main(args))
