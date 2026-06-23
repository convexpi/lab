"""
seed_contributions.py — populate the community reputation ledger (public.contributions).

Idempotent (upsert by source_key). Awards points for the contributions that already exist:
  - replications merged into convexpi/replications  (+50; +10 "Ghostbuster" if the factor came
    out dormant, i.e. you found a dead anomaly)
  - paper wikis authored                            (+10 each)
  - graded strategy submissions                     (+2; +15 "Survivor" if it posted a positive OOS)

As the community contributes, the same script (or the grader / a CI hook) keeps the ledger current.

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/seed_contributions.py [--dry-run]
"""
from __future__ import annotations
import argparse, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
RESULTS = "https://raw.githubusercontent.com/convexpi/replications/main/results.json"

POINTS = {"replication": 50, "ghost": 10, "wiki": 10, "submission": 2, "oos_survivor": 15}
# Map replication "authors" display names to GitHub handles. Extend as contributors join.
GH = {"convexpi": "convexpi"}


def _get(path):
    req = urllib.request.Request(f"{URL}/rest/v1/{path}",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"})
    return json.loads(urllib.request.urlopen(req).read())


def _fetch_json(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def gather() -> list[dict]:
    rows: list[dict] = []

    # 1) Replications (+ Ghostbuster for dead ones)
    try:
        for r in _fetch_json(RESULTS):
            authors = r.get("authors") or ["ConvexPi"]
            for a in authors:
                gh = GH.get(a.strip().lower(), a.strip().lower().replace(" ", "-"))
                rows.append(dict(kind="replication", points=POINTS["replication"], github_username=gh,
                                 ref=r["name"], detail=f"Replication: {r['title']}",
                                 source_key=f"replication:{r['name']}:{gh}"))
                if r.get("verdict") in ("dormant", "decayed"):
                    rows.append(dict(kind="ghost", points=POINTS["ghost"], github_username=gh,
                                     ref=r["name"], detail=f"Found a fading factor: {r['title']} ({r['verdict']})",
                                     source_key=f"ghost:{r['name']}:{gh}"))
    except Exception as exc:
        print(f"  (replications skipped: {exc})")

    # 2) Paper wikis (authored by ConvexPi in this seed)
    for off in range(0, 100000, 1000):
        batch = _get(f"papers?select=id,title&wiki_generated_at=not.is.null&curation_status=in.(candidate,approved)&limit=1000&offset={off}")
        for p in batch:
            rows.append(dict(kind="wiki", points=POINTS["wiki"], github_username="convexpi",
                             ref=p["id"], detail=f"Wiki: {p['title'][:80]}", source_key=f"wiki:{p['id']}"))
        if len(batch) < 1000:
            break

    # 3) Graded submissions (+ Survivor for positive OOS) -> real platform users
    reports = _get("grade_reports?select=submission_id,oos_sharpe,submissions(id,user_id,strategy_name)&limit=1000")
    for g in reports:
        sub = g.get("submissions") or {}
        uid = sub.get("user_id")
        if not uid:
            continue
        sid = sub.get("id") or g["submission_id"]
        name = sub.get("strategy_name") or "strategy"
        rows.append(dict(kind="submission", points=POINTS["submission"], user_id=uid,
                         ref=str(sid), detail=f"Submission graded: {name}", source_key=f"submission:{sid}"))
        if (g.get("oos_sharpe") or 0) > 0:
            rows.append(dict(kind="oos_survivor", points=POINTS["oos_survivor"], user_id=uid,
                             ref=str(sid), detail=f"Survived out-of-sample: {name}", source_key=f"survivor:{sid}"))
    return rows


def upsert(rows):
    # PostgREST bulk upsert on the unique source_key; every object must have the same keys.
    cols = ["kind", "points", "github_username", "user_id", "ref", "detail", "source_key"]
    norm = [{c: r.get(c) for c in cols} for r in rows]
    body = json.dumps(norm).encode()
    req = urllib.request.Request(f"{URL}/rest/v1/contributions?on_conflict=source_key", data=body, method="POST",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"})
    urllib.request.urlopen(req).read()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not URL or not KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    rows = gather()
    by_kind: dict[str, int] = {}
    pts: dict[str, int] = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        who = r.get("github_username") or r.get("user_id")
        pts[who] = pts.get(who, 0) + r["points"]
    print("contributions by kind:", by_kind)
    print("points by contributor:", {k: v for k, v in sorted(pts.items(), key=lambda x: -x[1])})
    if args.dry_run:
        print(f"\n(dry run — {len(rows)} rows not written)")
        return
    # upsert in chunks
    for i in range(0, len(rows), 500):
        upsert(rows[i:i + 500])
    print(f"\nupserted {len(rows)} contributions")


if __name__ == "__main__":
    main()
