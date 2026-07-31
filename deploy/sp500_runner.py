"""
sp500_runner.py — score the S&P 500 next-day prediction competition on real Yahoo prices.

For each active model (sp500_models.code defines `predict(history) -> float`), we walk forward over the
last ~252 trading days of real ^GSPC data: each day the model sees only history up to that day and
predicts the next session's return; we score the realized move. The result (directional hit-rate,
cumulative PnL, Sharpe) is upserted into sp500_scores. Run daily after the US close — each run folds in
the newest day, so the standings are genuinely live and out-of-sample.

Safety: submitted code is validated and executed via deploy/sandbox.py — AST-checked imports, a
stripped environment that carries no credentials, and POSIX resource limits. See that module for
what this does and does not guarantee.

Identity: each forecast is stamped with a hash of the code that produced it, and the live
aggregates only count forecasts from the model's current code. Editing a submission therefore
starts its live track over rather than blending the new code's score with the old code's history.

Env: NEXT_PUBLIC_SUPABASE_URL (or SUPABASE_URL), SUPABASE_SERVICE_KEY.
Run: python deploy/sp500_runner.py
"""
from __future__ import annotations
import datetime
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats  # noqa: E402
from sandbox import Rejected, run as run_sandboxed, validate  # noqa: E402

URL = (os.environ.get("SUPABASE_URL") or os.environ["NEXT_PUBLIC_SUPABASE_URL"]).rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
WINDOW = 252            # trading days scored
TIMEOUT = 60            # seconds per model

# Round-trip cost charged whenever the position changes, in basis points of notional. Without this
# the scoring is blind to turnover: a model that flips long/short every session pays nothing, while
# one that holds pays the same nothing, so churn is free and high-turnover noise outranks patience.
# 2bp is a realistic all-in estimate for a liquid index future — deliberately conservative, since
# the point is to stop rewarding churn rather than to model execution precisely.
COST_BPS = 2.0


def code_hash(code: str) -> str:
    """Identity of a submission's code. Forecasts are attributed to the exact source that made them."""
    return hashlib.sha256(code.encode()).hexdigest()[:16]


def _req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{URL}/rest/v1{path}", data=data, method=method,
                               headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                                        "Content-Type": "application/json",
                                        "Prefer": "resolution=merge-duplicates,return=minimal"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else None


def _column_exists(table: str, column: str) -> bool:
    """Probe whether a column is present, so a deploy that lands before its migration degrades
    instead of failing every write. PostgREST answers an unknown column with 400."""
    try:
        _req("GET", f"/{table}?select={column}&limit=1")
        return True
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            return False
        raise


# Resolved once in main(). When false, the live track can't be scoped to the producing code, so it
# falls back to the old unscoped behaviour rather than breaking the nightly run.
HAS_CODE_HASH = True

# Columns added by 20260731_sp500_costs_and_deflation.sql. Dropped from the payload when the
# migration hasn't been applied, so shipping the runner first degrades instead of 400-ing.
EXTRA_SCORE_COLS = ("gross_sharpe", "cost_drag", "turnover", "excess_return", "info_ratio",
                    "live_info_ratio", "live_turnover", "live_deflated_sharpe")
HAS_EXTRA_SCORE_COLS = True


def fetch_models():
    r = urllib.request.Request(f"{URL}/rest/v1/sp500_models?status=eq.active&select=id,name,code",
                               headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())


