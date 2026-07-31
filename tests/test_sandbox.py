"""Tests for the untrusted-code sandbox.

The `bypasses_old_blocklist` cases all defeat the substring guard this module replaces; they are
kept as named regressions so the point of the change stays visible.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy"))

from sandbox import Rejected, child_env, run, validate  # noqa: E402


GOOD = """
import numpy as np

def predict(history):
    close = history['close'].values
    return float(np.mean(np.diff(close[-5:]) / close[-5:-1]))
"""


def test_accepts_a_plain_predictor():
    validate(GOOD)


def test_accepts_allowlisted_imports():
    validate("import pandas as pd\nfrom math import sqrt\ndef predict(h):\n    return sqrt(1.0)\n")


def test_requires_predict():
    with pytest.raises(Rejected, match="predict"):
        validate("import numpy as np\ndef forecast(h):\n    return 0.0\n")


def test_rejects_syntax_error():
    with pytest.raises(Rejected, match="Syntax error"):
        validate("def predict(h)\n    return 0\n")


def test_rejects_oversized_code():
    with pytest.raises(Rejected, match="exceeds"):
        validate("def predict(h):\n    return 0.0\n# " + "x" * 20_001)


@pytest.mark.parametrize("code,name", [
    ("import os\ndef predict(h):\n    return 0.0\n", "plain import os"),
    ("import subprocess\ndef predict(h):\n    return 0.0\n", "import subprocess"),
    ("import socket\ndef predict(h):\n    return 0.0\n", "import socket"),
    ("import ctypes\ndef predict(h):\n    return 0.0\n", "import ctypes"),
    ("from os import environ\ndef predict(h):\n    return 0.0\n", "from os import"),
    ("import os.path\ndef predict(h):\n    return 0.0\n", "dotted import"),
])
def test_rejects_dangerous_imports(code, name):
    with pytest.raises(Rejected):
        validate(code)


@pytest.mark.parametrize("code,name", [
    # Whitespace defeats a substring blocklist; it does not defeat an AST walk.
    ("import  os\ndef predict(h):\n    return 0.0\n",
     "double-space import"),
    ("import\tos\ndef predict(h):\n    return 0.0\n",
     "tab import"),
    # Name built at runtime, so the literal '__import__' never appears.
    ("def predict(h):\n    f = globals()['__buil' + 'tins__']\n    return 0.0\n",
     "concatenated dunder"),
    # The classic route from any object back to the interpreter.
    ("def predict(h):\n    return ().__class__.__bases__[0].__subclasses__()\n",
     "subclasses walk"),
    # getattr reaches dunders without the literal appearing as an attribute.
    ("def predict(h):\n    return getattr(h, '__class__')\n",
     "getattr indirection"),
    # eval/exec with the call spelled indirectly.
    ("def predict(h):\n    e = eval\n    return e('1+1')\n",
     "aliased eval"),
    ("def predict(h):\n    return open('/etc/passwd').read()\n",
     "open"),
])
def test_bypasses_old_blocklist_are_rejected(code, name):
    with pytest.raises(Rejected):
        validate(code)


# --------------------------------------------------------------------------------------------
# Execution layer
# --------------------------------------------------------------------------------------------

def test_child_env_carries_no_secrets(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "super-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_secret")
    env = child_env("/tmp/x")
    assert "SUPABASE_SERVICE_KEY" not in env
    assert "GITHUB_TOKEN" not in env
    assert "super-secret" not in "".join(env.values())


def test_child_cannot_read_parent_secrets(monkeypatch):
    """End to end: even code that reaches os.environ finds nothing worth taking."""
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "super-secret")
    out = run("import os\nprint(os.environ.get('SUPABASE_SERVICE_KEY'))\n", timeout=30)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "None"


def test_numpy_and_pandas_still_import():
    """The isolation flags must not break the libraries a real model needs."""
    out = run("import numpy, pandas\nprint('ok')\n", timeout=60)
    assert out.returncode == 0, out.stderr
    assert "ok" in out.stdout


def test_runaway_loop_is_killed():
    """Either mechanism is fine — the CPU rlimit (SIGXCPU) or the wall-clock timeout."""
    try:
        out = run("while True:\n    pass\n", timeout=20, cpu_seconds=3)
    except subprocess.TimeoutExpired:
        return
    assert out.returncode != 0, "runaway loop exited cleanly — no limit was enforced"
