"""Scoring-path tests for the S&P next-day runner (no network — score_model is self-contained)."""
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
    res = R.score_model("import numpy as np\ndef predict(history):\n    return 0.001\n", csv)
    assert res is not None
    assert res["n_days"] == R.WINDOW
    assert 0.0 <= res["hit_rate"] <= 1.0
    assert np.isfinite(res["sharpe"])
    assert res["last_forecast"] == pytest.approx(0.001)


def test_always_long_matches_buy_and_hold(csv):
    """A constant positive forecast is buy-and-hold, so its cumulative PnL must equal the index's."""
    res = R.score_model("def predict(history):\n    return 1.0\n", csv)
    close = pd.read_csv(csv, index_col=0)["close"].values
    start = max(1, len(close) - R.WINDOW - 1)
    expected = close[-1] / close[start] - 1.0
    assert res["cum_return"] == pytest.approx(expected, rel=1e-9)


def test_rejects_code_without_predict(csv):
    assert R.score_model("def forecast(history):\n    return 0.0\n", csv) is None


def test_rejects_credential_theft(csv):
    """The attack the old substring blocklist allowed: `import  os` with two spaces."""
    assert R.score_model(
        "import  os\ndef predict(history):\n    return len(os.environ)\n", csv) is None


def test_model_raising_is_scored_as_flat_not_crashed(csv):
    """A broken predict() must not take down the run — the harness scores it as no position."""
    res = R.score_model("def predict(history):\n    raise ValueError('boom')\n", csv)
    assert res is not None
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
