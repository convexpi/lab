#!/usr/bin/env python3
"""
import_wikis.py — Push locally generated wiki files to Supabase.

Reads CONVEXPI_DATA_DIR/wiki/*.md, compares content hashes against what's
already in the Supabase `papers.wiki_markdown` column, and PATCHes only the
files that are new or changed.

Usage:
    python pipeline/import_wikis.py
    python pipeline/import_wikis.py --dry-run
    python pipeline/import_wikis.py --paper-id <uuid>
    python pipeline/import_wikis.py --force   # re-upload all

Env vars:
    SUPABASE_URL          https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  service role key
    CONVEXPI_DATA_DIR     data root (default: /Users/smc77/convexpi-data)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

DATA_DIR   = Path(os.environ.get("CONVEXPI_DATA_DIR", "/Users/smc77/convexpi-data"))
WIKI_DIR   = DATA_DIR / "wiki"
INDEX_PATH = DATA_DIR / "wiki_import_index.json"

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def _headers() -> dict:
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def load_index() -> dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text())
    return {}


def save_index(index: dict) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2))


def patch_wiki(paper_id: str, wiki_markdown: str, dry_run: bool) -> bool:
    """PATCH wiki_markdown + wiki_generated_at for one paper. Returns True on success."""
    if dry_run:
        print(f"  [DRY RUN] Would update {paper_id} ({len(wiki_markdown)} chars)")
        return True

    url = f"{SUPABASE_URL}/rest/v1/papers"
    params = {"id": f"eq.{paper_id}"}
    payload = {
        "wiki_markdown":    wiki_markdown,
        "wiki_generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    resp = httpx.patch(url, params=params, json=payload, headers=_headers(), timeout=20)
    if resp.status_code not in (200, 204):
        print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
        return False
    return True


def main(args: argparse.Namespace) -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    if not WIKI_DIR.exists():
        print(f"Wiki directory not found: {WIKI_DIR}")
        print("Run generate_factor_wiki.py first.")
        sys.exit(1)

    index = load_index()

    wiki_files = sorted(WIKI_DIR.glob("*.md"))
    if args.paper_id:
        wiki_files = [f for f in wiki_files if f.stem == args.paper_id]
    print(f"Found {len(wiki_files)} wiki files in {WIKI_DIR}")

    updated = skipped = errors = 0
    for wiki_file in wiki_files:
        paper_id = wiki_file.stem
        text = wiki_file.read_text(encoding="utf-8")
        h = content_hash(text)

        if not args.force and index.get(paper_id) == h:
            skipped += 1
            continue

        print(f"  Uploading: {paper_id} ({len(text)} chars)")
        ok = patch_wiki(paper_id, text, dry_run=args.dry_run)
        if ok:
            index[paper_id] = h
            updated += 1
        else:
            errors += 1

    if not args.dry_run:
        save_index(index)

    print(f"\nDone: {updated} updated, {skipped} skipped (no change), {errors} errors.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Push generated wikis to Supabase")
    p.add_argument("--paper-id", help="Import a single wiki by paper UUID")
    p.add_argument("--dry-run",  action="store_true")
    p.add_argument("--force",    action="store_true", help="Re-upload all wikis even if unchanged")
    args = p.parse_args()
    main(args)
