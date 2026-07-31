"""Scoring-path tests for the S&P next-day runner (no network — score_model is self-contained)."""
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy"))

# Module-level config reads these at import time.
os.environ.setdefault("NEXT_PUBLIC_SUPABASE_URL", "https://example.invalid")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key-not-real")

import sp500_runner as R  # noqa: E402


@pytest.fixture(scope="module")
def csv(tmp_path_factory):
    """A deterministic price series long enough to exercise the 252-day walk-forward."""
    rng = np.random.default_rng(0)
    close = 4000 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 400)))
    idx = pd.bdate_range("2024-01-01", periods=400)
    p = tmp_path_factory.mktemp("data") / "gspc.csv"
    pd.Series(close, index=idx, name="close").to_frame().to_csv(p)
    return str(p)


def test_scores_a_valid_model(csv):
    res, err = R.score_model("import numpy as np\ndef predict(history):\n    return 0.001\n", csv)
    assert err is None and res is not None
    assert res["n_days"] == R.WINDOW
    assert 0.0 <= res["hit_rate"] <= 1.0
    assert np.isfinite(res["sharpe"])
    assert res["last_forecast"] == pytest.approx(0.001)


def _bench_returns(csv):
    close = pd.read_csv(csv, index_col=0)["close"].values
    start = max(1, len(close) - R.WINDOW - 1)
    return close[start + 1:] / close[start:-1] - 1.0


def test_always_long_is_buy_and_hold_less_one_entry_cost(csv):
    """A constant positive forecast is buy-and-hold: it pays to open the position, then never trades."""
    res, _ = R.score_model("def predict(history):\n    return 1.0\n", csv)
    r = _bench_returns(csv).copy()
    r[0] -= R.COST_BPS / 10000.0                      # flat -> long on the first session
    assert res["cum_return"] == pytest.approx(np.prod(1 + r) - 1, rel=1e-9)
    assert res["turnover"] == pytest.approx(1 / len(r))
    # Gross is the index itself, and the drag is exactly the single entry cost.
    assert res["gross_sharpe"] > res["sharpe"]


def test_buy_and_hold_excess_over_itself_is_exactly_its_entry_cost(csv):
    res, _ = R.score_model("def predict(history):\n    return 1.0\n", csv)
    assert res["excess_return"] == pytest.approx(-R.COST_BPS / 10000.0, abs=5e-5)


def test_information_ratio_is_degenerate_for_a_pure_buy_and_hold(csv):
    """Documents a real artifact rather than papering over it.

    Buy-and-hold's excess series is zero every session except the one where it opens the position.
    A series with a single non-zero value has a tiny standard deviation, so mean/sd is about
    -1/sqrt(n-1) regardless of how small that one cost was — the annualised IR lands near -1.0 and
    looks like systematic underperformance when it is one entry fee. The maths is right; the
    statistic is just meaningless on a near-constant series. Any UI showing IR should suppress it
    when the model barely trades.
    """
    res, _ = R.score_model("def predict(history):\n    return 1.0\n", csv)
    assert res["info_ratio"] == pytest.approx(-math.sqrt(252 / (res["n_days"] - 1)), rel=0.02)
    assert res["turnover"] < 0.01, "the artifact is confined to models that barely trade"


def test_costs_penalise_a_daily_flipper(csv):
    """A model that reverses every session must score worse than the same signal traded free."""
    flipper = ("def predict(history):\n"
               "    return 1.0 if len(history) %% 2 == 0 else -1.0\n").replace("%%", "%")
    res, _ = R.score_model(flipper, csv)
    assert res["turnover"] == pytest.approx(1.0), "should trade every session"
    assert res["cost_drag"] > 0.02, "252 daily reversals at 2bp round trip should cost >2%"
    assert res["gross_sharpe"] > res["sharpe"], "costs must lower the reported Sharpe"


def test_holding_flat_pays_nothing(csv):
    res, _ = R.score_model("def predict(history):\n    return 0.0\n", csv)
    assert res["turnover"] == pytest.approx(0.0)
    assert res["cost_drag"] == pytest.approx(0.0)
    assert res["cum_return"] == pytest.approx(0.0)


def test_rejects_code_without_predict(csv):
    res, err = R.score_model("def forecast(history):\n    return 0.0\n", csv)
    assert res is None and "predict" in err


def test_rejects_credential_theft(csv):
    """The attack the old substring blocklist allowed: `import  os` with two spaces."""
    res, err = R.score_model(
        "import  os\ndef predict(history):\n    return len(os.environ)\n", csv)
    assert res is None and "rejected" in err


def test_model_raising_is_scored_as_flat_not_crashed(csv):
    """A broken predict() must not take down the run — the harness scores it as no position."""
    res, err = R.score_model("def predict(history):\n    raise ValueError('boom')\n", csv)
    assert err is None and res is not None
    assert res["cum_return"] == pytest.approx(0.0)


def _capture(monkeypatch):
    """Record every REST call update_live_track makes, returning empty results."""
    calls = []

    def fake(method, path, body=None):
        calls.append((method, path, body))
        return []

    monkeypatch.setattr(R, "_req", fake)
    return calls


def test_live_track_scopes_to_current_code_when_column_exists(monkeypatch):
    calls = _capture(monkeypatch)
    monkeypatch.setattr(R, "HAS_CODE_HASH", True)
    R.update_live_track("m1", "2026-07-30", 0.5, ["2026-07-30"], [100.0], "abc123")
    assert any(b and b.get("code_hash") == "abc123" for _, _, b in calls), "forecast not stamped"
    assert any("code_hash=eq.abc123" in p for m, p, _ in calls if m == "GET"), "aggregate not scoped"


def test_live_track_degrades_when_column_missing(monkeypatch):
    """A deploy landing before its migration must still score, just without code scoping."""
    calls = _capture(monkeypatch)
    monkeypatch.setattr(R, "HAS_CODE_HASH", False)
    R.update_live_track("m1", "2026-07-30", 0.5, ["2026-07-30"], [100.0], "abc123")
    assert not any(b and "code_hash" in b for _, _, b in calls), "wrote a column that doesn't exist"
    assert not any("code_hash" in p for _, p, _ in calls), "queried a column that doesn't exist"
    assert any(m == "POST" and "sp500_forecasts" in p for m, p, _ in calls), "forecast not recorded"


def test_code_hash_tracks_edits():
    a = "def predict(h):\n    return 0.0\n"
    assert R.code_hash(a) == R.code_hash(a)
    assert R.code_hash(a) != R.code_hash(a + "# tweak\n")
