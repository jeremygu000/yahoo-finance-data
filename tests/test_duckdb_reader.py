"""Tests for duckdb_reader module."""

import pytest
import pandas as pd
from datetime import date, timedelta
from pathlib import Path

from market_data import duckdb_reader, store


class TestBatchStatus:
    def test_empty_dir(self, tmp_path: Path) -> None:
        result = duckdb_reader.batch_status(data_dir=tmp_path)
        assert result == []

    def test_single_ticker(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=10)
        store.save("AAPL", df, data_dir=tmp_path)

        result = duckdb_reader.batch_status(data_dir=tmp_path)
        assert len(result) == 1
        item = result[0]
        assert item["ticker"] == "AAPL"
        assert item["interval"] == "1d"
        assert item["rows"] == 10
        assert "first_date" in item
        assert "last_date" in item
        assert "size_kb" in item
        assert float(str(item["size_kb"])) > 0

    def test_multiple_tickers(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path)
        store.save("GOOG", df, data_dir=tmp_path)
        store.save("MSFT", df, data_dir=tmp_path)

        result = duckdb_reader.batch_status(data_dir=tmp_path)
        tickers = {r["ticker"] for r in result}
        assert tickers == {"AAPL", "GOOG", "MSFT"}
        assert all(r["rows"] == 5 for r in result)

    def test_different_intervals(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path, interval="1d")
        store.save("AAPL", df, data_dir=tmp_path, interval="1h")

        result = duckdb_reader.batch_status(data_dir=tmp_path)
        assert len(result) == 2
        intervals = {r["interval"] for r in result}
        assert intervals == {"1d", "1h"}


class TestBatchStatusPaginated:
    def test_empty_dir(self, tmp_path: Path) -> None:
        result = duckdb_reader.batch_status_paginated(data_dir=tmp_path)
        assert result["items"] == []
        assert result["total"] == 0

    def test_pagination(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=5)
        for i in range(5):
            store.save(f"T{i:02d}", df, data_dir=tmp_path)

        result = duckdb_reader.batch_status_paginated(page=1, page_size=2, data_dir=tmp_path)
        assert result["total"] == 5
        assert result["total_pages"] == 3
        assert len(result["items"]) == 2  # type: ignore[arg-type]

        result2 = duckdb_reader.batch_status_paginated(page=3, page_size=2, data_dir=tmp_path)
        assert len(result2["items"]) == 1  # type: ignore[arg-type]

    def test_search_filter(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path)
        store.save("GOOG", df, data_dir=tmp_path)
        store.save("AMZN", df, data_dir=tmp_path)

        result = duckdb_reader.batch_status_paginated(search="A", data_dir=tmp_path)
        tickers = {item["ticker"] for item in result["items"]}  # type: ignore[union-attr]
        assert tickers == {"AAPL", "AMZN"}

    def test_latest_quote_present(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path)

        result = duckdb_reader.batch_status_paginated(data_dir=tmp_path)
        items = result["items"]
        assert len(items) == 1  # type: ignore[arg-type]
        item = items[0]  # type: ignore[index]
        assert item["latest"] is not None
        latest = item["latest"]
        assert "date" in latest  # type: ignore[operator]
        assert "close" in latest  # type: ignore[operator]
        assert "volume" in latest  # type: ignore[operator]