RUNNER = """
import json, numpy as np, pandas as pd
prices = pd.read_csv({csv!r}, index_col=0, parse_dates=True)

{user_code}

close = prices['close'].values
n = len(close)
start = max(1, n - {window} - 1)
cost = {cost_bps} / 10000.0
pnl, gross, bench, hits, bets, flips = [], [], [], 0, 0, 0
prev_s = 0
for i in range(start, n - 1):
    hist = prices.iloc[:i + 1]
    try:
        p = float(predict(hist))
    except Exception:
        p = 0.0
    realized = close[i + 1] / close[i] - 1.0
    s = 1 if p > 0 else (-1 if p < 0 else 0)
    # Cost is charged on the size of the position change, so a hold pays nothing, a flat->long pays
    # one unit and a long->short pays two.
    turn = abs(s - prev_s)
    flips += int(turn > 0)
    gross.append(s * realized)
    pnl.append(s * realized - cost * turn)
    bench.append(realized)                      # buy & hold, the null this all competes against
    prev_s = s
    if s != 0:
        bets += 1
        hits += int(s == (1 if realized > 0 else -1))
pnl, gross, bench = np.array(pnl), np.array(gross), np.array(bench)


def _sharpe(x):
    return float(np.sqrt(252) * x.mean() / x.std()) if len(x) and x.std() > 1e-12 else 0.0


# Excess over buy & hold: the question a visitor actually has is "did this beat just holding it?",
# which an absolute Sharpe cannot answer.
excess = pnl - bench
# The model's live call for the NEXT (unrealized) session: predict on the full history.
try:
    fwd = float(predict(prices))
except Exception:
    fwd = 0.0
print(json.dumps({{
    "n_days": int(len(pnl)),
    "hit_rate": (hits / bets) if bets else 0.0,
    "cum_return": float(np.prod(1 + pnl) - 1),
    "sharpe": _sharpe(pnl),
    "gross_sharpe": _sharpe(gross),
    "cost_drag": float(np.prod(1 + gross) - np.prod(1 + pnl)),
    "turnover": float(flips / len(pnl)) if len(pnl) else 0.0,
    "excess_return": float(np.prod(1 + pnl) - np.prod(1 + bench)),
    "info_ratio": _sharpe(excess),
    "last_date": str(prices.index[-1].date()),
    "last_forecast": fwd,
    "last_forecast_as_of": str(prices.index[-1].date()),
}}))
"""


def score_model(code: str, csv_path: str) -> tuple[dict | None, str | None]:
    """Score one submission. Returns (result, error); exactly one is non-None.

    The error string is written back to the model row so its author can see why nothing scored —
    silent failure is the worst possible feedback on a competition site.
    """
    try:
        validate(code)
    except Rejected as e:
        return None, f"rejected: {e}"
    script = RUNNER.format(csv=csv_path, user_code=code, window=WINDOW, cost_bps=COST_BPS)
    try:
        out = run_sandboxed(script, timeout=TIMEOUT, cpu_seconds=TIMEOUT - 15)
    except subprocess.TimeoutExpired:
        return None, f"timed out after {TIMEOUT}s"
    if out.returncode != 0:
        return None, f"crashed: {(out.stderr.strip().splitlines() or ['(no output)'])[-1][:300]}"
    try:
        return json.loads(out.stdout.strip().splitlines()[-1]), None
    except (ValueError, IndexError):
        return None, "produced no parsable result"


