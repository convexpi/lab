"""Check the deployed container boundary without reading or changing the submission queue."""
import numpy as np

try:
    from .evaluation import StrategyProcess
except ImportError:
    from evaluation import StrategyProcess


def check_runtime():
    examples = {
        'python': 'class MyStrategy:\n    def on_day(self, day, features, prices, portfolio):\n        return prices * 0 + 1\n',
        'r': 'on_day <- function(day, features, prices, portfolio) rep(1, length(prices))',
        'julia': 'function on_day(day, features, prices, portfolio)\n    ones(length(prices))\nend',
    }
    for language, code in examples.items():
        with StrategyProcess(code, language) as process:
            weights = process.on_day(0, {}, np.ones(2), np.zeros(2))
            np.testing.assert_allclose(weights, [.5, .5])


if __name__ == '__main__':
    check_runtime()
    print('Isolated Python, R, and Julia execution passed; no submissions were accessed.')
