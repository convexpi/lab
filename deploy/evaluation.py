"""Trusted hosted scoring. The child sees only current observations and returns decisions."""
import json
from pathlib import Path

import numpy as np
from convexpi.lab import Grader

try:
    from .sandbox import Session, SandboxError
except ImportError:
    from sandbox import Session, SandboxError

HARNESSES = Path(__file__).with_name('harnesses')


class StrategyProcess:
    def __init__(self, code, language='python', *, timeout=60, mode='lab'):
        ext, executable = {'python': ('py', '/usr/local/bin/python'),
                           'r': ('R', '/usr/bin/Rscript'),
                           'julia': ('jl', '/usr/local/bin/julia')}[language]
        if mode != 'lab' and language != 'python':
            raise ValueError('forecasting requires Python')
        self.language = language
        self.session = Session(
            {f'strategy.{ext}': code, f'harness.{ext}': (HARNESSES / f'strategy.{ext}').read_text()},
            [executable, *(['-I'] if language == 'python' else ['--compiled-modules=no'] if language == 'julia' else []),
             f'/submission/harness.{ext}', mode], timeout=timeout, cpu_seconds=timeout)

    def __enter__(self):
        self.session.__enter__()
        try:
            # Read initialization without advancing strategy state.
            if self.session.receive() != 'ready':
                raise SandboxError('strategy did not initialize the decision protocol')
            return self
        except BaseException:
            self.session.close()
            raise

    def __exit__(self, *args):
        self.session.__exit__(*args)

    def on_day(self, day, features, prices, portfolio):
        if self.language == 'python':
            message = json.dumps(dict(day=day, features={k: v.tolist() for k, v in features.items()},
                                      prices=prices.tolist(), portfolio=portfolio.tolist()))
            result = json.loads(self.session.exchange(message))
        else:
            def vector(v):
                return ','.join(str(float(x)) for x in v)
            lines = [str(day), vector(prices), vector(portfolio), str(len(features))]
            for name, values in features.items():
                lines += [name, vector(values)]
            raw = self.session.exchange('\n'.join(lines))
            result = [float(x) for x in raw.split(',')]
        weights = np.asarray(result, dtype=float)
        if weights.shape != prices.shape or not np.isfinite(weights).all():
            raise SandboxError('strategy must return one finite weight per stock')
        gross = np.abs(weights).sum()
        if not np.isfinite(gross):
            raise SandboxError('strategy weights overflowed')
        return weights / gross if gross > 1 else weights

    def predict(self, history):
        result = json.loads(self.session.exchange(json.dumps({
            'dates': history.index.astype(str).tolist(), 'close': history['close'].tolist()})))
        value = float(result)
        if not np.isfinite(value):
            raise SandboxError('forecast must be finite')
        return value


def score_strategy(strategy, prices, features, backtest):
    """Collect bounded decisions before computing returns in the trusted process.

    Unlike the notebook backtester, protocol errors fail the hosted submission rather
    than being silently replaced with cash. No future price/feature is sent to the child.
    """
    t_count, n = prices.shape
    warmup = min(backtest.warmup_days, t_count - 2)
    weights = np.zeros_like(prices, dtype=float)
    portfolio = np.zeros(n)
    for t in range(warmup, t_count - 1):
        if (t - warmup) % backtest.rebalance_every == 0:
            portfolio = strategy.on_day(t, {k: v[t] for k, v in features.items()}, prices[t], portfolio)
        weights[t + 1] = portfolio
    return backtest.run_from_weights(weights, prices)


def grade_code(code, language, market, *, timeout=60):
    grader = Grader(market)
    with StrategyProcess(code, language, timeout=timeout) as strategy:
        ins = score_strategy(strategy, market.prices('train'), market.features('train'), grader._backtest)
        oos = score_strategy(strategy, market.prices('test'), market.features('test'), grader._backtest)
    return grader._report_from_results('MyStrategy', ins, oos)


def report_dict(report):
    return dict(is_sharpe=report.is_sharpe, oos_sharpe=report.oos_sharpe,
                overfitting_ratio=report.overfitting_ratio,
                is_max_dd=report.is_max_dd, oos_max_dd=report.oos_max_dd,
                is_annual_return=report.is_result.annualized_return,
                oos_annual_return=report.oos_result.annualized_return,
                is_turnover=report.is_result.turnover_annual, oos_turnover=report.oos_result.turnover_annual,
                alphas_discovered=sum(d.discovered for d in report.alpha_discovery),
                total_alphas=len(report.alpha_discovery),
                alpha_details=[dict(feature=d.feature, planted_bps=d.planted_strength_bps,
                                    corr=d.correlation, discovered=d.discovered, signal_ir=d.oos_contribution)
                               for d in report.alpha_discovery], noise_loadings=report.noise_loadings)
