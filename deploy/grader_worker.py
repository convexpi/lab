"""
grader_worker.py — Polls Supabase for pending submissions and grades them.

Deploy as a separate Railway service (same Docker image, different start command):
    python deploy/grader_worker.py

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
    - Student code runs in a subprocess with a 30s hard timeout.
    - Blocked imports are checked before execution (belt-and-suspenders with the API route check).
    - Each submission runs in a temp directory, isolated from other submissions.
    - The service role key is never exposed to student code.
"""

from __future__ import annotations
import os
import sys
import json
import time
import logging
import tempfile
import textwrap
import subprocess
import traceback
from pathlib import Path

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
# Grade runner — executes in a subprocess to isolate student code
# ---------------------------------------------------------------------------

# The runner always builds the market + grader the same way; only the strategy-execution middle
# differs by language (Python inlines a MyStrategy class; R/Julia hand their source to the grader,
# which runs it via its harness). Scoring + result extraction are shared.
_SETUP = textwrap.dedent("""
import sys, json
sys.path.insert(0, "{pkg_path}")
from convexpi.lab import SyntheticMarket, Grader
from convexpi.lab.synth import PlantedAlpha

_planted_alphas = {planted_alphas_repr}
market = SyntheticMarket(
    n_stocks={n_stocks}, n_days={n_days}, seed={seed},
    planted_alphas=_planted_alphas if _planted_alphas is not None else None,
)
grader = Grader(market)
""")

_PY_EXEC = textwrap.dedent("""
{user_code}

report = grader.evaluate(MyStrategy())
""")

_FOREIGN_EXEC = textwrap.dedent("""
report = grader.evaluate_language("{language}", {user_code_repr}, name="strategy")
""")

_RESULT = textwrap.dedent("""
result = dict(
    is_sharpe=report.is_sharpe,
    oos_sharpe=report.oos_sharpe,
    overfitting_ratio=report.overfitting_ratio,
    is_max_dd=report.is_max_dd,
    oos_max_dd=report.oos_max_dd,
    is_annual_return=report.is_result.annualized_return,
    oos_annual_return=report.oos_result.annualized_return,
    is_turnover=report.is_result.turnover_annual,
    oos_turnover=report.oos_result.turnover_annual,
    alphas_discovered=sum(1 for d in report.alpha_discovery if d.discovered),
    total_alphas=len(report.alpha_discovery),
    alpha_details=[
        dict(feature=d.feature, planted_bps=d.planted_strength_bps,
             corr=d.correlation, discovered=d.discovered, signal_ir=d.oos_contribution)
        for d in report.alpha_discovery
    ],
    noise_loadings={{k: v for k, v in report.noise_loadings.items()}},
)
print("__RESULT__:" + json.dumps(result))
""")

PY_RUNNER = _SETUP + _PY_EXEC + _RESULT
FOREIGN_RUNNER = _SETUP + _FOREIGN_EXEC + _RESULT

# Where the convexpi package lives (same container)
PKG_PATH = str(Path(__file__).parent.parent / "src")

BLOCKED_PATTERNS = [
    "import os", "import sys", "import subprocess", "import socket",
    "import requests", "__import__", "open(", "eval(", "exec(",
]

# Docker sandbox config — set GRADER_DOCKER_IMAGE to enable; falls back to subprocess
DOCKER_IMAGE   = os.environ.get("GRADER_DOCKER_IMAGE", "")
DOCKER_TIMEOUT = TIMEOUT_SECS + 5  # outer timeout slightly larger than inner


def _docker_available() -> bool:
    """Return True if the Docker daemon is reachable."""
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False

_USE_DOCKER: bool | None = None  # resolved lazily once


