from __future__ import annotations

from datetime import date
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from market_data.providers.base import OHLCV_COLUMNS
from market_data.providers.yfinance import YFinanceProvider, _normalize
from market_data.rate_limiter import YFinanceEmptyDownloadError
from market_data.providers.tiingo import TiingoProvider, _normalize_tiingo
from market_data.providers.fmp import FMPProvider, _normalize_fmp
from market_data.providers import get_provider, get_fallback_chain


def _make_raw_ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Volume": [1000000, 1100000],
        },
        index=pd.date_range("2024-01-01", periods=2),
    )


class TestNormalize:
    def test_valid_ohlcv(self) -> None:
        df = _normalize(_make_raw_ohlcv())
        assert list(df.columns) == OHLCV_COLUMNS
        assert df.index.name == "Date"
        assert len(df) == 2

    def test_empty(self) -> None:
        assert _normalize(pd.DataFrame()).empty

    def test_none(self) -> None:
        assert _normalize(None).empty  # type: ignore[arg-type]

    def test_all_na(self) -> None:
        df = pd.DataFrame(
            {c: [None, None] for c in OHLCV_COLUMNS},
            index=pd.date_range("2024-01-01", periods=2),
        )
        assert _normalize(df).empty

    def test_multiindex_columns(self) -> None:
        arrays = [OHLCV_COLUMNS, ["AAPL"] * 5]
        columns = pd.MultiIndex.from_arrays(arrays)
        df = pd.DataFrame(
            [[100.0, 102.0, 99.0, 101.0, 1000000], [101.0, 103.0, 100.0, 102.0, 1100000]],
            columns=columns,
            index=pd.date_range("2024-01-01", periods=2),
        )
        result = _normalize(df)
        assert list(result.columns) == OHLCV_COLUMNS

    def test_string_index_converted(self) -> None:
        df = pd.DataFrame(
            {"Open": [100.0], "High": [102.0], "Low": [99.0], "Close": [101.0], "Volume": [1000000]},
            index=["2024-01-01"],
        )
        result = _normalize(df)
        assert isinstance(result.index, pd.DatetimeIndex)


class TestNormalizeTiingo:
    def test_adjusted_columns(self) -> None:
        df = pd.DataFrame(
            {
                "date": ["2024-01-01T00:00:00+00:00", "2024-01-02T00:00:00+00:00"],
                "adjOpen": [100.0, 101.0],
                "adjHigh": [102.0, 103.0],
                "adjLow": [99.0, 100.0],
                "adjClose": [101.0, 102.0],
                "adjVolume": [1000000, 1100000],
                "close": [101.5, 102.5],
                "open": [100.5, 101.5],
            }
        )
        result = _normalize_tiingo(df)
        assert list(result.columns) == OHLCV_COLUMNS
        assert result.index.name == "Date"
        assert len(result) == 2

    def test_fallback_to_raw_columns(self) -> None:
        df = pd.DataFrame(
            {
                "date": ["2024-01-01T00:00:00+00:00"],
                "open": [100.0],
                "high": [102.0],
                "low": [99.0],
                "close": [101.0],
                "volume": [1000000],
            }
        )
        result = _normalize_tiingo(df)
        assert list(result.columns) == OHLCV_COLUMNS

    def test_empty(self) -> None:
        assert _normalize_tiingo(pd.DataFrame()).empty


class TestNormalizeFMP:
    def test_valid(self) -> None:
        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02"],
                "open": [100.0, 101.0],
                "high": [102.0, 103.0],
                "low": [99.0, 100.0],
                "close": [101.0, 102.0],
                "volume": [1000000, 1100000],
                "vwap": [101.5, 102.5],
            }
        )
        result = _normalize_fmp(df)
        assert list(result.columns) == OHLCV_COLUMNS
        assert result.index.name == "Date"
        assert len(result) == 2

    def test_empty(self) -> None:
        assert _normalize_fmp(pd.DataFrame()).empty

    def test_missing_date_column(self) -> None:
        df = pd.DataFrame({"open": [100.0], "close": [101.0]})
        assert _normalize_fmp(df).empty


