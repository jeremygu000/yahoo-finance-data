from __future__ import annotations

import math
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from market_data import indicators as ind
from market_data.server import app

client = TestClient(app, raise_server_exceptions=False)


def _make_df(n: int = 50, start_price: float = 100.0, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2024-01-01", periods=n, freq="B")
    close = start_price + rng.standard_normal(n).cumsum()
    open_ = close + rng.uniform(-1, 1, n)
    high = np.maximum(close, open_) + rng.uniform(0, 1, n)
    low = np.minimum(close, open_) - rng.uniform(0, 1, n)
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=index)


class TestSMA:
    def test_column_name(self) -> None:
        df = _make_df(30)
        result = ind.sma(df, period=10)
        assert "SMA_10" in result.columns

    def test_first_valid_row(self) -> None:
        df = _make_df(30)
        result = ind.sma(df, period=10)
        assert result["SMA_10"].iloc[:9].isna().all()
        assert not math.isnan(result["SMA_10"].iloc[9])

    def test_value_accuracy(self) -> None:
        df = _make_df(20)
        result = ind.sma(df, period=5)
        expected = df["Close"].iloc[4:9].mean()
        assert abs(result["SMA_5"].iloc[8] - expected) < 1e-9

    def test_empty_df_returns_empty(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.sma(df, period=20)
        assert result.empty
        assert "SMA_20" in result.columns

    def test_insufficient_data_all_nan(self) -> None:
        df = _make_df(5)
        result = ind.sma(df, period=20)
        assert result["SMA_20"].isna().all()


class TestEMA:
    def test_column_name(self) -> None:
        df = _make_df(30)
        result = ind.ema(df, period=10)
        assert "EMA_10" in result.columns

    def test_first_valid_row(self) -> None:
        df = _make_df(30)
        result = ind.ema(df, period=10)
        assert result["EMA_10"].iloc[:9].isna().all()
        assert not math.isnan(result["EMA_10"].iloc[9])

    def test_empty_df(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.ema(df, period=10)
        assert result.empty
        assert "EMA_10" in result.columns

    def test_ema_differs_from_sma(self) -> None:
        df = _make_df(50)
        sma_result = ind.sma(df, period=20)
        ema_result = ind.ema(df, period=20)
        assert not (sma_result["SMA_20"].dropna() == ema_result["EMA_20"].dropna()).all()


class TestRSI:
    def test_column_name(self) -> None:
        df = _make_df(30)
        result = ind.rsi(df, period=14)
        assert "RSI_14" in result.columns

    def test_range_0_100(self) -> None:
        df = _make_df(100)
        result = ind.rsi(df, period=14)
        valid = result["RSI_14"].dropna()
        assert (valid >= 0.0).all()
        assert (valid <= 100.0).all()

    def test_empty_df(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.rsi(df, period=14)
        assert result.empty

    def test_pure_uptrend_rsi_100(self) -> None:
        index = pd.date_range("2024-01-01", periods=30, freq="B")
        close = pd.Series(range(1, 31), dtype=float)
        df = pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": 1.0}, index=index)
        result = ind.rsi(df, period=14)
        valid = result["RSI_14"].dropna()
        assert (valid == 100.0).all()

    def test_insufficient_data_all_nan(self) -> None:
        df = _make_df(5)
        result = ind.rsi(df, period=14)
        assert result["RSI_14"].isna().all()


class TestMACD:
    def test_columns(self) -> None:
        df = _make_df(100)
        result = ind.macd(df)
        assert set(result.columns) == {"MACD", "Signal", "Histogram"}

    def test_histogram_equals_macd_minus_signal(self) -> None:
        df = _make_df(100)
        result = ind.macd(df)
        valid = result.dropna()
        diff = (valid["MACD"] - valid["Signal"] - valid["Histogram"]).abs()
        assert (diff < 1e-9).all()

    def test_empty_df(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.macd(df)
        assert result.empty
        assert set(result.columns) == {"MACD", "Signal", "Histogram"}

    def test_insufficient_data_all_nan(self) -> None:
        df = _make_df(10)
        result = ind.macd(df, fast=12, slow=26, signal=9)
        assert result["MACD"].isna().all()
        assert result["Signal"].isna().all()


class TestBollingerBands:
    def test_columns(self) -> None:
        df = _make_df(50)
        result = ind.bollinger_bands(df)
        assert set(result.columns) == {"BB_Upper", "BB_Middle", "BB_Lower"}

    def test_upper_above_lower(self) -> None:
        df = _make_df(50)
        result = ind.bollinger_bands(df).dropna()
        assert (result["BB_Upper"] > result["BB_Lower"]).all()

    def test_middle_is_sma(self) -> None:
        df = _make_df(50)
        bb = ind.bollinger_bands(df, period=20)
        sma_result = ind.sma(df, period=20)
        valid = bb["BB_Middle"].dropna()
        sma_valid = sma_result["SMA_20"].dropna()
        pd.testing.assert_series_equal(valid, sma_valid, check_names=False, atol=1e-9)

    def test_empty_df(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.bollinger_bands(df)
        assert result.empty
        assert set(result.columns) == {"BB_Upper", "BB_Middle", "BB_Lower"}

    def test_custom_std_dev_wider(self) -> None:
        df = _make_df(50)
        bb1 = ind.bollinger_bands(df, period=20, std_dev=1.0).dropna()
        bb2 = ind.bollinger_bands(df, period=20, std_dev=3.0).dropna()
        width1 = (bb1["BB_Upper"] - bb1["BB_Lower"]).mean()
        width2 = (bb2["BB_Upper"] - bb2["BB_Lower"]).mean()
        assert width2 > width1


class TestIndicatorsAPI:
    def _mock_df(self) -> pd.DataFrame:
        return _make_df(50)

    def test_sma_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=sma&period=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        assert "date" in first
        assert "time" in first
        assert "values" in first

    def test_ema_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=ema&period=10")
        assert resp.status_code == 200
        data = resp.json()
        assert any("EMA_10" in row["values"] for row in data)

    def test_rsi_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=rsi&period=14")
        assert resp.status_code == 200

    def test_macd_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=macd")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        last_valid = [r for r in data if r["values"].get("MACD") is not None]
        assert len(last_valid) > 0
        assert "Signal" in last_valid[0]["values"]
        assert "Histogram" in last_valid[0]["values"]

    def test_bollinger_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=bollinger&period=20")
        assert resp.status_code == 200
        data = resp.json()
        valid = [r for r in data if r["values"].get("BB_Upper") is not None]
        assert len(valid) > 0

    def test_invalid_indicator_returns_400(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=unknown")
        assert resp.status_code == 400

    def test_invalid_interval_returns_400(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=sma&interval=bad")
        assert resp.status_code == 400

    def test_legacy_route(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/indicators/AAPL?indicator=sma&period=10")
        assert resp.status_code == 200

    def test_empty_data_returns_empty_list(self) -> None:
        empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        with patch("market_data.server.store.load", return_value=empty):
            resp = client.get("/api/v1/indicators/AAPL?indicator=sma&period=10")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_nan_values_serialized_as_null(self) -> None:
        df = _make_df(5)
        with patch("market_data.server.store.load", return_value=df):
            resp = client.get("/api/v1/indicators/AAPL?indicator=sma&period=20")
        assert resp.status_code == 200
        data = resp.json()
        assert all(row["values"]["SMA_20"] is None for row in data)


class TestVWAP:
    def test_column_name(self) -> None:
        df = _make_df(30)
        result = ind.vwap(df)
        assert "VWAP" in result.columns

    def test_first_row_valid(self) -> None:
        df = _make_df(30)
        result = ind.vwap(df)
        assert not math.isnan(result["VWAP"].iloc[0])

    def test_value_in_price_range(self) -> None:
        df = _make_df(50)
        result = ind.vwap(df)
        valid = result["VWAP"].dropna()
        assert (valid >= df["Low"].min()).all()
        assert (valid <= df["High"].max()).all()

    def test_empty_df(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.vwap(df)
        assert result.empty
        assert "VWAP" in result.columns


class TestATR:
    def test_column_name(self) -> None:
        df = _make_df(30)
        result = ind.atr(df, period=14)
        assert "ATR_14" in result.columns

    def test_first_valid_row(self) -> None:
        df = _make_df(30)
        result = ind.atr(df, period=14)
        assert result["ATR_14"].iloc[:13].isna().all()
        assert not math.isnan(result["ATR_14"].iloc[13])

    def test_values_positive(self) -> None:
        df = _make_df(50)
        result = ind.atr(df, period=14)
        valid = result["ATR_14"].dropna()
        assert (valid > 0).all()

    def test_empty_df(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.atr(df, period=14)
        assert result.empty
        assert "ATR_14" in result.columns


class TestStochastic:
    def test_columns(self) -> None:
        df = _make_df(50)
        result = ind.stochastic(df, period=14)
        assert set(result.columns) == {"Stoch_K", "Stoch_D"}

    def test_range_0_100(self) -> None:
        df = _make_df(100)
        result = ind.stochastic(df, period=14)
        valid_k = result["Stoch_K"].dropna()
        valid_d = result["Stoch_D"].dropna()
        assert (valid_k >= 0.0).all() and (valid_k <= 100.0).all()
        assert (valid_d >= 0.0).all() and (valid_d <= 100.0).all()

    def test_d_is_smoothed_k(self) -> None:
        df = _make_df(50)
        result = ind.stochastic(df, period=14, smooth_k=3)
        k = result["Stoch_K"].dropna()
        expected_d = k.rolling(window=3, min_periods=3).mean()
        actual_d = result["Stoch_D"].loc[expected_d.dropna().index]
        pd.testing.assert_series_equal(actual_d, expected_d.dropna(), check_names=False, atol=1e-9)

    def test_empty_df(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.stochastic(df, period=14)
        assert result.empty
        assert set(result.columns) == {"Stoch_K", "Stoch_D"}


class TestOBV:
    def test_column_name(self) -> None:
        df = _make_df(30)
        result = ind.obv(df)
        assert "OBV" in result.columns

    def test_first_row_valid(self) -> None:
        df = _make_df(30)
        result = ind.obv(df)
        assert not math.isnan(result["OBV"].iloc[0])

    def test_monotonic_up_increases(self) -> None:
        index = pd.date_range("2024-01-01", periods=10, freq="B")
        close = pd.Series(range(1, 11), dtype=float, index=index)
        vol = pd.Series([1000.0] * 10, index=index)
        df = pd.DataFrame(
            {"Open": close, "High": close, "Low": close, "Close": close, "Volume": vol},
            index=index,
        )
        result = ind.obv(df)
        valid = result["OBV"].iloc[1:]
        assert (valid.diff().dropna() > 0).all()

    def test_empty_df(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.obv(df)
        assert result.empty
        assert "OBV" in result.columns


class TestADX:
    def test_columns(self) -> None:
        df = _make_df(50)
        result = ind.adx(df, period=14)
        assert set(result.columns) == {"ADX_14", "Plus_DI", "Minus_DI"}

    def test_adx_range_0_100(self) -> None:
        df = _make_df(100)
        result = ind.adx(df, period=14)
        valid = result["ADX_14"].dropna()
        assert (valid >= 0.0).all()
        assert (valid <= 100.0).all()

    def test_di_positive(self) -> None:
        df = _make_df(100)
        result = ind.adx(df, period=14)
        valid_plus = result["Plus_DI"].dropna()
        valid_minus = result["Minus_DI"].dropna()
        assert (valid_plus >= 0.0).all()
        assert (valid_minus >= 0.0).all()

    def test_empty_df(self) -> None:
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = ind.adx(df, period=14)
        assert result.empty
        assert set(result.columns) == {"ADX_14", "Plus_DI", "Minus_DI"}


class TestNewIndicatorsAPI:
    def _mock_df(self) -> pd.DataFrame:
        return _make_df(50)

    def test_vwap_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=vwap")
        assert resp.status_code == 200
        data = resp.json()
        assert any(row["values"].get("VWAP") is not None for row in data)

    def test_atr_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=atr&period=14")
        assert resp.status_code == 200
        data = resp.json()
        assert any(row["values"].get("ATR_14") is not None for row in data)

    def test_stochastic_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=stochastic&period=14")
        assert resp.status_code == 200
        data = resp.json()
        valid = [r for r in data if r["values"].get("Stoch_K") is not None]
        assert len(valid) > 0
        assert "Stoch_D" in valid[0]["values"]

    def test_obv_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=obv")
        assert resp.status_code == 200
        data = resp.json()
        assert any(row["values"].get("OBV") is not None for row in data)

    def test_adx_endpoint(self) -> None:
        with patch("market_data.server.store.load", return_value=self._mock_df()):
            resp = client.get("/api/v1/indicators/AAPL?indicator=adx&period=14")
        assert resp.status_code == 200
        data = resp.json()
        valid = [r for r in data if r["values"].get("ADX_14") is not None]
        assert len(valid) > 0
        assert "Plus_DI" in valid[0]["values"]
        assert "Minus_DI" in valid[0]["values"]