def _run_script(script_path: str, tmpdir: str) -> subprocess.CompletedProcess:
    """Run the grader script either inside a Docker sandbox or bare subprocess."""
    global _USE_DOCKER
    if _USE_DOCKER is None:
        _USE_DOCKER = bool(DOCKER_IMAGE) and _docker_available()
        log.info("sandbox mode: %s", "docker" if _USE_DOCKER else "subprocess")

    if _USE_DOCKER:
        cmd = [
            "docker", "run",
            "--rm",
            "--network", "none",        # no outbound network
            "--read-only",              # read-only root filesystem
            "--tmpfs", "/tmp:size=64m", # writable /tmp for numpy etc.
            "--memory", "512m",
            "--cpus", "1",
            "-v", f"{tmpdir}:{tmpdir}:ro",   # mount script read-only
            "-v", f"{PKG_PATH}:{PKG_PATH}:ro",
            DOCKER_IMAGE,
            "python", script_path,
        ]
    else:
        cmd = [sys.executable, script_path]

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=DOCKER_TIMEOUT if _USE_DOCKER else TIMEOUT_SECS,
        cwd=tmpdir,
    )


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

    # Build planted_alphas repr for the runner script
    raw_alphas = cfg.get("planted_alphas")  # list of dicts, or None = use defaults
    if raw_alphas is not None:
        alpha_reprs = []
        for a in raw_alphas:
            alpha_reprs.append(
                f"PlantedAlpha("
                f"feature={a['feature']!r}, "
                f"strength_bps={float(a['strength_bps'])}, "
                f"halflife_days={int(a.get('halflife_days', 20))}, "
                f"start_day={int(a.get('start_day', 0))}, "
                f"end_day={int(a.get('end_day', -1))})"
            )
        planted_alphas_repr = "[" + ", ".join(alpha_reprs) + "]"
    else:
        planted_alphas_repr = "None"  # SyntheticMarket will use its own defaults

    common = dict(pkg_path=PKG_PATH, n_stocks=n_stocks, n_days=n_days, seed=seed,
                  planted_alphas_repr=planted_alphas_repr)
    if language == "python":
        runner = PY_RUNNER.format(user_code=code, **common)
    else:
        runner = FOREIGN_RUNNER.format(language=language, user_code_repr=repr(code), **common)

    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "runner.py"
        script.write_text(runner)

        t_start = time.monotonic()
        try:
            result = _run_script(str(script), tmpdir)
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - t_start
            log.warning("submission=%s timed out after %.1fs", sub_id[:8], elapsed)
            msg = f"Timed out after {TIMEOUT_SECS}s. Simplify your strategy."
            mark_failed(sub_id, msg)
            notify_grade_failed(sub_id, msg)
            return

    elapsed = time.monotonic() - t_start
    stdout = result.stdout

    if result.returncode != 0 or "__RESULT__:" not in stdout:
        stderr = result.stderr[-2000:] if result.stderr else "(no stderr)"
        log.warning("submission=%s error (rc=%d, %.1fs): %s",
                    sub_id[:8], result.returncode, elapsed, stderr[:200])
        msg = f"Strategy raised an error:\n{stderr}"
        mark_failed(sub_id, msg)
        notify_grade_failed(sub_id, msg)
        return

    try:
        json_str = stdout.split("__RESULT__:")[1].strip().split("\n")[0]
        report_data = json.loads(json_str)
    except Exception:
        log.error("submission=%s could not parse grader output", sub_id[:8])
        mark_failed(sub_id, "Could not parse grader output.")
        return

    write_grade_report(sub_id, report_data)
    mark_completed(sub_id)
    notify_grade_completed(sub_id, report_data)
    log.info("submission=%s completed  oos_sharpe=%.3f  elapsed=%.1fs",
             sub_id[:8], report_data.get("oos_sharpe", 0), elapsed)


# ---------------------------------------------------------------------------
# Poll loop
# ---------------------------------------------------------------------------

def main():
    log.info("grader worker started  seed=%d  stocks=%d  days=%d  "
             "poll=%.1fs  timeout=%ds",
             MARKET_SEED, N_STOCKS, N_DAYS, POLL_SECONDS, TIMEOUT_SECS)
    while True:
        try:
            pending = fetch_pending()
            if pending:
                log.info("found %d pending submission(s)", len(pending))
            for sub in pending:
                try:
                    grade_submission(sub)
                except Exception:
                    log.exception("unexpected error grading submission=%s", sub["id"][:8])
                    mark_failed(sub["id"], traceback.format_exc()[-2000:])
        except Exception:
            log.exception("poll loop error")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