@patch("market_data.providers.yfinance.acquire")
class TestYFinanceProvider:
    def test_name(self, mock_acquire: MagicMock) -> None:
        assert YFinanceProvider().name == "yfinance"

    def test_always_available(self, mock_acquire: MagicMock) -> None:
        assert YFinanceProvider().is_available()

    def test_supported_intervals(self, mock_acquire: MagicMock) -> None:
        intervals = YFinanceProvider().supported_intervals
        assert "1d" in intervals
        assert "1h" in intervals
        assert "15m" in intervals
        assert "5m" in intervals

    @patch("market_data.providers.yfinance.yf.download")
    def test_fetch_ohlcv(self, mock_dl: MagicMock, mock_acquire: MagicMock) -> None:
        mock_dl.return_value = _make_raw_ohlcv()
        provider = YFinanceProvider()
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert not result.empty
        assert list(result.columns) == OHLCV_COLUMNS

    @patch("market_data.providers.yfinance.yf.download")
    def test_fetch_ohlcv_with_interval(self, mock_dl: MagicMock, mock_acquire: MagicMock) -> None:
        mock_dl.return_value = _make_raw_ohlcv()
        provider = YFinanceProvider()
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31), interval="1h")
        assert not result.empty
        call_kwargs = mock_dl.call_args[1]
        assert call_kwargs["interval"] == "1h"

    @patch("tenacity.nap.time.sleep")
    @patch("market_data.providers.yfinance.yf.download")
    def test_fetch_ohlcv_all_retries_fail(
        self, mock_dl: MagicMock, mock_sleep: MagicMock, mock_acquire: MagicMock
    ) -> None:
        mock_dl.side_effect = Exception("Network error")
        provider = YFinanceProvider()
        with pytest.raises(Exception, match="Network error"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))

    @patch("tenacity.nap.time.sleep")
    @patch("market_data.providers.yfinance.yf.download")
    def test_fetch_ohlcv_empty_download_raises(
        self, mock_dl: MagicMock, mock_sleep: MagicMock, mock_acquire: MagicMock
    ) -> None:
        mock_dl.return_value = pd.DataFrame()
        provider = YFinanceProvider()
        with pytest.raises(YFinanceEmptyDownloadError):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))

    @patch("tenacity.nap.time.sleep")
    @patch("market_data.providers.yfinance.yf.download")
    def test_fetch_batch_empty_download_raises(
        self, mock_dl: MagicMock, mock_sleep: MagicMock, mock_acquire: MagicMock
    ) -> None:
        mock_dl.return_value = pd.DataFrame()
        provider = YFinanceProvider()
        with pytest.raises(YFinanceEmptyDownloadError):
            provider.fetch_batch(["AAPL", "MSFT"], date(2024, 1, 1), date(2024, 12, 31))


class TestTiingoProvider:
    def test_name(self) -> None:
        assert TiingoProvider().name == "tiingo"

    def test_not_available_without_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert not TiingoProvider(api_key="").is_available()

    def test_available_with_key(self) -> None:
        assert TiingoProvider(api_key="test_key").is_available()

    def test_supported_intervals(self) -> None:
        intervals = TiingoProvider().supported_intervals
        assert intervals == ["1d"]

    @patch("market_data.providers.tiingo.requests.get")
    def test_fetch_ohlcv(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                "date": "2024-01-01T00:00:00+00:00",
                "adjOpen": 100.0,
                "adjHigh": 102.0,
                "adjLow": 99.0,
                "adjClose": 101.0,
                "adjVolume": 1000000,
            }
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = TiingoProvider(api_key="test_key")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert not result.empty
        assert list(result.columns) == OHLCV_COLUMNS

    def test_fetch_ohlcv_no_key(self) -> None:
        provider = TiingoProvider(api_key="")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert result.empty

    def test_fetch_ohlcv_non_daily_returns_empty(self) -> None:
        provider = TiingoProvider(api_key="test_key")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31), interval="1h")
        assert result.empty


class TestFMPProvider:
    def test_name(self) -> None:
        assert FMPProvider().name == "fmp"

    def test_not_available_without_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert not FMPProvider(api_key="").is_available()

    def test_available_with_key(self) -> None:
        assert FMPProvider(api_key="test_key").is_available()

    def test_supported_intervals(self) -> None:
        intervals = FMPProvider().supported_intervals
        assert intervals == ["1d"]

    @patch("market_data.providers.fmp.requests.get")
    def test_fetch_ohlcv(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                "date": "2024-01-02",
                "open": 101.0,
                "high": 103.0,
                "low": 100.0,
                "close": 102.0,
                "volume": 1100000,
            },
            {
                "date": "2024-01-01",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "volume": 1000000,
            },
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = FMPProvider(api_key="test_key")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert not result.empty
        assert list(result.columns) == OHLCV_COLUMNS
        assert result.index[0] < result.index[1]

    def test_fetch_ohlcv_no_key(self) -> None:
        provider = FMPProvider(api_key="")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert result.empty

    def test_fetch_ohlcv_non_daily_returns_empty(self) -> None:
        provider = FMPProvider(api_key="test_key")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31), interval="1h")
        assert result.empty


class TestRegistry:
    def test_get_provider_default(self) -> None:
        provider = get_provider()
        assert provider.name == "yfinance"

    def test_get_provider_by_name(self) -> None:
        assert get_provider("tiingo").name == "tiingo"
        assert get_provider("fmp").name == "fmp"

    def test_get_provider_unknown(self) -> None:
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nonexistent")

    @patch.dict("os.environ", {"MARKET_DATA_PROVIDER": "fmp"})
    def test_get_provider_from_env(self) -> None:
        provider = get_provider()
        assert provider.name == "fmp"

    def test_fallback_chain_default(self) -> None:
        chain = get_fallback_chain()
        assert len(chain) >= 1
        assert chain[0].name == "yfinance"

    @patch.dict("os.environ", {"MARKET_DATA_FALLBACK_CHAIN": "fmp,yfinance", "FMP_API_KEY": "test"})
    def test_fallback_chain_custom(self) -> None:
        chain = get_fallback_chain()
        names = [p.name for p in chain]
        assert names[0] == "fmp"
