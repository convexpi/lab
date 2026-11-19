"""
grader_worker.py — Polls Supabase for pending submissions and grades them.

Run on the dedicated Docker host, draining pending work and exiting:
    python deploy/grader_worker.py --once

Required env vars:
    NEXT_PUBLIC_SUPABASE_URL — your project URL (same var as the web platform)
    SUPABASE_SERVICE_KEY     — service role key (bypasses RLS)
    MARKET_SEED          — integer seed for the hidden market (keep private)
    MARKET_N_STOCKS      — default 200
    MARKET_N_DAYS        — default 1260

Per-cohort overrides (stored in cohorts.market_config JSONB):
    seed, n_stocks, n_days    — override defaults above
    planted_alphas            — list of {feature, strength_bps, halflife_days,
                                start_day, end_day} dicts; replaces default alphas

Security model:
    - Student code runs in mandatory, credential-free Docker containers.
    - Trusted scoring streams observations and accepts only bounded decisions.
    - Blocked imports are checked before execution (belt-and-suspenders with the API route check).
    - Each submission runs in a temp directory, isolated from other submissions.
    - Deployment credentials are never inherited by student code.
"""

from __future__ import annotations
import os
import sys
import json
import time
import argparse
import logging
import subprocess
import traceback

import urllib.request
import urllib.error

# Sentry is optional — only active when SENTRY_DSN env var is set.
try:
    import sentry_sdk
    _sentry_dsn = os.environ.get("SENTRY_DSN")
    if _sentry_dsn:
        sentry_sdk.init(
            dsn=_sentry_dsn,
            environment=os.environ.get("ENVIRONMENT", "production"),
            traces_sample_rate=0.1,
        )
except ImportError:
    pass  # sentry-sdk not installed — monitoring silently disabled


# ---------------------------------------------------------------------------
# Structured logging — timestamps + log levels, aggregated properly by Railway
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,
)
log = logging.getLogger("grader")


SUPABASE_URL    = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY    = os.environ["SUPABASE_SERVICE_KEY"]
MARKET_SEED     = int(os.environ.get("MARKET_SEED", "42"))
N_STOCKS        = int(os.environ.get("MARKET_N_STOCKS", "200"))
N_DAYS          = int(os.environ.get("MARKET_N_DAYS", "1260"))
POLL_SECONDS    = float(os.environ.get("POLL_SECONDS", "5"))
TIMEOUT_SECS    = int(os.environ.get("GRADE_TIMEOUT", "60"))
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")
MAX_SUBMISSIONS_PER_RUN = int(os.environ.get("MAX_SUBMISSIONS_PER_RUN", "20"))


# ---------------------------------------------------------------------------
# Supabase REST helpers (no external deps beyond stdlib)
# ---------------------------------------------------------------------------

def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _req(method: str, path: str, body: dict | None = None) -> dict | list | None:
    url = f"{SUPABASE_URL}/rest/v1{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log.error("supabase %s %s → %s: %s", method, path, e.code, e.read().decode())
        return None
    except Exception as e:
        log.error("supabase %s %s → %s", method, path, e)
        return None


def fetch_pending() -> list[dict]:
    result = _req("GET", "/submissions?status=eq.pending&limit=5&select=id,cohort_id,code,language")
    return result or []


def mark_running(sub_id: str) -> None:
    _req("PATCH", f"/submissions?id=eq.{sub_id}", {"status": "running"})


def mark_failed(sub_id: str, message: str) -> None:
    log.warning("submission=%s failed: %s", sub_id[:8], message[:120])
    _req("PATCH", f"/submissions?id=eq.{sub_id}",
         {"status": "failed", "error_message": message[:2000]})


def mark_completed(sub_id: str) -> None:
    _req("PATCH", f"/submissions?id=eq.{sub_id}", {"status": "completed"})


def write_grade_report(sub_id: str, report: dict) -> None:
    _req("POST", "/grade_reports", {"submission_id": sub_id, **report})


def fetch_market_config(cohort_id: str) -> dict:
    result = _req("GET", f"/cohorts?id=eq.{cohort_id}&select=market_config")
    if result and len(result) > 0:
        return result[0].get("market_config") or {}
    return {}


# ---------------------------------------------------------------------------
# Discord webhook (optional — only active when DISCORD_WEBHOOK_URL is set)
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


def notify_grade_completed(sub_id: str, report: dict) -> None:
    oos = report.get("oos_sharpe")
    ovf = report.get("overfitting_ratio")
    discovered = report.get("alphas_discovered")
    total      = report.get("total_alphas")

    if oos is None:
        return

    ovf_str = f"{ovf:.2f}" if ovf is not None else "—"
    alpha_str = f"{discovered}/{total}" if discovered is not None else "—"

    color = 0x57F287 if oos > 0.5 else (0xFEE75C if oos > 0 else 0xED4245)

    _discord_post({
        "embeds": [{
            "title": "Strategy graded",
            "color": color,
            "fields": [
                {"name": "OOS Sharpe",       "value": f"{oos:.3f}", "inline": True},
                {"name": "Overfitting ratio", "value": ovf_str,     "inline": True},
                {"name": "Alphas found",      "value": alpha_str,   "inline": True},
                {"name": "Submission",        "value": sub_id[:8],  "inline": True},
            ],
            "footer": {"text": "ConvexPi grader"},
        }]
    })


