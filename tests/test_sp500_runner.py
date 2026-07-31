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


def test_code_hash_tracks_edits():
    a = "def predict(h):\n    return 0.0\n"
    assert R.code_hash(a) == R.code_hash(a)
    assert R.code_hash(a) != R.code_hash(a + "# tweak\n")
