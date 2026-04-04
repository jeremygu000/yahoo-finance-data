import pytest
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from market_data import store


class TestSaveAndLoad:
    def test_save_and_load(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        rows_added = store.save("AAPL", df, data_dir=tmp_path)
        assert rows_added == 10

        loaded = store.load("AAPL", data_dir=tmp_path)
        assert not loaded.empty
        assert len(loaded) == 10
        assert list(loaded.columns) == list(df.columns)
        assert len(loaded) == len(df)

    def test_save_deduplication(self, tmp_path, sample_ohlcv):
        df1 = sample_ohlcv(days=10)
        store.save("TSLA", df1, data_dir=tmp_path)

        df2 = df1.iloc[-5:].copy()
        rows_added = store.save("TSLA", df2, data_dir=tmp_path)

        assert rows_added == 0
        loaded = store.load("TSLA", data_dir=tmp_path)
        assert len(loaded) == 10

    def test_load_days_filter(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=30)
        store.save("MSFT", df, data_dir=tmp_path)

        loaded = store.load("MSFT", days=7, data_dir=tmp_path)
        assert len(loaded) > 0
        assert all(loaded.index >= pd.Timestamp(date.today()) - pd.Timedelta(days=7))

    def test_load_missing_ticker(self, tmp_path):
        result = store.load("NONEXISTENT", data_dir=tmp_path)
        assert result.empty

    def test_list_tickers(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path)
        store.save("GOOG", df, data_dir=tmp_path)

        tickers = store.list_tickers(data_dir=tmp_path)
        assert set(tickers) == {"AAPL", "GOOG"}

    def test_clean(self, tmp_path, sample_ohlcv):
        start_date = date.today() - timedelta(days=730)
        df = sample_ohlcv(days=100, start_date=start_date)
        store.save("OLD", df, data_dir=tmp_path)

        removed = store.clean(keep_days=365, data_dir=tmp_path)
        assert "OLD_1d" in removed
        assert removed["OLD_1d"] > 0

        loaded = store.load("OLD", data_dir=tmp_path)
        assert all(loaded.index >= pd.Timestamp(date.today()) - pd.Timedelta(days=365))

    def test_status(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        store.save("TEST", df, data_dir=tmp_path)

        status = store.status(data_dir=tmp_path)
        assert len(status) == 1
        assert status[0]["ticker"] == "TEST"
        assert status[0]["rows"] == 10
        assert "first_date" in status[0]
        assert "last_date" in status[0]
        assert "size_kb" in status[0]

    def test_save_and_load_with_interval(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path, interval="1h")

        parquet_path = tmp_path / "AAPL_1h.parquet"
        assert parquet_path.exists()

        loaded = store.load("AAPL", data_dir=tmp_path, interval="1h")
        assert not loaded.empty
        assert len(loaded) == 5

    def test_lazy_migration(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=5)
        legacy_path = tmp_path / "AAPL.parquet"
        df.to_parquet(legacy_path, engine="pyarrow")

        store.invalidate_cache()
        loaded = store.load("AAPL", data_dir=tmp_path, interval="1d")
        assert not loaded.empty

        new_path = tmp_path / "AAPL_1d.parquet"
        assert new_path.exists()
        assert not legacy_path.exists()

    def test_list_tickers_with_intervals(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path, interval="1d")
        store.save("AAPL", df, data_dir=tmp_path, interval="1h")
        store.save("GOOG", df, data_dir=tmp_path, interval="1d")

        tickers = store.list_tickers(data_dir=tmp_path)
        assert set(tickers) == {"AAPL", "GOOG"}

    def test_status_includes_interval(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path, interval="1h")

        status = store.status(data_dir=tmp_path)
        assert len(status) == 1
        assert status[0]["interval"] == "1h"
        assert status[0]["ticker"] == "AAPL"
