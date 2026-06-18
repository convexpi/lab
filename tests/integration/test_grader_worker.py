"""
Integration tests for the grader worker.

These tests run the full grade_submission() pipeline against the real
convexpi.lab code (SyntheticMarket + Grader) but mock all Supabase HTTP
calls so no live database is needed.

Run with:
    pytest tests/integration/ -v
"""

from __future__ import annotations

import json
import sys
import os
import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

# ---------------------------------------------------------------------------
# Helpers — build a fake submission dict
# ---------------------------------------------------------------------------

COHORT_ID = "test-cohort-0000-0000-000000000000"
SUB_ID    = "test-sub-00000-0000-0000-000000000000"

VALID_STRATEGY = """
import numpy as np

class MyStrategy:
    def predict(self, features):
        # Single-feature strategy using the first feature
        raw = features[:, 0]
        return (raw - raw.mean()) / (raw.std() + 1e-8)
"""

BLOCKED_STRATEGY = "import os\nclass MyStrategy: pass"
NO_CLASS_STRATEGY = "import numpy as np\ndef fn(): pass"
TIMEOUT_STRATEGY = """
import time, numpy as np
class MyStrategy:
    def predict(self, features):
        time.sleep(9999)
        return np.zeros(features.shape[0])
"""


def make_submission(code: str = VALID_STRATEGY) -> dict:
    return {"id": SUB_ID, "cohort_id": COHORT_ID, "code": code}


# ---------------------------------------------------------------------------
# Fixtures — patch the grader worker's Supabase calls
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    """Set required env vars so the module can be imported."""
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-service-key")
    monkeypatch.setenv("MARKET_SEED", "99")
    monkeypatch.setenv("MARKET_N_STOCKS", "80")   # small market for speed
    monkeypatch.setenv("MARKET_N_DAYS", "500")
    monkeypatch.setenv("GRADE_TIMEOUT", "120")


