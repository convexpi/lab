# ConvexPi Literature Pipeline

Ports the DoOperator research pipeline to finance papers. Ingests arXiv q-fin
papers, downloads and keeps their PDFs, generates LLM wikis (extracting PDF text
in real time), and pushes them to Supabase + the convexpi/content repo.

## Data layout

```
CONVEXPI_DATA_DIR  (default: /Users/smc77/convexpi-data — outside Dropbox)
├── cache/          # OSAP and other downloaded data files
├── pdf/            # Downloaded arXiv PDFs — source of truth, kept on disk
├── fulltext/       # (optional) pre-extracted text cache, honoured if present
├── wiki/           # Generated markdown wiki files (pushed to Supabase)
└── wiki_index.json # Hash index to skip unchanged wikis
```

Text is extracted from the PDFs **on demand** at wiki-generation time
(PyMuPDF), so there's no bulk extraction step to keep in sync. Every paper is on
arXiv, so each PDF is also viewable at `https://arxiv.org/abs/{arxiv_id}`.

## Env vars

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | `https://xxxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Yes | Service role key (bypasses RLS) |
| `ANTHROPIC_API_KEY` | For wiki gen | Claude models |
| `GEMINI_API_KEY` | Optional | Gemini models |
| `DEEPSEEK_API_KEY` | Optional | DeepSeek models |
| `S2_API_KEY` | Optional | Semantic Scholar (higher rate limits) |
| `CONVEXPI_DATA_DIR` | Optional | Override data root |

## Scripts

### 1. Ingest papers from arXiv

```bash
python pipeline/ingest_finance_papers.py              # all topics
python pipeline/ingest_finance_papers.py --topic momentum --limit 500
python pipeline/ingest_finance_papers.py --dry-run    # preview without writing
```

### 1b. Other ingestion sources

The DB is fed from several complementary discovery sources (all free/open; dedup by DOI; same
finance-relevance gate + topic classifier reused throughout). Every script supports `--dry-run`,
which previews kept counts and touches neither Supabase nor any key.

```bash
python pipeline/seed_osap_papers.py          # canonical anomaly-defining journal papers (OSAP → Crossref + OpenAlex)
python pipeline/ingest_openalex_journals.py  # breadth from top finance/accounting + econ journals (OpenAlex by ISSN)
python pipeline/ingest_ml_venues.py          # AI/ML venues: ICAIF (via DBLP) + NeurIPS/ICML/ICLR/KDD/EMNLP/ACL/AAAI (OpenAlex), finance-gated
python pipeline/ingest_working_papers.py     # working papers: NBER + Fed FEDS/IFDP (OpenAlex); RePEc/NEP stub
python pipeline/expand_citations.py          # citation-graph snowballing from seed papers (Semantic Scholar refs/citations)
```

- **`ingest_ml_venues.py`** — discovers by OpenAlex venue id; general ML venues require a *strong*
  finance term (so RL/CV papers that merely say "option"/"reward" are dropped). ICAIF has no OpenAlex
  venue, so it is pulled from DBLP (`stream:conf/icaif:`) and enriched via OpenAlex by DOI.
- **`ingest_working_papers.py`** — OpenAlex by source id; rows tagged `is_preprint=True`. BIS/ECB/CEPR
  are not OpenAlex sources (left for the RePEc/NEP path, currently stubbed).
- **`expand_citations.py`** — from canonical seeds (or high-quality DB papers), keeps finance-relevant
  references/citations not already present; `source="semanticscholar"`.

### 1c. Curate for finance relevance (run after any ingest)

The per-ingest gate is a loose single-term match, so famous non-finance papers leak in via the
citation graph (e.g. AlphaFold, LIME) and the econ-journal breadth (macro/labor/development papers
from AER/QJE/JPE). They then dominate the library because they carry enormous citation counts. This
pass re-grades the whole corpus with a stricter, journal-class-first classifier and flips off-topic
rows to `curation_status='rejected'` (the site only shows `candidate`/`approved`). **Run it after
every ingest.**

```bash
python pipeline/curate_relevance.py --dry-run   # report rejects, with top-cited samples to sanity-check
python pipeline/curate_relevance.py             # apply: candidate -> rejected for off-topic papers
python pipeline/curate_relevance.py --revive     # also restore rejected rows that now pass
```

Finance + accounting journals and ICAIF/arXiv-q-fin are kept wholesale; econ journals, general ML
venues, and un-journalled citation-graph rows are kept only with a finance signal and no
disqualifying domain. Never touches `approved` rows.

### 2. Download PDFs

```bash
python pipeline/download_pdfs.py                       # all papers missing a PDF
python pipeline/download_pdfs.py --topic momentum
python pipeline/download_pdfs.py --force               # re-download existing
python pipeline/download_pdfs.py --include-oa          # also fetch OA PDFs for DOI-only (non-arXiv) papers via Unpaywall
```

Downloads each paper's arXiv PDF to `CONVEXPI_DATA_DIR/pdf/{arxiv_id}.pdf` and
keeps it. Text is extracted in real time during wiki generation — no separate
extraction step. Optional: wikis generate fine from the abstract alone if you
skip this step.

### 3. Generate wikis

```bash
python pipeline/generate_factor_wiki.py               # all papers without wikis
python pipeline/generate_factor_wiki.py --topic meta --limit 20
python pipeline/generate_factor_wiki.py --model sonnet # use Claude Sonnet
```

Extracts text from each paper's PDF (in `pdf/{arxiv_id}.pdf`) at generation
time, falling back to the abstract when no PDF is present.

### 4. Publish to convexpi/content (and optionally Supabase)

```bash
# Commit and push wikis + index.json to convexpi/content
python pipeline/publish_content.py

# Also patch Supabase papers.wiki_markdown at the same time
python pipeline/publish_content.py --supabase

# Preview changes without committing
python pipeline/publish_content.py --dry-run

# Override the path to your local content repo clone
python pipeline/publish_content.py --content-repo ~/Dropbox/convexpi/content
```

The `publish_content.py` script:
1. Copies changed wiki files from `CONVEXPI_DATA_DIR/wiki/` into the content repo
2. Rebuilds `index.json` with lightweight metadata (title, authors, year, topics)
3. Commits and pushes to `convexpi/content`
4. Optionally patches `papers.wiki_markdown` in Supabase (with `--supabase`)

`import_wikis.py` is also available for Supabase-only updates without touching the content repo.

## Topics

| Topic | arXiv categories | Description |
|---|---|---|
| `momentum` | q-fin.PM, q-fin.ST | Price momentum and trend following |
| `value` | q-fin.PM | Value / book-to-market anomaly |
| `quality` | q-fin.PM | Profitability, accruals, investment |
| `low_volatility` | q-fin.PM | Low-beta / low-vol anomaly |
| `short_term_reversal` | q-fin.ST | Microstructure reversal |
| `size` | q-fin.PM | Size premium |
| `factor_zoo` | econ.GN, q-fin.PM | Replication crisis, multiple testing |
| `market_microstructure` | q-fin.TR | Order flow, market making |
| `machine_learning_finance` | q-fin.PM, q-fin.ST | ML for return prediction |
| `options` | q-fin.PR, q-fin.PM | Options-based signals |
