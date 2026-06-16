"""
forward_runner.py — Nightly forward paper-trading evaluator.

For each completed submission, runs the strategy on a fresh synthetic market
window (seeded by today's date) and upserts one row into forward_scores.
The leaderboard then shows rolling forward Sharpe alongside backtest Sharpe.

Run once per day (cron, Railway cron service, or GitHub Actions schedule):
    python deploy/forward_runner.py

Required env vars (same as grader_worker):
    NEXT_PUBLIC_SUPABASE_URL — your project URL
    SUPABASE_SERVICE_KEY     — service role key (bypasses RLS)
    MARKET_SEED_BASE     — integer base seed (default 1000); daily seed = base + days_since_epoch

Optional:
    FORWARD_WINDOW_DAYS  — trading days per evaluation window (default 60)
    FORWARD_N_STOCKS     — stocks in each daily market (default 100; smaller = faster)
    DISCORD_WEBHOOK_URL  — post a daily summary embed
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import urllib.request
import urllib.error
from datetime import date, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,
)
log = logging.getLogger("forward_runner")

SUPABASE_URL    = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY    = os.environ["SUPABASE_SERVICE_KEY"]
SEED_BASE       = int(os.environ.get("MARKET_SEED_BASE", "1000"))
WINDOW_DAYS     = int(os.environ.get("FORWARD_WINDOW_DAYS", "60"))
N_STOCKS        = int(os.environ.get("FORWARD_N_STOCKS", "100"))
TIMEOUT_SECS    = int(os.environ.get("GRADE_TIMEOUT", "120"))
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")

PKG_PATH = str(Path(__file__).parent.parent / "src")

# Seed is deterministic per calendar date so re-runs are idempotent
EPOCH = date(2020, 1, 1)


def date_seed(run_date: date) -> int:
    return SEED_BASE + (run_date - EPOCH).days


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _req(method: str, path: str, body: dict | None = None):
    url = f"{SUPABASE_URL}/rest/v1{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log.error("supabase %s %s → %s: %s", method, path, e.code, e.read().decode()[:200])
        return None
    except Exception as exc:
        log.error("supabase %s %s → %s", method, path, exc)
        return None


def fetch_completed_submissions() -> list[dict]:
    result = _req("GET", "/submissions?status=eq.completed&select=id,cohort_id,code&limit=500")
    return result or []


def already_scored(submission_id: str, run_date: date) -> bool:
    result = _req("GET", f"/forward_scores?submission_id=eq.{submission_id}&run_date=eq.{run_date}&select=id")
    return bool(result)


def upsert_score(submission_id: str, run_date: date, seed: int, metrics: dict) -> None:
    _req("POST", "/forward_scores", {
        "submission_id":  submission_id,
        "run_date":       str(run_date),
        "forward_sharpe": metrics.get("oos_sharpe"),
        "forward_return": metrics.get("oos_annual_return"),
        "forward_max_dd": metrics.get("oos_max_dd"),
        "market_seed":    seed,
        "window_days":    WINDOW_DAYS,
    })


# ---------------------------------------------------------------------------
# Runner template (reuses grader runner pattern)
# ---------------------------------------------------------------------------

RUNNER_TEMPLATE = textwrap.dedent("""\
    import sys, json
    sys.path.insert(0, {pkg_path!r})

    from convexpi.lab.synth import SyntheticMarket
    from convexpi.lab.grader import Grader

    {user_code}

    market = SyntheticMarket(
        n_stocks={n_stocks},
        n_days={n_days},
        seed={seed},
    )
    report = Grader(market).evaluate(MyStrategy())
    result = {{
        "oos_sharpe":        report.oos_sharpe,
        "oos_annual_return": report.oos_annual_return,
        "oos_max_dd":        report.oos_max_dd,
    }}
    print("__RESULT__:" + json.dumps(result))
""")


def evaluate_submission(sub_id: str, code: str, seed: int) -> dict | None:
    runner = RUNNER_TEMPLATE.format(
        pkg_path=PKG_PATH,
        user_code=code,
        n_stocks=N_STOCKS,
        n_days=WINDOW_DAYS + 20,   # small buffer for IS warmup
        seed=seed,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "forward_runner.py"
        script.write_text(runner)
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True,
                timeout=TIMEOUT_SECS,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired:
            log.warning("submission=%s forward eval timed out", sub_id[:8])
            return None

    if result.returncode != 0 or "__RESULT__:" not in result.stdout:
        log.warning("submission=%s forward eval error: %s", sub_id[:8], result.stderr[:200])
        return None

    try:
        json_str = result.stdout.split("__RESULT__:")[1].strip().split("\n")[0]
        return json.loads(json_str)
    except Exception:
        log.error("submission=%s could not parse forward output", sub_id[:8])
        return None


# ---------------------------------------------------------------------------
# Discord summary
# ---------------------------------------------------------------------------

def _discord_post(payload: dict) -> None:
    if not DISCORD_WEBHOOK:
        return
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        DISCORD_WEBHOOK, data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception as exc:
        log.warning("discord webhook failed: %s", exc)


def post_daily_summary(run_date: date, n_scored: int, n_skipped: int, n_failed: int,
                       best: dict | None) -> None:
    lines = [
        f"Scored **{n_scored}** submissions   skipped {n_skipped}   failed {n_failed}",
    ]
    if best:
        lines.append(
            f"Best forward Sharpe: **{best['sharpe']:.3f}** (submission `{best['sub_id'][:8]}`)"
        )
    _discord_post({
        "embeds": [{
            "title": f"Forward paper-trading — {run_date}",
            "color": 0x5865F2,
            "description": "\n".join(lines),
            "footer": {"text": "ConvexPi forward runner"},
        }]
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    run_date = date.today()
    seed     = date_seed(run_date)
    log.info("forward runner started  date=%s  seed=%d  window=%d  stocks=%d",
             run_date, seed, WINDOW_DAYS, N_STOCKS)

    submissions = fetch_completed_submissions()
    log.info("found %d completed submissions", len(submissions))

    n_scored = n_skipped = n_failed = 0
    best: dict | None = None

    for sub in submissions:
        sub_id    = sub["id"]
        code      = sub.get("code", "")

        if already_scored(sub_id, run_date):
            log.info("submission=%s already scored for %s — skipping", sub_id[:8], run_date)
            n_skipped += 1
            continue

        t0 = time.monotonic()
        metrics = evaluate_submission(sub_id, code, seed)
        elapsed = time.monotonic() - t0

        if metrics is None:
            n_failed += 1
            continue

        upsert_score(sub_id, run_date, seed, metrics)
        sharpe = metrics.get("oos_sharpe") or 0.0
        log.info("submission=%s  forward_sharpe=%.3f  elapsed=%.1fs", sub_id[:8], sharpe, elapsed)
        n_scored += 1

        if best is None or sharpe > best["sharpe"]:
            best = {"sub_id": sub_id, "sharpe": sharpe}

    log.info("done  scored=%d  skipped=%d  failed=%d", n_scored, n_skipped, n_failed)
    post_daily_summary(run_date, n_scored, n_skipped, n_failed, best)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.error("forward runner crashed:\n%s", traceback.format_exc())
        sys.exit(1)