def update_live_track(mid: str, as_of: str, forecast, dates: list[str], closes: list[float],
                      chash: str) -> dict:
    """Persist this model's daily forward call, realize any past calls now that the next session is
    known, and return the live (forward-only, since-first-call) aggregates. This is the genuine
    live track that accumulates from when a model went active — distinct from the 252-day backtest.

    Aggregates cover only forecasts stamped with `chash`, the current code's hash. A submission can
    be edited in place (sp500-actions.ts refreshes the code on the same row so the track survives),
    which previously left the live Sharpe averaging over forecasts from code that no longer existed
    while the backtest reflected only the new code — two columns describing two different models.
    Scoping to the current hash means an edit restarts the live track, which is the honest reading:
    the new code has no forward record yet.
    """
    idx = {d: i for i, d in enumerate(dates)}

    if HAS_CODE_HASH:
        # One-time backfill for rows written before forecasts carried a hash. They can only be
        # attributed to whatever code is present now; after this pass every row is explicitly stamped.
        _req("PATCH", f"/sp500_forecasts?model_id=eq.{mid}&code_hash=is.null", {"code_hash": chash})

    if as_of is not None and forecast is not None:
        row = {"model_id": mid, "as_of": as_of, "forecast": forecast}
        if HAS_CODE_HASH:
            row["code_hash"] = chash
        _req("POST", "/sp500_forecasts?on_conflict=model_id,as_of", row)

    # Realize past forecasts whose next session now exists (next-session return after as_of).
    pending = _req("GET", f"/sp500_forecasts?model_id=eq.{mid}&realized=is.null&select=as_of,forecast") or []
    for row in pending:
        i = idx.get(row["as_of"])
        if i is None or i + 1 >= len(closes):
            continue
        realized = closes[i + 1] / closes[i] - 1.0
        s = 1 if row["forecast"] > 0 else (-1 if row["forecast"] < 0 else 0)
        _req("PATCH", f"/sp500_forecasts?model_id=eq.{mid}&as_of=eq.{row['as_of']}",
             {"realized": realized, "pnl": s * realized})

    # Aggregate from the forecast series rather than the stored per-row pnl: costs depend on the
    # position *change* between consecutive sessions, which a single row cannot know. The stored
    # pnl stays gross; net is derived here, so the cost model can change without a backfill.
    scope = f"&code_hash=eq.{chash}" if HAS_CODE_HASH else ""
    rows = _req("GET", f"/sp500_forecasts?model_id=eq.{mid}&realized=not.is.null{scope}"
                       "&select=as_of,forecast,realized&order=as_of.asc") or []
    import numpy as np
    if not rows:
        return {"live_days": 0, "live_sharpe": None, "live_hit_rate": None,
                "live_cum_return": None, "live_info_ratio": None, "live_turnover": None,
                "live_daily_sharpe": None, "live_skew": None, "live_kurtosis": None}

    bench = np.array([r["realized"] for r in rows], dtype=float)
    sign = np.array([1 if r["forecast"] > 0 else (-1 if r["forecast"] < 0 else 0) for r in rows],
                    dtype=float)
    turn = np.abs(np.diff(np.concatenate([[0.0], sign])))    # first session opens from flat
    pnls = sign * bench - (COST_BPS / 10000.0) * turn
    excess = pnls - bench
    nz = sign != 0

    def ann(x):
        return float(np.sqrt(252) * x.mean() / x.std()) if x.std() > 1e-12 else 0.0

    sd = pnls.std()
    daily_sharpe = float(pnls.mean() / sd) if sd > 1e-12 else 0.0
    return {
        "live_days": int(len(pnls)),
        "live_sharpe": ann(pnls),
        "live_hit_rate": float((bench[nz] * sign[nz] > 0).mean()) if nz.any() else 0.0,
        "live_cum_return": float(np.prod(1 + pnls) - 1),
        "live_info_ratio": ann(excess),
        "live_turnover": float((turn > 0).mean()),
        # Carried for the board-level deflated Sharpe, which needs per-period units and the
        # distribution's shape.
        "live_daily_sharpe": daily_sharpe,
        "live_skew": float(((pnls - pnls.mean()) ** 3).mean() / sd ** 3) if sd > 1e-12 else 0.0,
        "live_kurtosis": float(((pnls - pnls.mean()) ** 4).mean() / sd ** 4) if sd > 1e-12 else 3.0,
    }


