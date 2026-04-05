from __future__ import annotations

from datetime import date
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from market_data.providers.base import OHLCV_COLUMNS
from market_data.providers.twelvedata import TwelvedataProvider, _normalize_twelvedata

_SAMPLE_VALUES = [
    {
        "datetime": "2024-01-01",
        "open": "100.00",
        "high": "102.00",
        "low": "99.00",
        "close": "101.00",
        "volume": "1000000",
    },
    {
        "datetime": "2024-01-02",
        "open": "101.00",
        "high": "103.00",
        "low": "100.00",
        "close": "102.00",
        "volume": "1100000",
    },
]


class TestNormalizeTwelvedata:
    def test_valid(self) -> None:
        df = pd.DataFrame(_SAMPLE_VALUES)
        result = _normalize_twelvedata(df)
        assert list(result.columns) == OHLCV_COLUMNS
        assert result.index.name == "Date"
        assert len(result) == 2
        assert result["Open"].iloc[0] == pytest.approx(100.0)

    def test_empty(self) -> None:
        assert _normalize_twelvedata(pd.DataFrame()).empty

    def test_missing_datetime(self) -> None:
        df = pd.DataFrame({"open": ["100"], "close": ["101"]})
        assert _normalize_twelvedata(df).empty

    def test_string_to_numeric_conversion(self) -> None:
        df = pd.DataFrame(_SAMPLE_VALUES)
        result = _normalize_twelvedata(df)
        assert result["Volume"].iloc[0] == pytest.approx(1000000)

    def test_sorted_ascending(self) -> None:
        values = list(reversed(_SAMPLE_VALUES))
        df = pd.DataFrame(values)
        result = _normalize_twelvedata(df)
        assert result.index[0] < result.index[1]


@patch("market_data.providers.twelvedata.ensure_quota")
class TestTwelvedataProvider:
    def test_name(self, mock_eq: MagicMock) -> None:
        assert TwelvedataProvider(api_key="k").name == "twelvedata"

    def test_not_available_without_key(self, mock_eq: MagicMock) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert not TwelvedataProvider(api_key="").is_available()

    def test_available_with_key(self, mock_eq: MagicMock) -> None:
        assert TwelvedataProvider(api_key="test_key").is_available()

    def test_supported_intervals(self, mock_eq: MagicMock) -> None:
        assert TwelvedataProvider(api_key="k").supported_intervals == ["1day"]

    @patch("market_data.providers.twelvedata.log_call")
    @patch("market_data.providers.twelvedata.record_success")
    @patch("market_data.providers.twelvedata.get_throttle", return_value={"current_delay": 0.0})
    @patch("market_data.providers.twelvedata.try_consume", return_value=True)
    @patch("market_data.providers.twelvedata.requests.get")
    def test_fetch_ohlcv_success(
        self,
        mock_get: MagicMock,
        mock_consume: MagicMock,
        mock_throttle: MagicMock,
        mock_success: MagicMock,
        mock_log: MagicMock,
        mock_eq: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "meta": {"symbol": "AAPL"},
            "values": _SAMPLE_VALUES,
            "status": "ok",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = TwelvedataProvider(api_key="test_key")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert not result.empty
        assert list(result.columns) == OHLCV_COLUMNS
        mock_success.assert_called_once()

    def test_fetch_ohlcv_no_key(self, mock_eq: MagicMock) -> None:
        provider = TwelvedataProvider(api_key="")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert result.empty

    @patch("market_data.providers.twelvedata.get_throttle", return_value={"current_delay": 0.0})
    @patch("market_data.providers.twelvedata.try_consume", return_value=True)
    @patch("market_data.providers.twelvedata.requests.get")
    def test_fetch_ohlcv_non_daily_returns_empty(
        self,
        mock_get: MagicMock,
        mock_consume: MagicMock,
        mock_throttle: MagicMock,
        mock_eq: MagicMock,
    ) -> None:
        provider = TwelvedataProvider(api_key="test_key")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31), interval="1h")
        assert result.empty

    @patch("market_data.providers.twelvedata.log_call")
    @patch("market_data.providers.twelvedata.record_rate_limit")
    @patch("market_data.providers.twelvedata.get_throttle", return_value={"current_delay": 0.0})
    @patch("market_data.providers.twelvedata.try_consume", return_value=True)
    @patch("market_data.providers.twelvedata.requests.get")
    def test_fetch_ohlcv_429(
        self,
        mock_get: MagicMock,
        mock_consume: MagicMock,
        mock_throttle: MagicMock,
        mock_rl: MagicMock,
        mock_log: MagicMock,
        mock_eq: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        provider = TwelvedataProvider(api_key="test_key")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert result.empty
        mock_rl.assert_called_once()

    @patch("market_data.providers.twelvedata.log_call")
    @patch("market_data.providers.twelvedata.get_throttle", return_value={"current_delay": 0.0})
    @patch("market_data.providers.twelvedata.try_consume", return_value=True)
    @patch("market_data.providers.twelvedata.requests.get")
    def test_fetch_ohlcv_api_error(
        self,
        mock_get: MagicMock,
        mock_consume: MagicMock,
        mock_throttle: MagicMock,
        mock_log: MagicMock,
        mock_eq: MagicMock,
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 400, "message": "Invalid symbol", "status": "error"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = TwelvedataProvider(api_key="test_key")
        result = provider.fetch_ohlcv("INVALID", date(2024, 1, 1), date(2024, 12, 31))
        assert result.empty

    @patch("market_data.providers.twelvedata.log_call")
    @patch("market_data.providers.twelvedata.get_throttle", return_value={"current_delay": 0.0})
    @patch("market_data.providers.twelvedata.try_consume", return_value=False)
    @patch("market_data.providers.twelvedata.time.sleep")
    def test_fetch_ohlcv_quota_exhausted(
        self,
        mock_sleep: MagicMock,
        mock_consume: MagicMock,
        mock_throttle: MagicMock,
        mock_log: MagicMock,
        mock_eq: MagicMock,
    ) -> None:
        provider = TwelvedataProvider(api_key="test_key")
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert result.empty
