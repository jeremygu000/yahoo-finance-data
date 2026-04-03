import pytest
import pandas as pd
from datetime import date, timedelta
from market_data import store


class TestGetOhlcv:
    def test_get_ohlcv(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=30)
        store.save("AAPL", df, data_dir=tmp_path)

        result = store.load("AAPL", days=30, data_dir=tmp_path)

        assert not result.empty
        assert len(result) == 30
        assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]

    def test_get_ohlcv_with_days_filter(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=60)
        store.save("MSFT", df, data_dir=tmp_path)

        result = store.load("MSFT", days=7, data_dir=tmp_path)

        assert not result.empty
        assert all(result.index >= pd.Timestamp(date.today()) - pd.Timedelta(days=7))


class TestGetLatest:
    def test_get_latest(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        store.save("GOOG", df, data_dir=tmp_path)

        loaded = store.load("GOOG", days=7, data_dir=tmp_path)
        assert not loaded.empty

        last = loaded.iloc[-1]
        result = {
            "date": loaded.index[-1].date().isoformat(),
            "open": float(last.get("Open", 0)),
            "high": float(last.get("High", 0)),
            "low": float(last.get("Low", 0)),
            "close": float(last.get("Close", 0)),
            "volume": int(last.get("Volume", 0)),
        }

        assert result is not None
        assert "date" in result
        assert "open" in result
        assert "high" in result
        assert "low" in result
        assert "close" in result
        assert "volume" in result
        assert isinstance(result["date"], str)
        assert isinstance(result["open"], float)
        assert isinstance(result["volume"], int)

    def test_get_latest_missing(self, tmp_path):
        result = store.load("NONEXISTENT", days=7, data_dir=tmp_path)
        assert result.empty


class TestListTickersApi:
    def test_list_tickers_api(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path)
        store.save("TSLA", df, data_dir=tmp_path)
        store.save("GOOG", df, data_dir=tmp_path)

        result = store.list_tickers(data_dir=tmp_path)

        assert set(result) == {"AAPL", "TSLA", "GOOG"}
        assert result == sorted(result)
