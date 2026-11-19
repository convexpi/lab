"""Execution boundary for hosted, untrusted code.

Validation gives early feedback only: Python libraries expose capabilities that an
AST allowlist cannot contain. Every hosted execution requires a Docker container;
missing configuration/runtime fails closed. Never mount credentials or market data.
"""
from __future__ import annotations

import ast
import os
import subprocess
import tempfile
import selectors
import time
import threading
import uuid

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
    "sys", "os", "subprocess", "socket", "ctypes", "importlib", "memoryview", "exit", "quit", "help", "copyright", "credits", "license",
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
            if any(a.name in FORBIDDEN_NAMES or a.name.startswith("_") or a.name == "*" for a in node.names):
                raise Rejected(f"Unsafe imported name (line {node.lineno}).")
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
        "PATH": "/usr/local/bin:/usr/bin:/bin",
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


class SandboxUnavailable(RuntimeError):
    """No configured, working container runtime. Never fall back to host execution."""


class SandboxError(RuntimeError):
    """The strategy process exited or violated the bounded response protocol."""


class Session:
    """A credential-free container, exchanging one bounded line at a time.

    Only the supplied code/harness files are mounted. The market, worker filesystem,
    daemon socket and deployment environment are never exposed to the container.
    The deadline covers startup and every request, including blocked writes.
    """
    def __init__(self, files, command, *, timeout=60, memory_mb=2048, cpu_seconds=45):
        self.files, self.command = files, command
        self.timeout, self.memory_mb, self.cpu_seconds = timeout, memory_mb, cpu_seconds
        self.proc = None
        self.tmp = None
        self.name = "convexpi-" + uuid.uuid4().hex
        self.buffer = bytearray()
        self.deadline = 0.0
        self.stderr = b""
        self.stderr_thread = None

    def __enter__(self):
        image = os.environ.get("GRADER_DOCKER_IMAGE")
        if not image:
            raise SandboxUnavailable("GRADER_DOCKER_IMAGE is required; host execution is disabled")
        self.tmp = tempfile.TemporaryDirectory(prefix="convexpi-sandbox-")
        try:
            # The unprivileged container user needs read access to these non-secret files.
            os.chmod(self.tmp.name, 0o755)
            for name, content in self.files.items():
                if name != os.path.basename(name):
                    raise ValueError("sandbox file names must be basenames")
                path = os.path.join(self.tmp.name, name)
                with open(path, "w") as f:
                    f.write(content)
                os.chmod(path, 0o644)
            cmd = ["docker", "run", "--rm", "--pull=never", "--name", self.name,
                   "--network=none", "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges", "--user=65534:65534",
                   "--pids-limit=64", "--memory", f"{self.memory_mb}m",
                   "--memory-swap", f"{self.memory_mb}m", "--cpus=1",
                   "--ulimit", f"cpu={self.cpu_seconds}:{self.cpu_seconds}",
                   "--ulimit", "fsize=33554432:33554432", "--ulimit", "core=0:0",
                   "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m,mode=1777",
                   "--mount", f"type=bind,src={self.tmp.name},dst=/submission,readonly",
                   "--workdir=/tmp", "--log-driver=none", "-i"]
            # Explicit values only; never `-e NAME`, which copies from the host.
            for key, value in child_env("/tmp").items():
                cmd += ["--env", f"{key}={value}"]
            cmd += ["--entrypoint", self.command[0], image, *self.command[1:]]
            self.deadline = time.monotonic() + self.timeout
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, bufsize=0)
            error_pipe = self.proc.stderr

            def drain_errors():
                try:
                    while chunk := error_pipe.read(4096):
                        self.stderr = (self.stderr + chunk)[-4096:]
                except (OSError, ValueError):
                    pass  # cleanup may close a pipe after stopping the Docker client
            self.stderr_thread = threading.Thread(target=drain_errors, daemon=True)
            self.stderr_thread.start()
            os.set_blocking(self.proc.stdin.fileno(), False)
            os.set_blocking(self.proc.stdout.fileno(), False)
            return self
        except Exception:
            self.close()
            raise

    def _ready(self, pipe, event):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(self.command, self.timeout)
        with selectors.DefaultSelector() as sel:
            sel.register(pipe, event)
            if not sel.select(remaining):
                raise subprocess.TimeoutExpired(self.command, self.timeout)

    def exchange(self, message):
        raw = (message + "\n").encode()
        if len(raw) > 4 * 1024 * 1024:
            raise SandboxError("input exceeds sandbox request limit")
        view = memoryview(raw)
        while view:
            self._ready(self.proc.stdin, selectors.EVENT_WRITE)
            try:
                written = os.write(self.proc.stdin.fileno(), view)
            except BrokenPipeError as e:
                raise SandboxError("strategy process exited before returning a decision: " + self.stderr.decode("utf-8", errors="replace")[-1000:]) from e
            view = view[written:]
        return self.receive()

    def receive(self):
        while b"\n" not in self.buffer:
            self._ready(self.proc.stdout, selectors.EVENT_READ)
            chunk = os.read(self.proc.stdout.fileno(), 65536)
            if not chunk:
                raise SandboxError("strategy process exited before returning a decision: " + self.stderr.decode("utf-8", errors="replace")[-1000:])
            self.buffer.extend(chunk)
            if len(self.buffer) > 1024 * 1024:
                raise SandboxError("strategy output exceeds sandbox response limit")
        line, _, remaining = self.buffer.partition(b"\n")
        self.buffer = bytearray(remaining)
        return line.decode("utf-8")

    def close(self):
        proc, self.proc = self.proc, None
        try:
            if proc is not None:
                # Killing the Docker client does not kill its container. Remove it
                # explicitly, including descendants, even on a request timeout.
                try:
                    subprocess.run(["docker", "rm", "-f", self.name],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                finally:
                    try:
                        proc.kill()
                        proc.wait(timeout=10)
                    finally:
                        if self.stderr_thread is not None:
                            self.stderr_thread.join(timeout=1)
                        for pipe in (proc.stdin, proc.stdout, proc.stderr):
                            pipe.close()
        finally:
            if self.tmp is not None:
                self.tmp.cleanup()
                self.tmp = None

    def __exit__(self, *_):
        self.close()


def run(script: str, *, timeout=60, cpu_seconds=45, memory_mb=2048):
    """Execute a standalone diagnostic script in the same mandatory container boundary."""
    with Session({"run.py": script}, ["/usr/local/bin/python", "-I", "/submission/run.py"],
                 timeout=timeout, cpu_seconds=cpu_seconds, memory_mb=memory_mb) as session:
        session.proc.stdin.close()
        output = bytearray()
        while True:
            session._ready(session.proc.stdout, selectors.EVENT_READ)
            chunk = os.read(session.proc.stdout.fileno(), 65536)
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > 1024 * 1024:
                raise SandboxError("script output exceeds sandbox response limit")
        session.proc.wait(timeout=max(0.01, session.deadline - time.monotonic()))
        return subprocess.CompletedProcess(session.command, session.proc.returncode, output.decode(), session.stderr.decode("utf-8", errors="replace"))
