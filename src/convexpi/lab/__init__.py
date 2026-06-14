"""
convexpi.lab — Synthetic market backtesting and alpha discovery grader.

Student-facing imports:
    from convexpi.lab import SyntheticMarket, Backtest, Strategy
    from convexpi.lab import LongShortRank, CombinedSignal    # example strategies

Instructor / grader:
    from convexpi.lab import Grader, PlantedAlpha
"""

from .synth import SyntheticMarket, PlantedAlpha
from .backtest import (
    Strategy,
    Backtest,
    BacktestResult,
    EqualWeight,
    MomentumLong,
    LongShortRank,
    CombinedSignal,
)
from .grader import Grader, GradeReport, AlphaDiscovery
from .real_data import RealDataMarket, FrenchFactorData, FredSeries, fetch_prices
from .anomalies import compute_all as compute_anomaly_stats, AnomalySpec, _CATALOGUE as ANOMALY_CATALOGUE
from .strategies import (
    STRATEGIES,
    compare,
    CrossSectionalMomentum,
    ShortTermReversal,
    TimeSeriesMomentum,
    ValueTilt,
    QualityTilt,
    BettingAgainstBeta,
    SizePremium,
    FamaFrench3,
    MultiFactorRank,
    ICWeightedComposite,
    InverseVolatilityWeight,
    MinimumVarianceScreen,
    TrendFilter,
    DualMomentum,
    MacroCyclical,
)

__all__ = [
    "AlphaDiscovery",
    "Backtest",
    "BacktestResult",
    "CombinedSignal",
    "EqualWeight",
    "FrenchFactorData",
    "FredSeries",
    "GradeReport",
    "Grader",
    "LongShortRank",
    "MomentumLong",
    "PlantedAlpha",
    "RealDataMarket",
    "Strategy",
    "SyntheticMarket",
    "fetch_prices",
]
