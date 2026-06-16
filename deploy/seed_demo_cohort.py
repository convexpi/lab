"""
Seed a public demo competition cohort with baseline submission rows.

Usage:
    NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co \
    SUPABASE_SERVICE_KEY=eyJ... \
    python deploy/seed_demo_cohort.py

The cohort slug is 'demo-fall-2026'. Running this script twice is safe —
it checks for an existing cohort and existing baselines before inserting.

Baseline rows use a synthetic user_id so they never conflict with real users.
The grade_reports are hardcoded to represent equal weight, naive momentum,
and random noise strategies as permanent reference points on the leaderboard.
"""
import os
import sys
import uuid
from datetime import datetime, timezone

try:
    from supabase import create_client
except ImportError:
    sys.exit("Install supabase-py: pip install supabase")

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

DEMO_SLUG = "demo-fall-2026"
DEMO_NAME = "Demo Competition — Fall 2026"
DEMO_DESC = (
    "The always-open public competition. Submit any strategy from the missions "
    "and see how it ranks against reference baselines and other participants."
)

# Deterministic IDs so re-running is idempotent
BASELINE_USER_ID = "00000000-0000-0000-0000-000000000001"  # synthetic baseline user

BASELINES = [
    {
        "strategy_name": "Equal Weight",
        "sub_id": "10000000-0000-0000-0000-000000000001",
        "report": {
            "is_sharpe": 0.08,
            "oos_sharpe": 0.10,
            "overfitting_ratio": 1.00,
            "is_max_dd": -11.2,
            "oos_max_dd": -12.4,
            "is_annual_return": 1.1,
            "oos_annual_return": 0.9,
            "is_turnover": 0.6,
            "oos_turnover": 0.7,
            "alphas_discovered": 0,
            "total_alphas": 3,
            "alpha_details": None,
            "noise_loadings": None,
        },
    },
    {
        "strategy_name": "Naive Momentum",
        "sub_id": "10000000-0000-0000-0000-000000000002",
        "report": {
            "is_sharpe": 0.30,
            "oos_sharpe": -0.05,
            "overfitting_ratio": -0.17,
            "is_max_dd": -21.3,
            "oos_max_dd": -28.1,
            "is_annual_return": 4.2,
            "oos_annual_return": -0.7,
            "is_turnover": 10.8,
            "oos_turnover": 11.2,
            "alphas_discovered": 1,
            "total_alphas": 3,
            "alpha_details": None,
            "noise_loadings": None,
        },
    },
    {
        "strategy_name": "Random Noise",
        "sub_id": "10000000-0000-0000-0000-000000000003",
        "report": {
            "is_sharpe": 0.95,
            "oos_sharpe": -0.80,
            "overfitting_ratio": -0.84,
            "is_max_dd": -38.7,
            "oos_max_dd": -61.3,
            "is_annual_return": 12.1,
            "oos_annual_return": -8.4,
            "is_turnover": 43.1,
            "oos_turnover": 45.0,
            "alphas_discovered": 0,
            "total_alphas": 3,
            "alpha_details": None,
            "noise_loadings": None,
        },
    },
]

BASELINE_CODE = "# Baseline — not a real submission\nclass MyStrategy:\n    pass\n"


def main() -> None:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ── 1. Ensure baseline user exists in auth.users (required for FK) ─────────
    # Use Supabase admin API to create a synthetic auth user if not present.
    import urllib.request, json as _json
    admin_url = f"{SUPABASE_URL}/auth/v1/admin/users/{BASELINE_USER_ID}"
    req = urllib.request.Request(
        admin_url,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req)
        print("Baseline auth user already exists")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Create the user
            create_req = urllib.request.Request(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                data=_json.dumps({
                    "id": BASELINE_USER_ID,
                    "email": "baseline@convexpi.internal",
                    "email_confirm": True,
                    "user_metadata": {"display_name": "— Baseline —"},
                }).encode(),
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(create_req)
            print("Created baseline auth user")
        else:
            raise

    # ── 2. Ensure baseline profile exists ────────────────────────────────────
    profile_check = (
        sb.table("profiles").select("id").eq("id", BASELINE_USER_ID).execute()
    )
    if not profile_check.data:
        sb.table("profiles").insert(
            {
                "id": BASELINE_USER_ID,
                "username": "baseline",
                "display_name": "— Baseline —",
            }
        ).execute()
        print("Created baseline profile")

    # ── 3. Upsert cohort ─────────────────────────────────────────────────────
    existing = (
        sb.table("cohorts").select("id").eq("slug", DEMO_SLUG).execute()
    )
    if existing.data:
        cohort_id = existing.data[0]["id"]
        print(f"Cohort already exists: {DEMO_SLUG} ({cohort_id})")
    else:
        result = (
            sb.table("cohorts")
            .insert(
                {
                    "slug": DEMO_SLUG,
                    "name": DEMO_NAME,
                    "description": DEMO_DESC,
                    "type": "competition",
                    "visibility": "public",
                    "owner_id": BASELINE_USER_ID,
                    "status": "active",
                }
            )
            .execute()
        )
        cohort_id = result.data[0]["id"]
        print(f"Created cohort: {DEMO_SLUG} ({cohort_id})")

    # ── 4. Insert baseline submissions + grade reports ────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    for b in BASELINES:
        sub_id = b["sub_id"]
        sub_check = sb.table("submissions").select("id").eq("id", sub_id).execute()
        if sub_check.data:
            print(f"Baseline already exists: {b['strategy_name']}")
            continue

        sb.table("submissions").insert(
            {
                "id": sub_id,
                "cohort_id": cohort_id,
                "user_id": BASELINE_USER_ID,
                "strategy_name": b["strategy_name"],
                "code": BASELINE_CODE,
                "submitted_at": now,
                "status": "completed",
                "error_message": None,
            }
        ).execute()

        report_id = str(uuid.uuid4())
        sb.table("grade_reports").insert(
            {
                "id": report_id,
                "submission_id": sub_id,
                "graded_at": now,
                **b["report"],
            }
        ).execute()

        print(f"Inserted baseline: {b['strategy_name']}")

    print("\nDone. Visit /compete/demo-fall-2026/leaderboard to verify.")


if __name__ == "__main__":
    main()
