"""
sandbox.py — validate and execute untrusted, user-submitted Python.

The competition runners execute code that anyone on the internet can submit. The original guard was
a substring blocklist (`"import os" in code.lower()`), which is not a guard at all: `import  os`
with two spaces passes it, as does building the name at runtime
(`__builtins__.__dict__['__imp' + 'ort__']`). Worse, the child inherited the parent's environment,
so anything that got through could read SUPABASE_SERVICE_KEY straight out of `os.environ`.

This module replaces that with three independent layers:

1. `validate()` — an AST walk. Imports must be on an allowlist, and the escape hatches (`eval`,
   `getattr`, dunder attribute access, …) are rejected outright. Because it parses rather than
   greps, whitespace and string-concatenation tricks don't help.
2. `child_env()` — a minimal environment. The child never sees the service key, the GitHub token,
   or anything else the parent holds, so a successful escape still has no credentials to steal.
3. `run()` — POSIX resource limits (CPU, address space, file size, no new processes) and an
   isolated working directory, so runaway or malicious code can't exhaust the host or fork-bomb.

This is defence in depth, not true isolation. A determined escape through a C extension is still
conceivable, and only a container or VM boundary closes that. `deploy/Dockerfile.grader` already
carries the container pattern (`--network none --read-only --memory 512m`); routing this runner
through it is the next step if the threat model warrants it. What's here removes the trivially
exploitable paths and, critically, removes the credentials from the blast radius.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile

# Third-party modules a forecasting model has a legitimate reason to import. Everything else — os,
# sys, socket, subprocess, ctypes, importlib, pickle — is denied by omission rather than listed,
# so a module nobody thought of is denied rather than allowed.
ALLOWED_IMPORTS = frozenset({
    "numpy", "pandas", "scipy", "sklearn", "statsmodels",
    "math", "statistics", "random", "decimal", "fractions",
    "itertools", "functools", "operator", "collections", "heapq", "bisect",
    "datetime", "typing", "dataclasses", "enum", "abc", "warnings",
})

# Builtins that turn "run this arithmetic" into "run anything". `getattr`/`setattr` are here because
# they reach dunders dynamically, which is exactly what the dunder rule below is meant to stop.
FORBIDDEN_NAMES = frozenset({
    "eval", "exec", "compile", "open", "input", "breakpoint", "__import__",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "memoryview", "exit", "quit", "help", "copyright", "credits", "license",
})

MAX_CODE_BYTES = 20_000


class Rejected(Exception):
    """Submitted code failed validation. The message is safe to show the submitter."""


def validate(code: str) -> None:
    """Raise `Rejected` if `code` is not a plain, self-contained predictor.

    Checks the AST, so formatting tricks (`import  os`) and dynamic name construction
    (`'__imp' + 'ort__'`) cannot slip past the way they do with substring matching.
    """
    if len(code.encode()) > MAX_CODE_BYTES:
        raise Rejected(f"Code exceeds {MAX_CODE_BYTES} bytes.")

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise Rejected(f"Syntax error on line {e.lineno}: {e.msg}") from None

    for node in ast.walk(tree):
        # Imports: allowlisted top-level package only.
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    raise Rejected(f"Import of '{alias.name}' is not allowed (line {node.lineno}).")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if node.level:                       # `from . import x` — no package to import from
                raise Rejected(f"Relative imports are not allowed (line {node.lineno}).")
            if root not in ALLOWED_IMPORTS:
                raise Rejected(f"Import from '{node.module}' is not allowed (line {node.lineno}).")

        # Dunder attribute access — the standard route from any object back to the interpreter
        # (`().__class__.__bases__[0].__subclasses__()`).
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                raise Rejected(f"Access to '{node.attr}' is not allowed (line {node.lineno}).")

        # Dunder names and the dangerous builtins, however they're referenced.
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                raise Rejected(f"Use of '{node.id}' is not allowed (line {node.lineno}).")
            if node.id.startswith("__") and node.id.endswith("__"):
                raise Rejected(f"Use of '{node.id}' is not allowed (line {node.lineno}).")

        # Dunder string constants, which only exist to be fed to a dynamic lookup.
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value
            if len(v) > 4 and v.startswith("__") and v.endswith("__"):
                raise Rejected(f"String '{v}' is not allowed (line {node.lineno}).")

    if not any(isinstance(n, ast.FunctionDef) and n.name == "predict" for n in tree.body):
        raise Rejected("Code must define a top-level function named predict(history).")


def child_env(tmpdir: str) -> dict[str, str]:
    """A minimal environment for the child — no inherited secrets.

    The runner holds SUPABASE_SERVICE_KEY (and, under GitHub Actions, a job token). Untrusted code
    has no business seeing either, and stripping them means even a full escape finds nothing to
    exfiltrate.
    """
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": tmpdir,
        "TMPDIR": tmpdir,
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        # BLAS threads: keep the CPU rlimit meaningful and results reproducible.
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }


def _limits(cpu_seconds: int, memory_mb: int):
    """Build a preexec_fn applying POSIX rlimits, or None where `resource` is unavailable."""
    try:
        import resource
    except ImportError:                                    # non-POSIX; caller still gets the timeout
        return None

    def _set(which: int, soft: int) -> None:
        """Lower one limit, never raising. Anything that fails here must not kill a legitimate run.

        The soft limit is clamped to the inherited hard limit — asking for more than the hard limit
        is a ValueError, and an unprivileged process cannot raise the hard limit back up.
        """
        try:
            _, hard = resource.getrlimit(which)
            if hard != resource.RLIM_INFINITY:
                soft = min(soft, hard)
            resource.setrlimit(which, (soft, hard))
        except (ValueError, OSError, AttributeError):
            pass

    def apply() -> None:
        # CPU seconds — catches an infinite loop that a wall-clock timeout would only catch later.
        _set(resource.RLIMIT_CPU, cpu_seconds)
        # Files: enough for scratch, not enough to fill the disk.
        _set(resource.RLIMIT_FSIZE, 32 * 1024 * 1024)
        _set(resource.RLIMIT_CORE, 0)
        # Address space. Skipped on macOS: the allocator reserves large virtual regions there, so an
        # RLIMIT_AS low enough to be useful stops numpy from importing at all. Linux — where the
        # runner actually executes — enforces it.
        if sys.platform.startswith("linux"):
            _set(resource.RLIMIT_AS, memory_mb * 1024 * 1024)
        # Deliberately no RLIMIT_NPROC: it counts every process owned by the UID, not just this
        # subtree, and pthread_create is charged against it — numpy would fail to import. Blocking
        # subprocess/os at the import allowlist is what stops shelling out here.

    return apply


def run(script: str, *, timeout: int = 60, cpu_seconds: int = 45,
        memory_mb: int = 2048) -> subprocess.CompletedProcess:
    """Execute `script` in a stripped environment, under rlimits, in a throwaway directory.

    `script` is the full program text (harness + submitted code), already validated.
    """
    with tempfile.TemporaryDirectory(prefix="sandbox-") as tmpdir:
        path = os.path.join(tmpdir, "run.py")
        with open(path, "w") as f:
            f.write(script)
        return subprocess.run(
            # -I isolates the interpreter: no PYTHON* env vars, no user site-packages, cwd off
            # sys.path. Not -S — that would drop site-packages and numpy with it.
            [sys.executable, "-I", path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmpdir,
            env=child_env(tmpdir),
            preexec_fn=_limits(cpu_seconds, memory_mb),
        )
