"""
render_post.py — execute a community post notebook and render it to a safe, embeddable HTML fragment.

This is the heart of the project showcase build step. It runs inside a sandboxed worker (see
.github/workflows/build_post.yml), takes a Jupyter notebook, and produces:

  out/rendered.html  — a SANITIZED HTML fragment (no <script>, no inline styles) for embedding
  out/meta.json      — extracted front-matter: {title, summary, tags, has_strategy}

Front-matter convention: the notebook's first markdown cell starts with a YAML-ish block:

    ---
    title: My Momentum Strategy
    summary: A one-line description shown in the gallery.
    tags: [momentum, equities]
    ---
    # then the narrative...

Usage:
    python render_post.py path/to/notebook.ipynb --out out/           # execute, then render
    python render_post.py path/to/notebook.ipynb --out out/ --no-execute   # render as-is (testing)
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys

import nbformat
from nbconvert import HTMLExporter
import bleach

CELL_TIMEOUT = 120          # seconds per cell — a hard cap on runaway code
STRATEGY_RE = re.compile(r"class\s+MyStrategy\b")

# Conservative allow-list. Notebook outputs are arbitrary HTML, so we strip everything not here.
ALLOWED_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr", "div", "span", "pre", "code",
    "blockquote", "em", "strong", "b", "i", "u", "s", "sub", "sup", "a", "img",
    "ul", "ol", "li", "dl", "dt", "dd", "table", "thead", "tbody", "tfoot", "tr", "th", "td",
]
ALLOWED_ATTRS = {
    "*": ["class"],
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["colspan", "rowspan"], "th": ["colspan", "rowspan"],
}
# Allow data: URIs so nbconvert's inline figures (base64 PNGs) survive; http(s) for links.
ALLOWED_PROTOCOLS = ["http", "https", "data", "mailto"]


def parse_frontmatter(nb) -> tuple[dict, object]:
    """Pull title/summary/tags from a leading `--- ... ---` block in the first markdown cell,
    and strip that block from the rendered body."""
    meta = {"title": None, "summary": None, "tags": []}
    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue
        m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n?(.*)", cell.source, re.DOTALL)
        if not m:
            break
        block, rest = m.group(1), m.group(2)
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key, val = key.strip().lower(), val.strip()
            if key == "tags":
                meta["tags"] = [t.strip() for t in val.strip("[]").split(",") if t.strip()]
            elif key in ("title", "summary"):
                meta[key] = val.strip().strip('"\'')
        cell.source = rest      # drop the front-matter from the visible body
        break
    return meta, nb


def execute(nb, path: str):
    from nbclient import NotebookClient
    client = NotebookClient(nb, timeout=CELL_TIMEOUT, kernel_name="python3",
                            resources={"metadata": {"path": os.path.dirname(path) or "."}})
    client.execute()
    return nb


def render(nb) -> str:
    exporter = HTMLExporter(template_name="basic")   # body fragment, not a full HTML page
    body, _ = exporter.from_notebook_node(nb)
    return body


def sanitize(html: str) -> str:
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
                        protocols=ALLOWED_PROTOCOLS, strip=True, strip_comments=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("notebook")
    ap.add_argument("--out", default="out")
    ap.add_argument("--no-execute", action="store_true", help="skip execution (render as-is)")
    args = ap.parse_args()

    nb = nbformat.read(args.notebook, as_version=4)
    raw_src = "\n".join(c.source for c in nb.cells if c.cell_type == "code")
    has_strategy = bool(STRATEGY_RE.search(raw_src))

    if not args.no_execute:
        execute(nb, args.notebook)

    meta, nb = parse_frontmatter(nb)
    meta["has_strategy"] = has_strategy
    if not meta["title"]:
        # Fall back to the first H1 in any markdown cell.
        for c in nb.cells:
            if c.cell_type == "markdown":
                h = re.search(r"^#\s+(.+)$", c.source, re.MULTILINE)
                if h:
                    meta["title"] = h.group(1).strip()
                    break
    meta["title"] = meta["title"] or "Untitled post"

    html = sanitize(render(nb))

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "rendered.html"), "w") as f:
        f.write(html)
    with open(os.path.join(args.out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"rendered: {len(html):,} chars  title={meta['title']!r}  "
          f"tags={meta['tags']}  has_strategy={has_strategy}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                                # noqa: BLE001 — surface a clean build error
        print(f"render_post failed: {e}", file=sys.stderr)
        sys.exit(1)
