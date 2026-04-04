from __future__ import annotations

import argparse
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from market_data.cli import cmd_backfill, main


def _make_ohlcv(rows: int = 5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(rows)],
            "High": [102.0 + i for i in range(rows)],
            "Low": [99.0 + i for i in range(rows)],
            "Close": [101.0 + i for i in range(rows)],
            "Volume": [1_000_000 + i * 100_000 for i in range(rows)],
        },
        index=pd.date_range("2020-01-01", periods=rows),
    )


class TestBackfillBasic:
    @patch("market_data.cli.save")
    @patch("market_data.cli.fetch_batch")
    def test_backfill_basic(self, mock_fetch: MagicMock, mock_save: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
        df = _make_ohlcv(5)
        mock_fetch.return_value = {"AAPL": df}
        mock_save.return_value = 5

        args = argparse.Namespace(ticker="AAPL", start="2020-01-01", end=None, interval="1d")
        cmd_backfill(args)

        mock_fetch.assert_called_once_with(
            ["AAPL"],
            start=date(2020, 1, 1),
            end=date.today(),
            interval="1d",
        )
        mock_save.assert_called_once_with("AAPL", df, interval="1d")

        out = capsys.readouterr().out
        assert "AAPL: +5 rows" in out
        assert "Done. 5 new rows added." in out


class TestBackfillNoData:
    @patch("market_data.cli.fetch_batch")
    def test_backfill_no_data(self, mock_fetch: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
        mock_fetch.return_value = {}

        args = argparse.Namespace(ticker="AAPL", start="2023-01-01", end=None, interval="1d")

        with pytest.raises(SystemExit) as exc_info:
            cmd_backfill(args)

        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "No data returned" in out


class TestBackfillWithInterval:
    @patch("market_data.cli.save")
    @patch("market_data.cli.fetch_batch")
    def test_backfill_with_interval(
        self, mock_fetch: MagicMock, mock_save: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        df = _make_ohlcv(3)
        mock_fetch.return_value = {"AAPL": df}
        mock_save.return_value = 3

        args = argparse.Namespace(ticker="AAPL", start="2023-01-01", end="2023-12-31", interval="1h")
        cmd_backfill(args)

        mock_fetch.assert_called_once_with(
            ["AAPL"],
            start=date(2023, 1, 1),
            end=date(2023, 12, 31),
            interval="1h",
        )
        mock_save.assert_called_once_with("AAPL", df, interval="1h")

        out = capsys.readouterr().out
        assert "interval=1h" in out


class TestBackfillMissingTicker:
    @patch("market_data.cli.save")
    @patch("market_data.cli.fetch_batch")
    def test_backfill_missing_ticker(
        self, mock_fetch: MagicMock, mock_save: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        df = _make_ohlcv(4)
        mock_fetch.return_value = {"AAPL": df}
        mock_save.return_value = 4

        args = argparse.Namespace(ticker="AAPL,MSFT", start="2023-01-01", end=None, interval="1d")
        cmd_backfill(args)

        out = capsys.readouterr().out
        assert "Missing: MSFT" in out
        assert "AAPL: +4 rows" in out


class TestBackfillMissingRequiredArgs:
    def test_backfill_missing_ticker_arg(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["market-data", "backfill", "--start", "2023-01-01"]):
                main()

        assert exc_info.value.code == 2

    def test_backfill_missing_start_arg(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["market-data", "backfill", "--ticker", "AAPL"]):
                main()

        assert exc_info.value.code == 2


class TestBackfillMultipleTickers:
    @patch("market_data.cli.save")
    @patch("market_data.cli.fetch_batch")
    def test_backfill_multiple_tickers(
        self, mock_fetch: MagicMock, mock_save: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        df_aapl = _make_ohlcv(3)
        df_msft = _make_ohlcv(2)
        mock_fetch.return_value = {"AAPL": df_aapl, "MSFT": df_msft}
        mock_save.side_effect = [3, 2]

        args = argparse.Namespace(ticker="AAPL, MSFT", start="2023-01-01", end="2023-12-31", interval="1d")
        cmd_backfill(args)

        mock_fetch.assert_called_once_with(
            ["AAPL", "MSFT"],
            start=date(2023, 1, 1),
            end=date(2023, 12, 31),
            interval="1d",
        )
        assert mock_save.call_count == 2
        mock_save.assert_any_call("AAPL", df_aapl, interval="1d")
        mock_save.assert_any_call("MSFT", df_msft, interval="1d")

        out = capsys.readouterr().out
        assert "Done. 5 new rows added." in out


class TestBackfillEndDate:
    @patch("market_data.cli.save")
    @patch("market_data.cli.fetch_batch")
    def test_backfill_with_end_date(
        self, mock_fetch: MagicMock, mock_save: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        df = _make_ohlcv(10)
        mock_fetch.return_value = {"AAPL": df}
        mock_save.return_value = 10

        args = argparse.Namespace(ticker="AAPL", start="2020-01-01", end="2023-12-31", interval="1d")
        cmd_backfill(args)

        mock_fetch.assert_called_once_with(
            ["AAPL"],
            start=date(2020, 1, 1),
            end=date(2023, 12, 31),
            interval="1d",
        )
        out = capsys.readouterr().out
        assert "2020-01-01" in out
        assert "2023-12-31" in out