def main():
    import pandas as pd
    import yfinance as yf
    df = yf.download("^GSPC", period="3y", auto_adjust=True, progress=False)
    close = df["Close"]
    if isinstance(close, pd.DataFrame):          # yfinance may return a 1-column frame
        close = close.iloc[:, 0]
    csv = os.path.join(tempfile.gettempdir(), "gspc.csv")
    close.to_frame("close").to_csv(csv)
    print(f"^GSPC: {len(close)} days through {close.index[-1].date()}")

    dates = [d.date().isoformat() for d in close.index]
    closes = [float(v) for v in close.values]

    global HAS_CODE_HASH, HAS_EXTRA_SCORE_COLS
    HAS_CODE_HASH = _column_exists("sp500_forecasts", "code_hash")
    if not HAS_CODE_HASH:
        print("   note: sp500_forecasts.code_hash absent — live track unscoped until the migration "
              "(20260731_sp500_forecast_code_hash.sql) is applied")
    HAS_EXTRA_SCORE_COLS = _column_exists("sp500_scores", "live_deflated_sharpe")
    if not HAS_EXTRA_SCORE_COLS:
        print("   note: cost/benchmark/deflation columns absent — scoring still applies costs, but "
              "they aren't published until 20260731_sp500_costs_and_deflation.sql is applied")

    has_status = _column_exists("sp500_models", "last_error")
    if not has_status:
        print("   note: sp500_models.last_error absent — submitters won't see why a model failed "
              "until 20260731_sp500_model_status.sql is applied")

    def set_status(mid: str, error: str | None) -> None:
        """Record why a model did or didn't score, so its author isn't left guessing."""
        if not has_status:
            return
        _req("PATCH", f"/sp500_models?id=eq.{mid}",
             {"last_error": error,
              "last_run_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})

    models = fetch_models()
    print(f"scoring {len(models)} models...")

    # Pass 1 — score every model. Deflating a Sharpe needs to know what the whole field looks like,
    # so nothing can be finalised until all of them are in.
    scored: list[tuple[dict, dict, dict]] = []
    for m in models:
        try:
            res, err = score_model(m["code"], csv)
        except Exception as e:                            # one bad model must not end the run
            res, err = None, f"runner error: {type(e).__name__}: {e}"[:400]
        if res is None:
            print(f"   {m['name']:28} skipped — {err}")
            set_status(m["id"], err)
            continue
        live = update_live_track(m["id"], res.get("last_forecast_as_of"), res.get("last_forecast"),
                                 dates, closes, code_hash(m["code"]))
        scored.append((m, res, live))
        set_status(m["id"], None)

    # Pass 2 — deflate against the field. The spread of daily Sharpes across entrants is what sets
    # how high the luckiest of them would be expected to land.
    import numpy as np
    dailies = [lv["live_daily_sharpe"] for _, _, lv in scored if lv.get("live_daily_sharpe") is not None]
    sharpe_var = float(np.var(dailies)) if len(dailies) > 1 else 0.0
    n_trials = max(len(models), 1)
    if sharpe_var > 0:
        bar = stats.expected_max_sharpe(n_trials, sharpe_var) * math.sqrt(252)
        print(f"selection bar: best-of-{n_trials} under the null ≈ {bar:+.2f} annualised Sharpe")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for m, res, live in scored:
        dsr = None
        if live.get("live_daily_sharpe") is not None and live["live_days"] > 1:
            dsr = stats.deflated_sharpe(
                live["live_daily_sharpe"], live["live_days"], n_trials, sharpe_var,
                skew=live.get("live_skew") or 0.0, kurtosis=live.get("live_kurtosis") or 3.0)
        # Shape stats are inputs to the deflation, not board columns.
        live_cols = {k: v for k, v in live.items()
                     if k not in ("live_daily_sharpe", "live_skew", "live_kurtosis")}
        payload = {"model_id": m["id"], **res, **live_cols, "live_deflated_sharpe": dsr,
                   "updated_at": now}
        if not HAS_EXTRA_SCORE_COLS:
            payload = {k: v for k, v in payload.items() if k not in EXTRA_SCORE_COLS}
        _req("POST", "/sp500_scores?on_conflict=model_id", payload)
        ls = live["live_sharpe"]
        live_str = (f"{live['live_days']}d sharpe={ls:+.2f}" if ls is not None
                    else f"{live['live_days']}d (no realized yet)")
        dsr_str = f"  dsr={dsr:.2f}" if dsr is not None else ""
        print(f"   {m['name']:28} backtest sharpe={res['sharpe']:+.2f}  |  live {live_str}{dsr_str}")


if __name__ == "__main__":
    main()
