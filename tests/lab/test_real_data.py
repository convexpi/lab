"""Tests for RealDataMarket, FrenchFactorData, FredSeries (offline, no network)."""

import csv
import io
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from convexpi.lab.real_data import (
    FredSeries,
    FrenchFactorData,
    RealDataMarket,
    _cs_zscore,
    _ts_zscore,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic price panel
# ---------------------------------------------------------------------------

def _make_prices(n_days: int = 300, n_stocks: int = 10, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0, 0.01, (n_days, n_stocks))
    rets[0] = 0.0
    start = rng.uniform(20.0, 100.0, n_stocks)
    return start * np.exp(np.cumsum(rets, axis=0))


def _make_dates(n_days: int, start: str = "2020-01-02") -> list[str]:
    from datetime import datetime, timedelta
    d = datetime.strptime(start, "%Y-%m-%d")
    dates = []
    while len(dates) < n_days:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return dates


def _make_market(n_days: int = 300, n_stocks: int = 10, **kwargs) -> RealDataMarket:
    prices = _make_prices(n_days, n_stocks)
    dates  = _make_dates(n_days)
    tickers = [f"STK{i}" for i in range(n_stocks)]
    return RealDataMarket(prices, dates, tickers,
                          load_fred=False, load_french=False, **kwargs)


# ---------------------------------------------------------------------------
# Helper math
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_cs_zscore_mean_zero(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        z = _cs_zscore(x)
        assert abs(z.mean()) < 1e-9

    def test_cs_zscore_nan_passthrough(self):
        x = np.array([np.nan, 1.0, 2.0])
        z = _cs_zscore(x)
        assert np.isnan(z[0])

    def test_ts_zscore_finite(self):
        x = np.array([1.0, 2.0, 3.0, np.nan, 5.0])
        z = _ts_zscore(x)
        assert np.isfinite(z[~np.isnan(x)]).all()
        assert z[3] == 0.0  # NaN mapped to 0

    def test_ts_zscore_constant_returns_zeros(self):
        x = np.full(10, 3.14)
        z = _ts_zscore(x)
        assert np.allclose(z, 0.0)


# ---------------------------------------------------------------------------
# RealDataMarket — shape and interface
# ---------------------------------------------------------------------------

class TestRealDataMarketInterface:
    def test_prices_train_shape(self):
        m = _make_market(n_days=300, n_stocks=10, train_frac=0.7)
        p = m.prices("train")
        assert p.shape == (210, 10)

    def test_prices_test_shape(self):
        m = _make_market(n_days=300, n_stocks=10, train_frac=0.7)
        p = m.prices("test")
        assert p.shape == (90, 10)

    def test_prices_all_shape(self):
        m = _make_market(n_days=300, n_stocks=10)
        assert m.prices("all").shape == (300, 10)

    def test_invalid_split_raises(self):
        m = _make_market()
        with pytest.raises(ValueError, match="split must be"):
            m.prices("future")

    def test_returns_shape(self):
        m = _make_market(n_days=200, n_stocks=5)
        r = m.returns("train")
        assert r.shape[1] == 5
        assert r.shape[0] == m.train_end - 1

    def test_stock_ids(self):
        m = _make_market(n_days=200, n_stocks=4)
        assert len(m.stock_ids) == 4

    def test_features_keys_present(self):
        m = _make_market(n_days=300, n_stocks=5)
        keys = set(m.features("train").keys())
        for k in ("mom_1m", "mom_3m", "mom_12m", "reversal_1w", "vol_1m", "size_cap"):
            assert k in keys, f"Missing feature: {k}"

    def test_features_train_shape(self):
        m = _make_market(n_days=300, n_stocks=8)
        for k, arr in m.features("train").items():
            assert arr.shape == (m.train_end, 8), f"{k}: {arr.shape}"

    def test_no_future_in_features(self):
        """mom_1m at day t should only use prices up to day t."""
        m = _make_market(n_days=100, n_stocks=3)
        # The feature at day 0 should be NaN (21-day lookback not satisfied)
        feat = m.features("all")
        assert np.all(np.isnan(feat["mom_1m"][0]))

    def test_describe_runs(self, capsys):
        m = _make_market(n_days=200, n_stocks=5)
        m.describe()
        out = capsys.readouterr().out
        assert "RealDataMarket" in out

    def test_from_prices_factory(self):
        """from_prices works with a dict-like pandas substitute."""
        prices_np = _make_prices(200, 5)
        dates = _make_dates(200)
        tickers = [f"T{i}" for i in range(5)]

        # Simulate a minimal DataFrame-like object
        import types
        df = types.SimpleNamespace()
        df.index = dates
        df.columns = tickers
        df.values = prices_np

        m = RealDataMarket.from_prices(df, load_fred=False, load_french=False)
        assert m.n_stocks == 5
        assert m.n_days == 200


# ---------------------------------------------------------------------------
# RealDataMarket — compatibility with Backtest
# ---------------------------------------------------------------------------

class TestBacktestCompatibility:
    def test_longshort_runs_on_real_data(self):
        from convexpi.lab import Backtest, LongShortRank
        m = _make_market(n_days=400, n_stocks=20)
        prices = m.prices("train")
        features = m.features("train")
        result = Backtest(warmup_days=21).run(LongShortRank("mom_1m"), prices, features)
        assert result.sharpe is not None
        assert len(result.daily_returns) > 0

    def test_equal_weight_baseline(self):
        from convexpi.lab import Backtest, EqualWeight
        m = _make_market(n_days=300, n_stocks=10)
        result = Backtest(warmup_days=10).run(
            EqualWeight(), m.prices("train"), m.features("train")
        )
        assert result.annualized_vol > 0


# ---------------------------------------------------------------------------
# FredSeries — offline (stubbed HTTP)
# ---------------------------------------------------------------------------

_FRED_CSV = """DATE,VALUE
2020-01-02,1.5
2020-01-03,1.6
2020-01-06,1.4
2020-01-07,.
2020-01-08,1.7
"""


class TestFredSeries:
    def _make_fred_with_data(self, tmp_path: Path) -> FredSeries:
        """Build a FredSeries whose cache files already exist."""
        series_ids = {"yield_curve": "T10Y2Y_TEST"}
        # Write pre-cached file
        cache = tmp_path / "fred_T10Y2Y_TEST.csv"
        cache.write_text(_FRED_CSV)

        with patch("convexpi.lab.real_data._CACHE_DIR", tmp_path):
            fred = FredSeries.__new__(FredSeries)
            fred._series_ids = series_ids
            fred._data = {"yield_curve": FredSeries._load.__func__(FredSeries, "T10Y2Y_TEST")
                          if False else {}}
            # Load directly from our test CSV
            data = {}
            for line in _FRED_CSV.splitlines()[1:]:
                parts = line.strip().split(",")
                if len(parts) < 2:
                    continue
                d, v = parts[0].strip(), parts[1].strip()
                try:
                    data[d] = float(v)
                except ValueError:
                    pass
            fred._data = {"yield_curve": data}
        return fred

    def test_get_known_date(self, tmp_path):
        fred = self._make_fred_with_data(tmp_path)
        vals = fred.get("yield_curve", ["2020-01-02", "2020-01-03"])
        assert vals[0] == 1.5
        assert vals[1] == 1.6

    def test_forward_fill_missing(self, tmp_path):
        fred = self._make_fred_with_data(tmp_path)
        # 2020-01-07 has '.' (missing) in FRED; should forward-fill from 2020-01-06
        vals = fred.get("yield_curve", ["2020-01-06", "2020-01-07"])
        assert vals[0] == 1.4
        assert vals[1] == 1.4  # forward-filled

    def test_available(self, tmp_path):
        fred = self._make_fred_with_data(tmp_path)
        assert "yield_curve" in fred.available()

    def test_unknown_name_returns_nans(self, tmp_path):
        fred = self._make_fred_with_data(tmp_path)
        vals = fred.get("nonexistent", ["2020-01-02"])
        assert np.isnan(vals[0])


# ---------------------------------------------------------------------------
# FrenchFactorData — offline (stubbed CSV inside ZIP)
# ---------------------------------------------------------------------------

_FF3_CSV = """,This file was created by CMPT_ME_BEME_OP_INV_RETS using the 202501 CRSP database.
COPYRIGHT 2025 EUGENE F. FAMA AND KENNETH R. FRENCH

Daily Factors: January 1, 1926 - December 31, 2024

         ,          ,          ,
         , Mkt-RF   ,    SMB   ,    HML   ,     RF
20200102 ,     0.35 ,     0.10 ,    -0.05 ,   0.01
20200103 ,    -0.70 ,    -0.20 ,     0.15 ,   0.01
20200106 ,     1.10 ,     0.30 ,    -0.10 ,   0.01
"""

_MOM_CSV = """,Momentum Factor (Mom): January 1927 - December 2024

Daily Mom Factor

        ,    Mom
20200102,   0.20
20200103,  -0.30
20200106,   0.50
"""


def _make_french_zip(csv_content: str, filename: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, csv_content)
    return buf.getvalue()


class TestFrenchFactorData:
    def _make_french(self, tmp_path: Path) -> FrenchFactorData:
        ff3_data = FrenchFactorData._parse_french_csv(_FF3_CSV)
        mom_data = FrenchFactorData._parse_french_csv(_MOM_CSV)
        french = FrenchFactorData.__new__(FrenchFactorData)
        french._ff3 = ff3_data
        french._mom = mom_data
        french._ff5 = None
        return french

    def test_parse_ff3(self, tmp_path):
        data = FrenchFactorData._parse_french_csv(_FF3_CSV)
        assert "20200102" in data
        assert abs(data["20200102"]["Mkt-RF"] - 0.35) < 1e-6

    def test_get_smb(self, tmp_path):
        french = self._make_french(tmp_path)
        vals = french.get("SMB", ["2020-01-02", "2020-01-03"])
        assert abs(vals[0] - 0.10) < 1e-6
        assert abs(vals[1] - (-0.20)) < 1e-6

    def test_get_mom(self, tmp_path):
        french = self._make_french(tmp_path)
        vals = french.get("Mom", ["2020-01-02"])
        assert abs(vals[0] - 0.20) < 1e-6

    def test_missing_date_returns_zero(self, tmp_path):
        french = self._make_french(tmp_path)
        vals = french.get("SMB", ["1900-01-01"])
        assert vals[0] == 0.0

    def test_available_factors(self, tmp_path):
        french = self._make_french(tmp_path)
        factors = french.available_factors()
        assert "SMB" in factors
        assert "HML" in factors
        assert "Mom" in factors
