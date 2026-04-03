import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from market_data.fetcher import fetch_batch, _clean_df


class TestFetchBatch:
    def test_fetch_batch_empty_tickers(self):
        result = fetch_batch([])
        assert result == {}

    def test_fetch_batch_success(self):
        ticker1_data = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [1000000, 1100000],
            },
            index=pd.date_range("2024-01-01", periods=2),
        )

        ticker2_data = pd.DataFrame(
            {
                "Open": [200.0, 201.0],
                "High": [202.0, 203.0],
                "Low": [199.0, 200.0],
                "Close": [201.0, 202.0],
                "Volume": [2000000, 2100000],
            },
            index=pd.date_range("2024-01-01", periods=2),
        )

        mock_data = pd.concat({"AAPL": ticker1_data, "GOOG": ticker2_data}, axis=1, keys=["AAPL", "GOOG"])

        with patch("market_data.fetcher.yf.download", return_value=mock_data):
            result = fetch_batch(["AAPL", "GOOG"])

        assert "AAPL" in result
        assert "GOOG" in result
        assert len(result["AAPL"]) == 2
        assert len(result["GOOG"]) == 2
        assert list(result["AAPL"].columns) == ["Open", "High", "Low", "Close", "Volume"]

    def test_fetch_batch_retry_on_exception(self):
        ticker_data = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [102.0],
                "Low": [99.0],
                "Close": [101.0],
                "Volume": [1000000],
            },
            index=pd.date_range("2024-01-01", periods=1),
        )

        mock_data = pd.concat({"AAPL": ticker_data}, axis=1, keys=["AAPL"])

        mock_download = Mock(side_effect=[Exception("Network error"), Exception("Timeout"), mock_data])

        with patch("market_data.fetcher.yf.download", mock_download):
            with patch("market_data.fetcher.time.sleep"):
                result = fetch_batch(["AAPL"])

        assert "AAPL" in result
        assert mock_download.call_count == 3

    def test_fetch_batch_all_retries_exhausted(self):
        mock_download = Mock(side_effect=Exception("Persistent error"))

        with patch("market_data.fetcher.yf.download", mock_download):
            with patch("market_data.fetcher.time.sleep"):
                result = fetch_batch(["AAPL"])

        assert result == {}

    def test_clean_df_empty(self):
        empty_df = pd.DataFrame()
        result = _clean_df(empty_df)
        assert result is None

    def test_clean_df_with_data(self):
        df = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [1000000, 1100000],
            },
            index=pd.date_range("2024-01-01", periods=2),
        )

        result = _clean_df(df)
        assert result is not None
        assert len(result) == 2
        assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert result.index.name == "Date"

    def test_clean_df_with_multiindex(self):
        arrays = [
            ["Open", "High", "Low", "Close", "Volume"],
            ["AAPL"] * 5,
        ]
        columns = pd.MultiIndex.from_arrays(arrays)
        df = pd.DataFrame(
            [[100.0, 102.0, 99.0, 101.0, 1000000], [101.0, 103.0, 100.0, 102.0, 1100000]],
            columns=columns,
            index=pd.date_range("2024-01-01", periods=2),
        )

        result = _clean_df(df)
        assert result is not None
        assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]

    def test_clean_df_none_input(self):
        result = _clean_df(None)
        assert result is None

    def test_clean_df_all_na(self):
        df = pd.DataFrame(
            {
                "Open": [None, None],
                "High": [None, None],
                "Low": [None, None],
                "Close": [None, None],
                "Volume": [None, None],
            },
            index=pd.date_range("2024-01-01", periods=2),
        )

        result = _clean_df(df)
        assert result is None

    def test_clean_df_non_numeric_index(self):
        df = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [102.0],
                "Low": [99.0],
                "Close": [101.0],
                "Volume": [1000000],
            },
            index=["2024-01-01"],
        )

        result = _clean_df(df)
        assert result is not None
        assert isinstance(result.index, pd.DatetimeIndex)
