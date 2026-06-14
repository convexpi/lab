"""
Lab demo — synthetic market generation, backtesting, and grading.

Run:
    python examples/lab_demo.py
"""

from convexpi.lab import (
    SyntheticMarket,
    Backtest,
    LongShortRank,
    CombinedSignal,
    EqualWeight,
    Grader,
)


def main():
    print("Generating synthetic market (200 stocks, 5 years)...")
    market = SyntheticMarket(n_stocks=200, n_days=1260, seed=42)
    market.describe()

    grader = Grader(market)

    strategies = {
        "EqualWeight":      EqualWeight(),
        "Momentum(mom_1m)": LongShortRank("mom_1m"),
        "Momentum(mom_3m)": LongShortRank("mom_3m"),
        "Value(val_bm)":    LongShortRank("val_bm"),
        "Noise(noise_1)":   LongShortRank("noise_1"),
        "MomValue":         CombinedSignal({"mom_1m": 1.0, "val_bm": 1.0}),
    }

    print("\nGrading all strategies against hidden holdout...")
    grader.compare(strategies)

    print("Detailed report for the best planted-signal strategy:")
    grader.evaluate(strategies["Momentum(mom_1m)"]).print()


if __name__ == "__main__":
    main()
