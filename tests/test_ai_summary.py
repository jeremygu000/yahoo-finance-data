from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pandas as pd
import pytest

from market_data.ai_summary import (
    SYSTEM_PROMPT,
    _format_ohlcv_csv,
    build_prompt,
    generate,
    generate_stream,
    generate_summary,
    health_check,
)


def _make_df(rows: int = 5) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=rows, freq="B")
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(rows)],
            "High": [105.0 + i for i in range(rows)],
            "Low": [95.0 + i for i in range(rows)],
            "Close": [102.0 + i for i in range(rows)],
            "Volume": [1_000_000 + i * 100 for i in range(rows)],
        },
        index=dates,
    )


class TestFormatOhlcvCsv:
    def test_basic_output(self) -> None:
        df = _make_df(3)
        result = _format_ohlcv_csv("AAPL", df, tail=3)
        assert "Ticker: AAPL" in result
        assert "Date,Open,High,Low,Close,Volume" in result
        assert "Period change:" in result
        lines = result.strip().split("\n")
        assert len(lines) == 6  # header + csv_header + 3 data + period change

    def test_tail_limits_rows(self) -> None:
        df = _make_df(20)
        result = _format_ohlcv_csv("SPY", df, tail=5)
        csv_lines = [
            l
            for l in result.strip().split("\n")
            if "," in l and "Ticker" not in l and "Period" not in l and "Date,Open" not in l
        ]
        assert len(csv_lines) == 5

    def test_single_row_no_period_change(self) -> None:
        df = _make_df(1)
        result = _format_ohlcv_csv("QQQ", df)
        assert "Period change:" not in result


class TestBuildPrompt:
    @patch("market_data.ai_summary.duckdb_reader")
    def test_with_data(self, mock_reader: MagicMock) -> None:
        mock_reader.batch_load.return_value = {"AAPL": _make_df(5), "MSFT": _make_df(5)}
        result = build_prompt(["AAPL", "MSFT"], days=30)
        assert "2 tickers" in result
        assert "30-day" in result
        assert "AAPL" in result
        assert "MSFT" in result
        mock_reader.batch_load.assert_called_once_with(["AAPL", "MSFT"], days=30)

    @patch("market_data.ai_summary.duckdb_reader")
    def test_empty_data(self, mock_reader: MagicMock) -> None:
        mock_reader.batch_load.return_value = {}
        result = build_prompt(["AAPL"])
        assert "No data available" in result


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("market_data.ai_summary.httpx.AsyncClient", return_value=mock_client):
            assert await health_check() is True

    @pytest.mark.asyncio
    async def test_unreachable(self) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("market_data.ai_summary.httpx.AsyncClient", return_value=mock_client):
            assert await health_check() is False

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("market_data.ai_summary.httpx.AsyncClient", return_value=mock_client):
            assert await health_check() is False


class TestGenerate:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        ollama_response = {
            "response": "Market is bullish.",
            "model": "qwen2.5:32b",
            "total_duration": 5_000_000_000,
            "eval_count": 150,
            "done": True,
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = ollama_response
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("market_data.ai_summary.httpx.AsyncClient", return_value=mock_client):
            result = await generate("test prompt")

        assert result["response"] == "Market is bullish."
        assert result["model"] == "qwen2.5:32b"
        assert result["total_duration_ms"] == 5000
        assert result["eval_count"] == 150

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["prompt"] == "test prompt"
        assert payload["system"] == SYSTEM_PROMPT
        assert payload["stream"] is False

    @pytest.mark.asyncio
    async def test_connect_error(self) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("market_data.ai_summary.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.ConnectError):
                await generate("test")


class TestGenerateSummary:
    @pytest.mark.asyncio
    async def test_end_to_end(self) -> None:
        with (
            patch("market_data.ai_summary.store") as mock_store,
            patch("market_data.ai_summary.generate", new_callable=AsyncMock) as mock_gen,
        ):
            mock_store.load.return_value = _make_df(5)
            mock_gen.return_value = {
                "response": "Summary text",
                "model": "qwen2.5:32b",
                "total_duration_ms": 3000,
                "eval_count": 100,
            }

            result = await generate_summary(["AAPL"], days=10)
            assert result["response"] == "Summary text"
            mock_gen.assert_called_once()
