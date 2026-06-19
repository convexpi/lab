"""
convexpi.lab.submit — submit a strategy to ConvexPi for hidden out-of-sample grading.

Replaces the copy-paste-into-the-web-editor step. Works from a Colab notebook,
a script, or an AI agent — anything that can make an HTTPS request.

    import os
    os.environ["CONVEXPI_API_KEY"] = "cpk_live_…"   # create one at /settings/api-keys

    from convexpi.lab import submit
    submit(MyStrategy, competition="demo-fall-2026", name="my-momentum")

`strategy` may be a `Strategy` subclass or a raw code string. The function POSTs
to the submission API, polls until grading finishes, and prints the OOS Sharpe
plus a leaderboard link.

Environment variables:
    CONVEXPI_API_KEY   your key (or pass api_key=...)
    CONVEXPI_API_URL   base URL (default https://www.convexpi.ai)
"""

from __future__ import annotations

import inspect
import json
import os
import textwrap
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "https://www.convexpi.ai"


class SubmitError(RuntimeError):
    pass


def _to_code(strategy: Any) -> str:
    """Accept a code string or a Strategy class and return submittable source."""
    if isinstance(strategy, str):
        return strategy
    if inspect.isclass(strategy):
        try:
            src = textwrap.dedent(inspect.getsource(strategy))
        except (OSError, TypeError) as exc:
            raise SubmitError(
                "Could not read the class source. Pass the strategy code as a "
                "string instead, e.g. submit(my_code_string, ...)."
            ) from exc
        header = (
            "import numpy as np\n"
            "try:\n"
            "    from convexpi.lab import Strategy\n"
            "except Exception:\n"
            "    pass\n\n"
        )
        alias = "" if strategy.__name__ == "MyStrategy" else f"\n\nMyStrategy = {strategy.__name__}\n"
        return header + src + alias
    raise SubmitError("strategy must be a code string or a Strategy subclass.")


def _request(url: str, api_key: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            msg = json.loads(body).get("error", body)
        except Exception:
            msg = body
        raise SubmitError(f"HTTP {exc.code}: {msg}") from None
    except urllib.error.URLError as exc:
        raise SubmitError(f"Network error reaching {url}: {exc.reason}") from None


def submit(
    strategy: Any,
    *,
    competition: str,
    name: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    wait: bool = True,
    poll_interval: float = 3.0,
    timeout: float = 300.0,
    github_url: str | None = None,
) -> dict:
    """Submit a strategy and (optionally) wait for the grade.

    Parameters
    ----------
    strategy : a Strategy subclass or a code string defining `MyStrategy`.
    competition : the competition slug, e.g. "demo-fall-2026".
    name : strategy name shown on the leaderboard (defaults to the class name).
    api_key : your key, or set CONVEXPI_API_KEY.
    wait : poll until grading completes (default True).

    Returns the final submission record (with `report` when graded).
    """
    api_key = api_key or os.environ.get("CONVEXPI_API_KEY")
    if not api_key:
        raise SubmitError(
            "No API key. Create one at /settings/api-keys, then set "
            'os.environ["CONVEXPI_API_KEY"] = "cpk_live_…" or pass api_key=...'
        )
    base = (base_url or os.environ.get("CONVEXPI_API_URL") or DEFAULT_BASE_URL).rstrip("/")

    code = _to_code(strategy)
    if name is None:
        name = strategy.__name__ if inspect.isclass(strategy) else "strategy"

    body = {"slug": competition, "strategyName": name, "code": code}
    if github_url:
        body["githubUrl"] = github_url

    print(f"Submitting '{name}' to '{competition}'…")
    resp = _request(f"{base}/api/submissions", api_key, method="POST", payload=body)
    sub = resp.get("submission") or resp
    sub_id = sub.get("id")
    if not sub_id:
        raise SubmitError(f"Unexpected response: {resp}")

    lb = f"{base}/compete/{competition}/leaderboard"
    if not wait:
        print(f"Queued. Track it on the leaderboard: {lb}")
        return sub

    print("Grading", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(poll_interval)
        print(".", end="", flush=True)
        status = _request(f"{base}/api/submissions/{sub_id}", api_key)
        st = status.get("status")
        if st == "completed":
            print(" done.")
            r = status.get("report") or {}
            oos, is_ = r.get("oos_sharpe"), r.get("is_sharpe")
            ovr = r.get("overfitting_ratio")
            print(f"\n  OOS Sharpe:        {oos:.3f}" if oos is not None else "\n  OOS Sharpe:        —")
            if is_ is not None:
                print(f"  IS Sharpe:         {is_:.3f}")
            if ovr is not None:
                print(f"  Overfitting ratio: {ovr*100:.0f}%")
            print(f"  Leaderboard:       {lb}")
            return status
        if st == "failed":
            print(" failed.")
            print(f"  Error: {status.get('error_message')}")
            return status

    print(" timed out (still grading).")
    print(f"  Check later: {lb}")
    return sub
