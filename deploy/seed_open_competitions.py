"""
seed_open_competitions.py — Create the permanent, public, always-open competitions.

Idempotent (safe to re-run; checks before inserting). Creates:
  - 'open-leaderboard'  (Lab)   : submit any strategy; ranked by out-of-sample /
                                  forward Sharpe; seeded with three reference
                                  baselines (Equal Weight, Naive Momentum, and a
                                  Random-Noise strategy whose backtest Sharpe
                                  collapses out of sample — the overfitting tell).
  - 'arena-open'        (Arena) : an always-open limit-order-book trading ladder
                                  ranked by PnL, with one active arena_sessions row.

Both are owned by the synthetic baseline/system user (shared with
seed_demo_cohort.py) and have no end date.

Ongoing scoring is automatic: the grader_worker service (Railway) grades Lab
submissions on the hidden OOS market, and forward_runner.py (nightly GitHub
Action) re-scores them on fresh windows. Live Arena play requires the Arena
server (arena/deploy) to be running.

Usage:
    NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co \
    SUPABASE_SERVICE_KEY=eyJ... \
    python deploy/seed_open_competitions.py
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# Synthetic baseline/system user — shared with seed_demo_cohort.py.
BASELINE_USER_ID = "00000000-0000-0000-0000-000000000001"
BASELINE_CODE = "# Baseline — not a real submission\nclass MyStrategy:\n    pass\n"

# Reference baselines shown on every Lab leaderboard. The Random-Noise row is the
# teaching artifact: a beautiful in-sample Sharpe that goes negative out of sample.
BASELINES = [
    {"strategy_name": "Equal Weight", "report": {
        "is_sharpe": 0.08, "oos_sharpe": 0.10, "overfitting_ratio": 1.00,
        "is_max_dd": -11.2, "oos_max_dd": -12.4, "is_annual_return": 1.1,
        "oos_annual_return": 0.9, "is_turnover": 0.6, "oos_turnover": 0.7,
        "alphas_discovered": 0, "total_alphas": 3, "alpha_details": None, "noise_loadings": None}},
    {"strategy_name": "Naive Momentum", "report": {
        "is_sharpe": 0.30, "oos_sharpe": -0.05, "overfitting_ratio": -0.17,
        "is_max_dd": -21.3, "oos_max_dd": -28.1, "is_annual_return": 4.2,
        "oos_annual_return": -0.7, "is_turnover": 10.8, "oos_turnover": 11.2,
        "alphas_discovered": 1, "total_alphas": 3, "alpha_details": None, "noise_loadings": None}},
    {"strategy_name": "Random Noise", "report": {
        "is_sharpe": 0.95, "oos_sharpe": -0.80, "overfitting_ratio": -0.84,
        "is_max_dd": -38.7, "oos_max_dd": -61.3, "is_annual_return": 12.1,
        "oos_annual_return": -8.4, "is_turnover": 43.1, "oos_turnover": 45.0,
        "alphas_discovered": 0, "total_alphas": 3, "alpha_details": None, "noise_loadings": None}},
]


# ---------------------------------------------------------------------------
# Tiny REST/auth helpers (urllib only — no extra deps, runs in CI)
# ---------------------------------------------------------------------------

def _api(method: str, url: str, body=None, extra_headers=None):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode()
        return r.status, (json.loads(raw) if raw.strip() else None)


def rest_get(table: str, query: str):
    _, data = _api("GET", f"{SUPABASE_URL}/rest/v1/{table}?{query}")
    return data or []


def rest_insert(table: str, row: dict):
    _, data = _api("POST", f"{SUPABASE_URL}/rest/v1/{table}", body=row,
                   extra_headers={"Prefer": "return=representation"})
    return data[0] if data else None


def rest_update(table: str, query: str, patch: dict):
    _api("PATCH", f"{SUPABASE_URL}/rest/v1/{table}?{query}", body=patch,
         extra_headers={"Prefer": "return=minimal"})


def ensure_baseline_user():
    """Create the synthetic baseline auth user + profile if missing (FK target)."""
    try:
        _api("GET", f"{SUPABASE_URL}/auth/v1/admin/users/{BASELINE_USER_ID}")
        print("Baseline auth user exists")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        _api("POST", f"{SUPABASE_URL}/auth/v1/admin/users", body={
            "id": BASELINE_USER_ID, "email": "baseline@convexpi.internal",
            "email_confirm": True, "user_metadata": {"display_name": "— Baseline —"}})
        print("Created baseline auth user")
    if not rest_get("profiles", f"id=eq.{BASELINE_USER_ID}&select=id"):
        rest_insert("profiles", {"id": BASELINE_USER_ID, "username": "baseline",
                                 "display_name": "— Baseline —"})
        print("Created baseline profile")


# ---------------------------------------------------------------------------
# Cohort / baseline / arena seeding (importable; reused by roll_seasons.py)
# ---------------------------------------------------------------------------

def upsert_cohort(spec: dict) -> str:
    """Insert the competition cohort if its slug is new; return the cohort id."""
    existing = rest_get("cohorts", f"slug=eq.{spec['slug']}&select=id")
    if existing:
        print(f"Cohort exists: {spec['slug']} ({existing[0]['id']})")
        return existing[0]["id"]
    row = rest_insert("cohorts", spec)
    print(f"Created cohort: {spec['slug']} ({row['id']})")
    return row["id"]


def seed_baselines(cohort_id: str, slug: str) -> None:
    """Insert the three reference baselines + grade reports (deterministic ids)."""
    now = datetime.now(timezone.utc).isoformat()
    for b in BASELINES:
        sub_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"convexpi-baseline:{slug}:{b['strategy_name']}"))
        if rest_get("submissions", f"id=eq.{sub_id}&select=id"):
            continue
        rest_insert("submissions", {
            "id": sub_id, "cohort_id": cohort_id, "user_id": BASELINE_USER_ID,
            "strategy_name": b["strategy_name"], "code": BASELINE_CODE,
            "submitted_at": now, "status": "completed", "error_message": None})
        rest_insert("grade_reports", {
            "id": str(uuid.uuid4()), "submission_id": sub_id, "graded_at": now, **b["report"]})
        print(f"  + baseline: {b['strategy_name']}")


def ensure_arena_session(cohort_id: str, config: dict, *, season_name: str = "Open Ladder",
                         description: str = "Always-open live trading ladder. Connect an agent "
                                            "and climb the PnL rankings.") -> None:
    """Ensure one active arena_sessions row exists for the cohort."""
    if rest_get("arena_sessions", f"cohort_id=eq.{cohort_id}&status=eq.active&select=id"):
        print("  arena session already active")
        return
    rest_insert("arena_sessions", {
        "cohort_id": cohort_id, "season_name": season_name,
        "description": description,
        "status": "active", "config": config})
    print("  + active arena session")


# ---------------------------------------------------------------------------
# Competition specs
# ---------------------------------------------------------------------------

OPEN_LEADERBOARD = {
    "slug": "open-leaderboard",
    "name": "The Open Leaderboard",
    "description": ("The always-open competition. Submit any strategy and see how it ranks "
                    "out of sample against reference baselines and everyone else. No deadline."),
    "type": "competition", "visibility": "public", "owner_id": BASELINE_USER_ID,
    "status": "active", "market_config": {},
}

ARENA_OPEN = {
    "slug": "arena-open",
    "name": "Arena Open Ladder",
    "description": ("An always-open live limit-order-book trading ladder. Connect an agent to the "
                    "Arena and climb the PnL rankings against other players and background agents."),
    "type": "competition", "visibility": "public", "owner_id": BASELINE_USER_ID,
    "status": "active",
    "arena_config": {"tick_interval": 0.5, "n_ticks": 2000, "n_background_agents": 20, "seed": 42},
}

# Real-order-book season: the Arena runs in book-replay mode against recorded L2 depth, so players
# trade against real (or realistic) market liquidity — real slippage, real queues. The arena server
# for this session must be launched with ARENA_CRYPTO_BOOK pointing at a depth JSONL (ship
# arena/data/sample_btcusdt_book.jsonl, or record one with deploy/fetch_crypto_orderbook.py).
ARENA_BOOK = {
    "slug": "arena-book",
    "name": "Arena — Real Order Book",
    "description": ("A live ladder run on a real recorded limit order book. Your market orders walk "
                    "the actual depth and pay real slippage; your limit orders queue against real "
                    "liquidity. Connect an agent and trade like it's a real exchange."),
    "type": "competition", "visibility": "public", "owner_id": BASELINE_USER_ID,
    "status": "active",
    "arena_config": {"tick_interval": 0.5, "n_ticks": None, "n_background_agents": 0, "seed": 42,
                     "mode": "crypto_book", "crypto_book": "data/btcusd_book.jsonl",
                     "maker_fee_bps": -1.0, "taker_fee_bps": 3.0,
                     # ws_url drives the public live-book view on /compete/arena-book.
                     "ws_url": "wss://arena-production-e3f1.up.railway.app"},
}


ARENA_L3 = {
    "slug": "arena-l3",
    "name": "Arena — Realistic Exchange (L3)",
    "description": ("Trade on a real order-by-order book. Your limit orders take a real place in the "
                    "FIFO queue and only fill once they reach the front — queue position and timing "
                    "decide everything. Run a server with ARENA_CRYPTO_L3 to feed this season."),
    "type": "competition", "visibility": "public", "owner_id": BASELINE_USER_ID,
    "status": "active",
    "arena_config": {"tick_interval": 0.5, "n_ticks": None, "n_background_agents": 0, "seed": 42,
                     "mode": "crypto_l3", "crypto_l3": "data/btcusd_l3_sample.jsonl",
                     "ws_url": "wss://arena-l3-production.up.railway.app"},
    "market_config": {"data_description": "Order-by-order (L3) replay of a real Bitstamp BTC feed. "
                      "Your limit orders join the real FIFO queue at their price and fill only when "
                      "they reach the front — genuine queue position, not snapshot depth."},
}


def main() -> None:
    ensure_baseline_user()

    lab_id = upsert_cohort(OPEN_LEADERBOARD)
    seed_baselines(lab_id, OPEN_LEADERBOARD["slug"])

    arena_id = upsert_cohort(ARENA_OPEN)
    ensure_arena_session(arena_id, ARENA_OPEN["arena_config"])

    book_id = upsert_cohort(ARENA_BOOK)
    ensure_arena_session(
        book_id, ARENA_BOOK["arena_config"],
        season_name="Real Order Book",
        description="Live ladder on a real recorded limit order book — real depth, real slippage.")

    l3_id = upsert_cohort(ARENA_L3)
    ensure_arena_session(
        l3_id, ARENA_L3["arena_config"],
        season_name="Realistic Exchange (L3)",
        description="Order-by-order book — real FIFO queue position and queue-based fills.")

    print("\nDone.")
    print("  Lab:        /compete/open-leaderboard/leaderboard")
    print("  Arena:      /compete/arena-open/leaderboard")
    print("  Arena book: /compete/arena-book/leaderboard")
    print("  Arena L3:   /compete/arena-l3")


if __name__ == "__main__":
    main()
