"""multilang.py — run a strategy written in another language (R, soon Julia) and score it identically.

The scoring engine (Backtest.run_from_weights → OOS Sharpe, overfitting ratio, alpha discovery) is
Python and language-agnostic. This module only handles the foreign half: export the market, run the
language's harness in a subprocess to produce the weights trajectory, and read it back. So an R
strategy is graded by the exact same code as a Python one.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

# language -> (file extension, harness filename, interpreter argv prefix)
LANGUAGES: dict[str, tuple[str, str, list[str]]] = {
    "r": ("R", "harness.R", ["Rscript"]),
    "julia": ("jl", "harness.jl", ["julia"]),
}

_HARNESS_DIR = Path(__file__).resolve().parent / "harnesses"


class ForeignStrategyError(RuntimeError):
    """The foreign-language strategy failed to run (compile/runtime error, timeout, bad output)."""


def supported_languages() -> list[str]:
    """Languages whose interpreter is actually available on this machine."""
    return [lang for lang, (_e, _h, argv) in LANGUAGES.items() if shutil.which(argv[0])]


def run_language_weights(
    language: str,
    user_code: str,
    prices: np.ndarray,
    features: dict[str, np.ndarray],
    warmup_days: int = 252,
    rebalance_every: int = 1,
    timeout: int = 60,
) -> np.ndarray:
    """Run `user_code` (defining on_day in `language`) over the market; return the (T, N) weights.

    `warmup`/`rebalance` are passed to the harness so its loop matches Backtest exactly; pass the
    SAME warmup_days/rebalance_every you score with."""
    lang = language.lower()
    if lang not in LANGUAGES:
        raise ForeignStrategyError(f"Unsupported language: {language}")
    ext, harness_name, argv = LANGUAGES[lang]
    if not shutil.which(argv[0]):
        raise ForeignStrategyError(f"{argv[0]} is not installed in this environment.")

    T = prices.shape[0]
    warmup = min(warmup_days, T - 2)

    with tempfile.TemporaryDirectory(prefix="convexpi_lab_") as tmp:
        d = Path(tmp)
        np.savetxt(d / "prices.csv", prices, delimiter=",")
        (d / "features").mkdir()
        for name, arr in features.items():
            np.savetxt(d / "features" / f"{name}.csv", arr, delimiter=",")
        user_path = d / f"strategy.{ext}"
        user_path.write_text(user_code)
        out_path = d / "weights.csv"

        cmd = [*argv, str(_HARNESS_DIR / harness_name), str(d), str(user_path),
               str(out_path), str(warmup), str(rebalance_every)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise ForeignStrategyError(f"{language} strategy timed out after {timeout}s.")
        if proc.returncode != 0 or not out_path.exists():
            raise ForeignStrategyError(
                f"{language} strategy failed:\n{(proc.stderr or proc.stdout)[-2000:].strip()}"
            )
        weights = np.loadtxt(out_path, delimiter=",")
        if weights.shape != prices.shape:
            raise ForeignStrategyError(
                f"{language} strategy produced weights of shape {weights.shape}, expected {prices.shape}."
            )
        return np.nan_to_num(weights)