class TestBatchLatest:
    def test_empty(self, tmp_path: Path) -> None:
        result = duckdb_reader.batch_latest([], data_dir=tmp_path)
        assert result == {}

    def test_nonexistent_tickers(self, tmp_path: Path) -> None:
        result = duckdb_reader.batch_latest(["FAKE"], data_dir=tmp_path)
        assert result == {}

    def test_single_ticker(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=10)
        store.save("AAPL", df, data_dir=tmp_path)

        result = duckdb_reader.batch_latest(["AAPL"], data_dir=tmp_path)
        assert "AAPL" in result
        row = result["AAPL"]
        assert "date" in row
        assert "open" in row
        assert "high" in row
        assert "low" in row
        assert "close" in row
        assert "volume" in row
        assert isinstance(row["close"], float)
        assert isinstance(row["volume"], int)

    def test_multiple_tickers(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path)
        store.save("GOOG", df, data_dir=tmp_path)

        result = duckdb_reader.batch_latest(["AAPL", "GOOG", "FAKE"], data_dir=tmp_path)
        assert set(result.keys()) == {"AAPL", "GOOG"}

    def test_returns_latest_row(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=10)
        store.save("AAPL", df, data_dir=tmp_path)

        result = duckdb_reader.batch_latest(["AAPL"], data_dir=tmp_path)
        latest_date = result["AAPL"]["date"]
        expected_date = df.index[-1].date().isoformat()  # type: ignore[union-attr]
        assert latest_date == expected_date


class TestBatchLoad:
    def test_empty(self, tmp_path: Path) -> None:
        result = duckdb_reader.batch_load([], data_dir=tmp_path)
        assert result == {}

    def test_single_ticker(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=10)
        store.save("AAPL", df, data_dir=tmp_path)

        result = duckdb_reader.batch_load(["AAPL"], data_dir=tmp_path)
        assert "AAPL" in result
        loaded = result["AAPL"]
        assert len(loaded) == 10
        assert loaded.index.name == "Date"
        assert "Close" in loaded.columns

    def test_days_filter(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=30)
        store.save("AAPL", df, data_dir=tmp_path)

        result = duckdb_reader.batch_load(["AAPL"], days=7, data_dir=tmp_path)
        loaded = result["AAPL"]
        assert len(loaded) > 0
        assert len(loaded) < 30
        cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=7)
        assert all(loaded.index >= cutoff)

    def test_column_projection(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=10)
        store.save("AAPL", df, data_dir=tmp_path)

        result = duckdb_reader.batch_load(["AAPL"], data_dir=tmp_path, columns=["Date", "Close"])
        loaded = result["AAPL"]
        assert list(loaded.columns) == ["Close"]
        assert len(loaded) == 10

    def test_multiple_tickers(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=5)
        store.save("AAPL", df, data_dir=tmp_path)
        store.save("GOOG", df, data_dir=tmp_path)

        result = duckdb_reader.batch_load(["AAPL", "GOOG"], data_dir=tmp_path)
        assert set(result.keys()) == {"AAPL", "GOOG"}
        assert len(result["AAPL"]) == 5
        assert len(result["GOOG"]) == 5


class TestCompareClose:
    def test_basic(self, tmp_path: Path, sample_ohlcv) -> None:  # type: ignore[no-untyped-def]
        df = sample_ohlcv(days=10)
        store.save("AAPL", df, data_dir=tmp_path)
        store.save("GOOG", df, data_dir=tmp_path)

        result = duckdb_reader.compare_close(["AAPL", "GOOG"], days=30, data_dir=tmp_path)
        assert set(result.keys()) == {"AAPL", "GOOG"}
        for ticker_df in result.values():
            assert list(ticker_df.columns) == ["Close"]
            assert ticker_df.index.name == "Date"


class TestParseTickerFromFilename:
    def test_standard(self) -> None:
        assert duckdb_reader._parse_ticker_from_filename("AAPL_1d.parquet") == ("AAPL", "1d")

    def test_hourly(self) -> None:
        assert duckdb_reader._parse_ticker_from_filename("GOOG_1h.parquet") == ("GOOG", "1h")

    def test_legacy_no_interval(self) -> None:
        assert duckdb_reader._parse_ticker_from_filename("AAPL.parquet") == ("AAPL", "1d")

    def test_full_path(self) -> None:
        assert duckdb_reader._parse_ticker_from_filename("/data/AAPL_1d.parquet") == ("AAPL", "1d")

    def test_ticker_with_dash(self) -> None:
        assert duckdb_reader._parse_ticker_from_filename("BRK-B_1d.parquet") == ("BRK-B", "1d")
