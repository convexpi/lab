# convexpi-lab

Synthetic equity panel generator, walk-forward backtester, and anti-overfitting grader for quantitative finance education and research.

```bash
pip install convexpi-lab
```

Part of the [ConvexPi](https://convexpi.ai) platform. See also [convexpi-arena](https://github.com/convexpi/arena) for the live exchange simulator.

## Quick start

```python
from convexpi.lab import SyntheticMarket, Backtest, LongShortRank

market = SyntheticMarket(n_stocks=50, n_days=756, seed=42)
result = Backtest(market).run(LongShortRank(feature='mom_1m'))
print(f"OOS Sharpe: {result.oos_sharpe:.3f}")
```

## Graded submission

```python
from convexpi.lab import Strategy, Grader
import numpy as np

class MyStrategy(Strategy):
    def on_day(self, day, features, prices, portfolio):
        sig = features['mom_1m']
        total = np.abs(sig).sum()
        return sig / total if total > 0 else np.zeros(len(prices))

report = Grader().grade(MyStrategy)
print(f"IS Sharpe: {report.is_sharpe:.3f}  OOS Sharpe: {report.oos_sharpe:.3f}")
print(f"Overfitting ratio: {report.overfitting_ratio:.2%}")
```

## Features

- Synthetic equity panel with planted alpha signals of known strength
- Walk-forward backtester with transaction costs and turnover limits
- Hidden-holdout grader — OOS data never seen during development
- Alpha discovery detection — did you find the planted signal or fit noise?
- 19 canonical strategy implementations (momentum, value, quality, size, risk-based)
- Real-data mode: Ken French factors, FRED macro, yfinance prices (optional)
- Anomaly graveyard: pre/post-publication Sharpe decay for 6 canonical factors
- Forward paper-trading scorer (nightly, via GitHub Actions)

## Optional dependencies

```bash
pip install "convexpi-lab[real-data]"   # yfinance + pandas-datareader
pip install "convexpi-lab[deploy]"      # supabase + sentry (grader worker)
```

## License

MIT © Shane Conway
