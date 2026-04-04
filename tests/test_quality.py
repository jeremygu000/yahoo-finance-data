from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from market_data import quality, store


class TestScanAnomalies:
    def test_detects_high_lt_low(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        df.iloc[3, df.columns.get_loc("High")] = 50.0
        df.iloc[3, df.columns.get_loc("Low")] = 100.0
        store.save("TEST", df, data_dir=tmp_path)

        anomalies = quality.scan_anomalies(data_dir=tmp_path)
        high_lt_low = [a for a in anomalies if a.issue == "high_lt_low"]
        assert len(high_lt_low) == 1
        assert high_lt_low[0].count >= 1

    def test_detects_non_positive_price(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        df.iloc[0, df.columns.get_loc("Close")] = -5.0
        store.save("TEST", df, data_dir=tmp_path)

        anomalies = quality.scan_anomalies(data_dir=tmp_path)
        neg = [a for a in anomalies if a.issue == "non_positive_price"]
        assert len(neg) == 1

    def test_detects_zero_volume(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        df.iloc[2, df.columns.get_loc("Volume")] = 0
        store.save("TEST", df, data_dir=tmp_path)

        anomalies = quality.scan_anomalies(data_dir=tmp_path)
        zero_vol = [a for a in anomalies if a.issue == "zero_volume"]
        assert len(zero_vol) == 1

    def test_clean_data_no_anomalies(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        df["High"] = df[["Open", "Close"]].max(axis=1) + 5
        df["Low"] = df[["Open", "Close"]].min(axis=1) - 5
        store.save("CLEAN", df, data_dir=tmp_path)

        anomalies = quality.scan_anomalies(data_dir=tmp_path)
        ticker_anomalies = [a for a in anomalies if a.ticker == "CLEAN" and a.issue != "zero_volume"]
        assert len(ticker_anomalies) == 0

    def test_empty_dir(self, tmp_path):
        assert quality.scan_anomalies(data_dir=tmp_path) == []


class TestStaleness:
    def test_detects_stale_ticker(self, tmp_path, sample_ohlcv):
        from datetime import date, timedelta

        old_start = date.today() - timedelta(days=60)
        df = sample_ohlcv(days=10, start_date=old_start)
        store.save("STALE", df, data_dir=tmp_path)

        stale = quality.scan_staleness(stale_days=3, data_dir=tmp_path)
        assert len(stale) == 1
        assert stale[0]["ticker"] == "STALE"
        assert int(str(stale[0]["days_stale"])) > 3

    def test_fresh_ticker_not_stale(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=5)
        store.save("FRESH", df, data_dir=tmp_path)

        stale = quality.scan_staleness(stale_days=3, data_dir=tmp_path)
        assert len(stale) == 0

    def test_empty_dir(self, tmp_path):
        assert quality.scan_staleness(data_dir=tmp_path) == []


class TestCompleteness:
    def test_full_completeness(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        store.save("FULL", df, data_dir=tmp_path)

        items = quality.scan_completeness(data_dir=tmp_path)
        assert len(items) == 1
        assert items[0]["fill_pct"] == 100.0
        assert items[0]["nan_pct"] == 0.0

    def test_partial_nan(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        df.iloc[0, df.columns.get_loc("Open")] = np.nan
        df.iloc[1, df.columns.get_loc("Open")] = np.nan
        store.save("PARTIAL", df, data_dir=tmp_path)

        items = quality.scan_completeness(data_dir=tmp_path)
        assert len(items) == 1
        assert items[0]["fill_pct"] < 100.0
        assert items[0]["nan_pct"] > 0.0

    def test_empty_dir(self, tmp_path):
        assert quality.scan_completeness(data_dir=tmp_path) == []


class TestDetectGaps:
    def test_detects_missing_days(self, tmp_path, sample_ohlcv):
        from datetime import date, timedelta

        start = date(2024, 1, 2)
        df = sample_ohlcv(days=20, start_date=start)
        df = df.drop(df.index[5:8])
        store.save("GAPPY", df, data_dir=tmp_path)

        gaps = quality.detect_gaps("GAPPY", data_dir=tmp_path)
        assert len(gaps) > 0

    def test_no_gaps(self, tmp_path, sample_ohlcv):
        from datetime import date

        start = date(2024, 1, 2)
        df = sample_ohlcv(days=5, start_date=start)
        store.save("SOLID", df, data_dir=tmp_path)

        gaps = quality.detect_gaps("SOLID", data_dir=tmp_path)
        assert len(gaps) == 0

    def test_nonexistent_ticker(self, tmp_path):
        gaps = quality.detect_gaps("NONEXIST", data_dir=tmp_path)
        assert gaps == []

    def test_intraday_skipped(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=10)
        store.save("INTRA", df, data_dir=tmp_path, interval="1h")

        gaps = quality.detect_gaps("INTRA", interval="1h", data_dir=tmp_path)
        assert gaps == []


class TestDetectOutliers:
    def test_detects_spike(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=60)
        df.iloc[50, df.columns.get_loc("Close")] = df["Close"].mean() * 5
        store.save("SPIKE", df, data_dir=tmp_path)

        outliers = quality.detect_outliers("SPIKE", threshold=3.0, data_dir=tmp_path)
        assert len(outliers) >= 1

    def test_no_outliers_in_normal_data(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=60)
        df["Close"] = np.linspace(100, 110, len(df))
        store.save("SMOOTH", df, data_dir=tmp_path)

        outliers = quality.detect_outliers("SMOOTH", data_dir=tmp_path)
        assert len(outliers) == 0

    def test_too_few_rows(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=5)
        store.save("SHORT", df, data_dir=tmp_path)

        outliers = quality.detect_outliers("SHORT", window=20, data_dir=tmp_path)
        assert outliers == []

    def test_nonexistent_ticker(self, tmp_path):
        assert quality.detect_outliers("NOPE", data_dir=tmp_path) == []


class TestGenerateReport:
    def test_full_report(self, tmp_path, sample_ohlcv):
        df = sample_ohlcv(days=30)
        df["High"] = df[["Open", "Close"]].max(axis=1) + 5
        df["Low"] = df[["Open", "Close"]].min(axis=1) - 5
        store.save("RPT1", df, data_dir=tmp_path)
        store.save("RPT2", df, data_dir=tmp_path)

        report = quality.generate_report(data_dir=tmp_path)
        assert report.total_files == 2
        assert report.total_rows == 60
        assert len(report.tickers) == 2

    def test_empty_dir(self, tmp_path):
        report = quality.generate_report(data_dir=tmp_path)
        assert report.total_files == 0
        assert report.total_rows == 0