def notify_grade_failed(sub_id: str, message: str) -> None:
    _discord_post({
        "embeds": [{
            "title": "Grading failed",
            "color": 0xED4245,
            "fields": [
                {"name": "Submission", "value": sub_id[:8],          "inline": True},
                {"name": "Reason",     "value": message[:200],       "inline": False},
            ],
            "footer": {"text": "ConvexPi grader"},
        }]
    })


# ---------------------------------------------------------------------------
# Grade runner — streams decisions from a mandatory isolated container
# ---------------------------------------------------------------------------

try:
    from .evaluation import grade_code, report_dict
    from .check_runtime import check_runtime
except ImportError:
    from evaluation import grade_code, report_dict
    from check_runtime import check_runtime
from convexpi.lab import SyntheticMarket, PlantedAlpha

BLOCKED_PATTERNS = [
    "import os", "import sys", "import subprocess", "import socket",
    "import requests", "__import__", "open(", "eval(", "exec(",
]


def grade_submission(submission: dict) -> None:
    sub_id = submission["id"]
    cohort_id = submission["cohort_id"]
    code: str = submission["code"]
    language: str = (submission.get("language") or "python").lower()

    log.info("submission=%s grading started (%s)", sub_id[:8], language)
    mark_running(sub_id)

    # Language-aware belt-and-suspenders (the API already validated; this guards the worker).
    if language == "python":
        for pattern in BLOCKED_PATTERNS:
            if pattern in code:
                mark_failed(sub_id, f"Blocked: '{pattern}' is not allowed.")
                return
        if "class MyStrategy" not in code:
            mark_failed(sub_id, "Code must define a class named MyStrategy.")
            return
    elif language not in ("r", "julia"):
        mark_failed(sub_id, f"Unsupported language: {language}")
        return

    # Resolve market config (cohort can override seed/size/planted alphas)
    cfg      = fetch_market_config(cohort_id)
    seed     = int(cfg.get("seed",     MARKET_SEED))
    n_stocks = int(cfg.get("n_stocks", N_STOCKS))
    n_days   = int(cfg.get("n_days",   N_DAYS))
    # Idiosyncratic-return DGP: "t" (default) or "garch" (finmlsim clustering + fat tails). Opt-in
    # per cohort so existing markets/grades are unchanged unless a cohort explicitly asks for it.
    idio_process = "garch" if str(cfg.get("idio_process", "t")).lower() == "garch" else "t"

    raw_alphas = cfg.get("planted_alphas")
    alphas = [PlantedAlpha(**a) for a in raw_alphas] if raw_alphas is not None else None
    market = SyntheticMarket(n_stocks=n_stocks, n_days=n_days, seed=seed,
                             idio_process=idio_process, planted_alphas=alphas)
    t_start = time.monotonic()
    try:
        report_data = report_dict(grade_code(code, language, market, timeout=TIMEOUT_SECS))
    except subprocess.TimeoutExpired:
        msg = f"Timed out after {TIMEOUT_SECS}s. Simplify your strategy."
        mark_failed(sub_id, msg)
        notify_grade_failed(sub_id, msg)
        return
    except Exception as exc:
        msg = f"Strategy evaluation failed: {exc}"
        mark_failed(sub_id, msg)
        notify_grade_failed(sub_id, msg)
        return
    elapsed = time.monotonic() - t_start

    write_grade_report(sub_id, report_data)
    mark_completed(sub_id)
    notify_grade_completed(sub_id, report_data)
    log.info("submission=%s completed  oos_sharpe=%.3f  elapsed=%.1fs",
             sub_id[:8], report_data.get("oos_sharpe", 0), elapsed)


# ---------------------------------------------------------------------------
# Poll loop
# ---------------------------------------------------------------------------

WORKER_BUILD = "2026-11-19-isolated-1"

def _grade_pending_once() -> int:
    """Drain a bounded batch and return the number of submissions processed."""
    processed = 0
    while processed < MAX_SUBMISSIONS_PER_RUN:
        pending = fetch_pending()
        if not pending:
            break
        log.info("found %d pending submission(s)", len(pending))
        for sub in pending[:MAX_SUBMISSIONS_PER_RUN - processed]:
            try:
                grade_submission(sub)
            except Exception:
                log.exception("unexpected error grading submission=%s", sub["id"][:8])
                mark_failed(sub["id"], traceback.format_exc()[-2000:])
            processed += 1
        if len(pending) < 5:
            break
    return processed


def main(*, run_once: bool = False):
    # Infrastructure outages must not turn queued submissions into failed grades.
    # Verify the daemon, image, shared mounts, and all language runtimes first.
    check_runtime()
    log.info("grader worker started  build=%s  languages=python,r,julia  "
             "stocks=%d  days=%d  mode=%s  poll=%.1fs  timeout=%ds",
             WORKER_BUILD, N_STOCKS, N_DAYS,
             "once" if run_once else "continuous", POLL_SECONDS, TIMEOUT_SECS)
    if run_once:
        processed = _grade_pending_once()
        log.info("grader run complete  processed=%d", processed)
        return

    while True:
        try:
            _grade_pending_once()
        except Exception:
            log.exception("poll loop error")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ConvexPi submission grader")
    parser.add_argument(
        "--once", action="store_true",
        help="Drain a bounded batch and exit (for scheduled jobs)",
    )
    main(run_once=parser.parse_args().once)
