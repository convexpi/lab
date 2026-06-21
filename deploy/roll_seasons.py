"""
roll_seasons.py — Open a fresh monthly competition season and close the prior one.

Run on the 1st of each month (GitHub Action `seasons.yml`). It:
  1. Ends any currently-active `season-*` competition whose slug is not this month's.
  2. Creates this month's public Lab competition `season-YYYY-MM` (if missing),
     seeded with the three reference baselines.

A "season" is a fresh, time-boxed leaderboard that keeps the competition lively;
the permanent boards from seed_open_competitions.py keep running alongside it.
Idempotent: re-running within the same month is a no-op.

Usage:
    NEXT_PUBLIC_SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python deploy/roll_seasons.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from seed_open_competitions import (  # noqa: E402
    BASELINE_USER_ID, ensure_baseline_user, rest_get, rest_update,
    seed_baselines, upsert_cohort,
)


def main() -> None:
    now = datetime.now(timezone.utc)
    slug = f"season-{now:%Y-%m}"
    name = f"Season — {now:%B %Y}"

    ensure_baseline_user()

    # 1. End prior active seasons (everything matching season-* except this month's).
    active = rest_get("cohorts",
                      "type=eq.competition&status=eq.active&slug=like.season-*&select=slug")
    for c in active:
        if c["slug"] != slug:
            rest_update("cohorts", f"slug=eq.{c['slug']}", {"status": "ended"})
            print(f"Ended prior season: {c['slug']}")

    # 2. Open this month's season.
    cohort_id = upsert_cohort({
        "slug": slug,
        "name": name,
        "description": (f"{name}: a fresh monthly leaderboard. Submit any strategy; ranked out of "
                        "sample against the reference baselines. Resets next month."),
        "type": "competition", "visibility": "public", "owner_id": BASELINE_USER_ID,
        "status": "active", "start_date": now.isoformat(), "market_config": {},
    })
    seed_baselines(cohort_id, slug)

    print(f"\nDone. Active season: {slug}  →  /compete/{slug}/leaderboard")


if __name__ == "__main__":
    main()