@pytest.fixture()
def grader_module(env_vars):
    """Import (or re-import) the grader worker with env vars set."""
    # Force fresh import so module-level constants pick up env vars
    mod_name = "deploy.grader_worker"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    # Add repo root to path
    repo_root = str(Path(__file__).parent.parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    import deploy.grader_worker as gw
    return gw


@pytest.fixture()
def mock_supabase(grader_module):
    """Patch all _req calls in the grader worker."""
    results = {
        "mark_running":    None,
        "mark_failed":     None,
        "mark_completed":  None,
        "grade_report":    None,
        "market_config":   {},
    }

    def fake_req(method, path, body=None):
        if method == "PATCH" and "status=eq.running" in path or (body and body.get("status") == "running"):
            results["mark_running"] = body
            return [{}]
        if method == "PATCH" and (body and body.get("status") == "failed"):
            results["mark_failed"] = body
            return [{}]
        if method == "PATCH" and (body and body.get("status") == "completed"):
            results["mark_completed"] = body
            return [{}]
        if method == "POST" and "/grade_reports" in path:
            results["grade_report"] = body
            return [{}]
        if method == "GET" and "/cohorts" in path:
            return [{"market_config": results["market_config"]}]
        return [{}]

    with patch.object(grader_module, "_req", side_effect=fake_req):
        yield results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGradeSubmission:
    def test_valid_strategy_completes(self, grader_module, mock_supabase):
        """A syntactically correct strategy should produce a grade report."""
        grader_module.grade_submission(make_submission(VALID_STRATEGY))

        assert mock_supabase["mark_completed"] is not None, "Should have been marked completed"
        assert mock_supabase["mark_failed"] is None, "Should not have been marked failed"

        report = mock_supabase["grade_report"]
        assert report is not None, "Grade report should have been written"
        assert "oos_sharpe" in report
        assert "is_sharpe" in report
        assert isinstance(report["oos_sharpe"], float)

    def test_grade_report_fields(self, grader_module, mock_supabase):
        """Grade report must contain all expected keys."""
        grader_module.grade_submission(make_submission(VALID_STRATEGY))
        report = mock_supabase["grade_report"]
        required = [
            "is_sharpe", "oos_sharpe", "overfitting_ratio",
            "is_max_dd", "oos_max_dd", "is_annual_return", "oos_annual_return",
            "is_turnover", "oos_turnover",
            "alphas_discovered", "total_alphas",
            "alpha_details", "noise_loadings",
        ]
        for key in required:
            assert key in report, f"Missing key: {key}"

    def test_oos_sharpe_in_plausible_range(self, grader_module, mock_supabase):
        """OOS Sharpe for a reasonable strategy should be finite."""
        grader_module.grade_submission(make_submission(VALID_STRATEGY))
        oos = mock_supabase["grade_report"]["oos_sharpe"]
        assert isinstance(oos, float)
        assert not (oos != oos)  # not NaN
        assert abs(oos) < 20    # sanity check — not infinite

    def test_alphas_discovered_bounds(self, grader_module, mock_supabase):
        """alphas_discovered should be between 0 and total_alphas."""
        grader_module.grade_submission(make_submission(VALID_STRATEGY))
        r = mock_supabase["grade_report"]
        assert 0 <= r["alphas_discovered"] <= r["total_alphas"]

    def test_alpha_details_structure(self, grader_module, mock_supabase):
        """alpha_details should be a list of dicts with expected keys."""
        grader_module.grade_submission(make_submission(VALID_STRATEGY))
        details = mock_supabase["grade_report"]["alpha_details"]
        assert isinstance(details, list)
        for d in details:
            assert "feature" in d
            assert "planted_bps" in d
            assert "discovered" in d
            assert isinstance(d["discovered"], bool)

    def test_blocked_import_fails(self, grader_module, mock_supabase):
        """Code with blocked imports should be marked failed without running."""
        grader_module.grade_submission(make_submission(BLOCKED_STRATEGY))
        assert mock_supabase["mark_failed"] is not None
        assert mock_supabase["mark_completed"] is None
        assert "Blocked" in mock_supabase["mark_failed"].get("error_message", "")

    def test_missing_mystrategy_fails(self, grader_module, mock_supabase):
        """Code without MyStrategy class should be marked failed."""
        grader_module.grade_submission(make_submission(NO_CLASS_STRATEGY))
        assert mock_supabase["mark_failed"] is not None
        assert mock_supabase["mark_completed"] is None

    def test_timeout_fails(self, grader_module, mock_supabase, monkeypatch):
        """Strategy that hangs should time out and be marked failed."""
        import subprocess as _sp
        # Simulate a timeout by making _run_script raise TimeoutExpired directly,
        # avoiding dependence on actual subprocess wall-clock timing.
        def fake_run_script(script_path, tmpdir):
            raise _sp.TimeoutExpired(cmd=["python", script_path], timeout=3)

        monkeypatch.setattr(grader_module, "_run_script", fake_run_script)
        grader_module.grade_submission(make_submission(VALID_STRATEGY))
        assert mock_supabase["mark_failed"] is not None
        assert mock_supabase["mark_completed"] is None
        assert "Timed out" in mock_supabase["mark_failed"].get("error_message", "")

    def test_marks_running_before_grading(self, grader_module, mock_supabase):
        """Submission should be marked running before the subprocess executes."""
        call_order = []
        original_req = grader_module._req

        def tracking_req(method, path, body=None):
            if body and body.get("status") == "running":
                call_order.append("running")
            elif body and body.get("status") in ("completed", "failed"):
                call_order.append(body["status"])
            return original_req(method, path, body)

        with patch.object(grader_module, "_req", side_effect=tracking_req):
            grader_module.grade_submission(make_submission(VALID_STRATEGY))

        assert call_order[0] == "running", "running must be set first"
        assert call_order[-1] == "completed"

    def test_per_cohort_alpha_config(self, grader_module, mock_supabase):
        """market_config planted_alphas override should be passed to SyntheticMarket."""
        mock_supabase["market_config"] = {
            "planted_alphas": [
                {"feature": "mom_1m", "strength_bps": 4.0, "halflife_days": 15}
            ]
        }
        # Should complete without error using the custom alpha config
        grader_module.grade_submission(make_submission(VALID_STRATEGY))
        assert mock_supabase["mark_completed"] is not None

    def test_per_cohort_seed_override(self, grader_module, mock_supabase):
        """market_config seed override should be used by the runner."""
        mock_supabase["market_config"] = {"seed": 7}
        grader_module.grade_submission(make_submission(VALID_STRATEGY))
        assert mock_supabase["mark_completed"] is not None


class TestFetchPending:
    def test_returns_list(self, grader_module):
        """fetch_pending should return a list (even if empty)."""
        with patch.object(grader_module, "_req", return_value=[]):
            result = grader_module.fetch_pending()
        assert isinstance(result, list)

    def test_handles_none_response(self, grader_module):
        """fetch_pending should handle None from _req gracefully."""
        with patch.object(grader_module, "_req", return_value=None):
            result = grader_module.fetch_pending()
        assert result == []
