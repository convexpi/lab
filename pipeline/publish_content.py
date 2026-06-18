#!/usr/bin/env python3
"""
publish_content.py — Commit generated wikis to convexpi/content and push.

Reads wiki markdown files from CONVEXPI_DATA_DIR/wiki/, copies new/changed
ones into the content repo, updates index.json, commits, and pushes.
Optionally also patches Supabase papers.wiki_markdown (--supabase flag).

Usage:
    python pipeline/publish_content.py
    python pipeline/publish_content.py --dry-run
    python pipeline/publish_content.py --supabase          # also push to Supabase
    python pipeline/publish_content.py --content-repo /path/to/content

Env vars:
    CONVEXPI_DATA_DIR     data root (default: /Users/smc77/convexpi-data)
    SUPABASE_URL          required only with --supabase
    SUPABASE_SERVICE_KEY  required only with --supabase
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DATA_DIR       = Path(os.environ.get("CONVEXPI_DATA_DIR", "/Users/smc77/convexpi-data"))
WIKI_SRC_DIR   = DATA_DIR / "wiki"

# Default content repo — can be overridden with --content-repo
DEFAULT_CONTENT_REPO = Path(__file__).parent.parent.parent / "content"

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

INDEX_PATH_NAME = "index.json"   # relative to content repo root


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  git error: {result.stderr.strip()}")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result.stdout.strip()


def git_push(content_repo: Path, dry_run: bool, message: str) -> bool:
    """Stage all changes, commit, and push. Returns True if anything was committed."""
    _run(["git", "add", "-A"], content_repo)
    status = _run(["git", "status", "--porcelain"], content_repo)
    if not status:
        print("  No changes to commit.")
        return False
    if dry_run:
        print(f"  [DRY RUN] Would commit:\n{status}")
        return False
    _run(["git", "commit", "-m", message], content_repo)
    _run(["git", "push", "origin", "main"], content_repo)
    print(f"  Committed and pushed: {message}")
    return True


# ---------------------------------------------------------------------------
# Supabase patch (optional)
# ---------------------------------------------------------------------------

def _supabase_headers() -> dict:
    return {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }


def patch_supabase_wiki(paper_id: str, wiki_markdown: str) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/papers"
    payload = {
        "wiki_markdown":    wiki_markdown,
        "wiki_generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    resp = httpx.patch(
        url, params={"id": f"eq.{paper_id}"},
        json=payload, headers=_supabase_headers(), timeout=20,
    )
    if resp.status_code not in (200, 204):
        print(f"    Supabase error {resp.status_code}: {resp.text[:200]}")
        return False
    return True


# ---------------------------------------------------------------------------
# Fetch paper metadata from Supabase (to build index.json)
# ---------------------------------------------------------------------------

def fetch_paper_meta(paper_ids: list[str]) -> dict[str, dict]:
    """Return {paper_id: {title, authors, year, topics, ...}} from Supabase."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return {}
    url = f"{SUPABASE_URL}/rest/v1/papers"
    headers = {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    # Fetch in batches of 50
    result: dict[str, dict] = {}
    for i in range(0, len(paper_ids), 50):
        batch = paper_ids[i : i + 50]
        ids_str = "(" + ",".join(batch) + ")"
        params = {
            "select": "id,title,authors,year,journal,doi,arxiv_id,topics,is_oos_paper",
            "id":     f"in.{ids_str}",
        }
        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=20)
            resp.raise_for_status()
            for row in resp.json():
                result[row["id"]] = row
        except Exception as exc:
            print(f"  Warning: failed to fetch metadata for batch: {exc}")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(args: argparse.Namespace) -> None:
    content_repo = Path(args.content_repo).expanduser().resolve()
    wiki_dst_dir = content_repo / "wikis"
    wiki_dst_dir.mkdir(parents=True, exist_ok=True)

    if not WIKI_SRC_DIR.exists():
        print(f"No wiki source directory: {WIKI_SRC_DIR}")
        print("Run generate_factor_wiki.py first.")
        sys.exit(1)

    # Load existing index
    index_path = content_repo / INDEX_PATH_NAME
    existing_index: dict = {}
    if index_path.exists():
        data = json.loads(index_path.read_text())
        for entry in data.get("wikis", []):
            existing_index[entry["id"]] = entry

    # Scan source wikis
    src_files = sorted(WIKI_SRC_DIR.glob("*.md"))
    print(f"Found {len(src_files)} wiki files in {WIKI_SRC_DIR}")

    changed_ids: list[str] = []
    all_ids: list[str] = []

    for src in src_files:
        paper_id = src.stem
        all_ids.append(paper_id)
        wiki_text = src.read_text(encoding="utf-8")
        dst = wiki_dst_dir / src.name
        h = content_hash(wiki_text)

        if dst.exists() and content_hash(dst.read_text(encoding="utf-8")) == h:
            continue  # unchanged

        if args.dry_run:
            print(f"  [DRY RUN] Would copy: {paper_id}")
        else:
            shutil.copy2(src, dst)
            print(f"  Copied: {paper_id} ({len(wiki_text)} chars)")

        changed_ids.append(paper_id)

        if args.supabase and not args.dry_run:
            ok = patch_supabase_wiki(paper_id, wiki_text)
            if ok:
                print(f"    → Supabase updated")

    if not changed_ids:
        print("Nothing changed.")
        return

    # Fetch metadata for all wikis to build/update index.json
    print(f"Fetching metadata for {len(all_ids)} papers…")
    meta_by_id = fetch_paper_meta(all_ids)

    now = datetime.now(tz=timezone.utc).isoformat()
    index_entries: list[dict] = []
    for paper_id in all_ids:
        meta = meta_by_id.get(paper_id, {})
        entry = existing_index.get(paper_id, {"id": paper_id})
        entry.update({
            "id":         paper_id,
            "title":      meta.get("title", entry.get("title", "")),
            "authors":    meta.get("authors", entry.get("authors", [])),
            "year":       meta.get("year",    entry.get("year")),
            "journal":    meta.get("journal", entry.get("journal")),
            "doi":        meta.get("doi",     entry.get("doi")),
            "arxiv_id":   meta.get("arxiv_id", entry.get("arxiv_id")),
            "topics":     meta.get("topics",  entry.get("topics", [])),
            "is_oos_paper": meta.get("is_oos_paper", entry.get("is_oos_paper", False)),
            "updated_at": now,
        })
        index_entries.append(entry)

    # Sort by year desc, then title
    index_entries.sort(key=lambda e: (-(e.get("year") or 0), e.get("title", "")))

    new_index = {
        "updated_at": now,
        "count":      len(index_entries),
        "wikis":      index_entries,
    }

    if args.dry_run:
        print(f"  [DRY RUN] Would update index.json ({len(index_entries)} entries)")
    else:
        index_path.write_text(json.dumps(new_index, indent=2, ensure_ascii=False))
        print(f"Updated index.json ({len(index_entries)} entries)")

    # Commit and push
    n = len(changed_ids)
    commit_msg = (
        f"content: add {n} wiki{'s' if n != 1 else ''} "
        f"({datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')})"
    )
    git_push(content_repo, dry_run=args.dry_run, message=commit_msg)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Publish wikis to convexpi/content repo")
    p.add_argument(
        "--content-repo",
        default=str(DEFAULT_CONTENT_REPO),
        help=f"Path to local convexpi/content clone (default: {DEFAULT_CONTENT_REPO})",
    )
    p.add_argument("--dry-run",  action="store_true")
    p.add_argument(
        "--supabase", action="store_true",
        help="Also patch papers.wiki_markdown in Supabase",
    )
    args = p.parse_args()
    main(args)
