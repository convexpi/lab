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
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import Rejected, run as run_sandboxed, validate  # noqa: E402

URL = (os.environ.get("SUPABASE_URL") or os.environ["NEXT_PUBLIC_SUPABASE_URL"]).rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
WINDOW = 252            # trading days scored
TIMEOUT = 60            # seconds per model


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
pnl, hits, bets = [], 0, 0
for i in range(start, n - 1):
    hist = prices.iloc[:i + 1]
    try:
        p = float(predict(hist))
    except Exception:
        p = 0.0
    realized = close[i + 1] / close[i] - 1.0
    s = 1 if p > 0 else (-1 if p < 0 else 0)
    pnl.append(s * realized)
    if s != 0:
        bets += 1
        hits += int(s == (1 if realized > 0 else -1))
pnl = np.array(pnl)
sharpe = float(np.sqrt(252) * pnl.mean() / pnl.std()) if pnl.std() > 1e-12 else 0.0
# The model's live call for the NEXT (unrealized) session: predict on the full history.
try:
    fwd = float(predict(prices))
except Exception:
    fwd = 0.0
print(json.dumps({{
    "n_days": int(len(pnl)),
    "hit_rate": (hits / bets) if bets else 0.0,
    "cum_return": float(np.prod(1 + pnl) - 1),
    "sharpe": sharpe,
    "last_date": str(prices.index[-1].date()),
    "last_forecast": fwd,
    "last_forecast_as_of": str(prices.index[-1].date()),
}}))
"""


def score_model(code: str, csv_path: str) -> dict | None:
    try:
        validate(code)
    except Rejected as e:
        print(f"   rejected: {e}")
        return None
    script = RUNNER.format(csv=csv_path, user_code=code, window=WINDOW)
    try:
        out = run_sandboxed(script, timeout=TIMEOUT, cpu_seconds=TIMEOUT - 15)
    except subprocess.TimeoutExpired:
        print("   model timed out")
        return None
    if out.returncode != 0:
        print(f"   model error: {out.stderr.strip()[:200]}")
        return None
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("   model produced no parsable result")
        return None


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

    scope = f"&code_hash=eq.{chash}" if HAS_CODE_HASH else ""
    realized_rows = _req(
        "GET", f"/sp500_forecasts?model_id=eq.{mid}&pnl=not.is.null{scope}&select=pnl") or []
    import numpy as np
    pnls = np.array([r["pnl"] for r in realized_rows], dtype=float)
    if not len(pnls):
        return {"live_days": 0, "live_sharpe": None, "live_hit_rate": None, "live_cum_return": None}
    nz = pnls[pnls != 0]
    return {
        "live_days": int(len(pnls)),
        "live_sharpe": float(np.sqrt(252) * pnls.mean() / pnls.std()) if pnls.std() > 1e-12 else 0.0,
        "live_hit_rate": float((nz > 0).mean()) if len(nz) else 0.0,
        "live_cum_return": float(np.prod(1 + pnls) - 1),
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

    global HAS_CODE_HASH
    HAS_CODE_HASH = _column_exists("sp500_forecasts", "code_hash")
    if not HAS_CODE_HASH:
        print("   note: sp500_forecasts.code_hash absent — live track unscoped until the migration "
              "(20260731_sp500_forecast_code_hash.sql) is applied")

    models = fetch_models()
    print(f"scoring {len(models)} models...")
    for m in models:
        res = score_model(m["code"], csv)
        if res is None:
            continue
        live = update_live_track(m["id"], res.get("last_forecast_as_of"), res.get("last_forecast"),
                                 dates, closes, code_hash(m["code"]))
        _req("POST", "/sp500_scores?on_conflict=model_id",
             {"model_id": m["id"], **res, **live,
              "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        ls = live["live_sharpe"]
        live_str = f"{live['live_days']}d sharpe={ls:+.2f}" if ls is not None else f"{live['live_days']}d (no realized yet)"
        print(f"   {m['name']:28} backtest sharpe={res['sharpe']:+.2f}  |  live {live_str}")


if __name__ == "__main__":
    main()
