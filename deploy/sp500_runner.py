"""
sp500_runner.py — score the S&P 500 next-day prediction competition on real Yahoo prices.

For each active model (sp500_models.code defines `predict(history) -> float`), we walk forward over the
last ~252 trading days of real ^GSPC data: each day the model sees only history up to that day and
predicts the next session's return; we score the realized move. The result (directional hit-rate,
cumulative PnL, Sharpe) is upserted into sp500_scores. Run daily after the US close — each run folds in
the newest day, so the standings are genuinely live and out-of-sample.

Safety: each model runs in a subprocess with a hard timeout; dangerous imports are blocked.

Env: NEXT_PUBLIC_SUPABASE_URL (or SUPABASE_URL), SUPABASE_SERVICE_KEY.
Run: python deploy/sp500_runner.py
"""
from __future__ import annotations
import datetime
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

URL = (os.environ.get("SUPABASE_URL") or os.environ["NEXT_PUBLIC_SUPABASE_URL"]).rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
WINDOW = 252            # trading days scored
TIMEOUT = 60            # seconds per model
BLOCKED = ("import os", "import sys", "import subprocess", "import socket", "import requests",
           "__import__", "open(", "eval(", "exec(", "urllib", "shutil")


def _req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{URL}/rest/v1{path}", data=data, method=method,
                               headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                                        "Content-Type": "application/json",
                                        "Prefer": "resolution=merge-duplicates,return=minimal"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else None


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
    low = code.lower()
    if any(b in low for b in BLOCKED):
        print("   blocked import in model code")
        return None
    script = RUNNER.format(csv=csv_path, user_code=code, window=WINDOW)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(script)
        path = f.name
    try:
        out = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=TIMEOUT)
        if out.returncode != 0:
            print(f"   model error: {out.stderr.strip()[:200]}")
            return None
        return json.loads(out.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        print("   model timed out")
        return None
    finally:
        os.unlink(path)


def update_live_track(mid: str, as_of: str, forecast, dates: list[str], closes: list[float]) -> dict:
    """Persist this model's daily forward call, realize any past calls now that the next session is
    known, and return the live (forward-only, since-first-call) aggregates. This is the genuine
    live track that accumulates from when a model went active — distinct from the 252-day backtest."""
    idx = {d: i for i, d in enumerate(dates)}
    if as_of is not None and forecast is not None:
        _req("POST", "/sp500_forecasts?on_conflict=model_id,as_of",
             {"model_id": mid, "as_of": as_of, "forecast": forecast})

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

    realized_rows = _req("GET", f"/sp500_forecasts?model_id=eq.{mid}&pnl=not.is.null&select=pnl") or []
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

    models = fetch_models()
    print(f"scoring {len(models)} models...")
    for m in models:
        res = score_model(m["code"], csv)
        if res is None:
            continue
        live = update_live_track(m["id"], res.get("last_forecast_as_of"), res.get("last_forecast"), dates, closes)
        _req("POST", "/sp500_scores?on_conflict=model_id",
             {"model_id": m["id"], **res, **live,
              "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        ls = live["live_sharpe"]
        live_str = f"{live['live_days']}d sharpe={ls:+.2f}" if ls is not None else f"{live['live_days']}d (no realized yet)"
        print(f"   {m['name']:28} backtest sharpe={res['sharpe']:+.2f}  |  live {live_str}")


if __name__ == "__main__":
    main()
