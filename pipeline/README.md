# ConvexPi Literature Pipeline

Ports the DoOperator research pipeline to finance papers. Ingests arXiv q-fin
papers, optionally downloads full text, generates LLM wikis, and pushes them
to Supabase.

## Data layout

```
CONVEXPI_DATA_DIR  (default: /Users/smc77/convexpi-data — outside Dropbox)
├── cache/          # OSAP and other downloaded data files
├── fulltext/       # Plain-text extractions of downloaded PDFs
├── pdf/            # Downloaded PDFs (large — keep off Dropbox)
├── wiki/           # Generated markdown wiki files (pushed to Supabase)
└── wiki_index.json # Hash index to skip unchanged wikis
```

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

### 2. Generate wikis

```bash
python pipeline/generate_factor_wiki.py               # all papers without wikis
python pipeline/generate_factor_wiki.py --topic meta --limit 20
python pipeline/generate_factor_wiki.py --model sonnet # use Claude Sonnet
```

### 3. Publish to convexpi/content (and optionally Supabase)

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
