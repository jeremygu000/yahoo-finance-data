"""Data quality checks for OHLCV Parquet files.

Uses DuckDB for high-performance scanning across all ticker files.
Detects: price anomalies, NaN density, staleness, completeness,
trading day gaps, and statistical outliers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

from market_data.config import DATA_DIR, VALID_INTERVALS
from market_data.duckdb_reader import _cursor, _glob_pattern, _parse_ticker_from_filename

logger = logging.getLogger(__name__)


@dataclass
class AnomalyRecord:
    """Single data quality anomaly."""

    ticker: str
    issue: str
    count: int
    detail: str = ""


@dataclass
class TickerQuality:
    """Per-ticker quality summary."""

    ticker: str
    interval: str
    rows: int
    first_date: str
    last_date: str
    days_stale: int
    completeness_pct: float
    nan_pct: float
    anomalies: list[AnomalyRecord] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    outliers: int = 0


@dataclass
class QualityReport:
    """Full quality scan report."""

    scan_date: str
    total_files: int
    total_rows: int
    tickers: list[TickerQuality] = field(default_factory=list)
    anomalies: list[AnomalyRecord] = field(default_factory=list)


def scan_anomalies(data_dir: Path = DATA_DIR) -> list[AnomalyRecord]:
    """Detect basic OHLCV anomalies across all Parquet files.

    Checks:
      - High < Low (inverted prices)
      - Close outside [Low, High] range
      - Zero or negative prices
      - Zero volume (on data that has volume)
      - NaN in Close column
    """
    pattern = _glob_pattern(data_dir)
    if not data_dir.exists() or not list(data_dir.glob("*.parquet")):
        return []

    conn = _cursor(data_dir)
    records: list[AnomalyRecord] = []

    try:
        rows = conn.execute(
            """
            SELECT filename, COUNT(*) AS cnt
            FROM read_parquet(?, filename=true, hive_partitioning=false)
            WHERE "High" < "Low"
            GROUP BY filename
            """,
            [pattern],
        ).fetchall()
        for fname, cnt in rows:
            ticker, _ = _parse_ticker_from_filename(fname)
            records.append(AnomalyRecord(ticker, "high_lt_low", cnt, "High < Low"))
    except duckdb.IOException:
        pass

    try:
        rows = conn.execute(
            """
            SELECT filename, COUNT(*) AS cnt
            FROM read_parquet(?, filename=true, hive_partitioning=false)
            WHERE "Close" < "Low" OR "Close" > "High"
            GROUP BY filename
            """,
            [pattern],
        ).fetchall()
        for fname, cnt in rows:
            ticker, _ = _parse_ticker_from_filename(fname)
            records.append(AnomalyRecord(ticker, "close_out_of_range", cnt, "Close outside [Low, High]"))
    except duckdb.IOException:
        pass

    try:
        rows = conn.execute(
            """
            SELECT filename, COUNT(*) AS cnt
            FROM read_parquet(?, filename=true, hive_partitioning=false)
            WHERE "Open" <= 0 OR "High" <= 0 OR "Low" <= 0 OR "Close" <= 0
            GROUP BY filename
            """,
            [pattern],
        ).fetchall()
        for fname, cnt in rows:
            ticker, _ = _parse_ticker_from_filename(fname)
            records.append(AnomalyRecord(ticker, "non_positive_price", cnt, "Price <= 0"))
    except duckdb.IOException:
        pass

    try:
        rows = conn.execute(
            """
            SELECT filename, COUNT(*) AS cnt
            FROM read_parquet(?, filename=true, hive_partitioning=false)
            WHERE "Volume" = 0
            GROUP BY filename
            """,
            [pattern],
        ).fetchall()
        for fname, cnt in rows:
            ticker, _ = _parse_ticker_from_filename(fname)
            records.append(AnomalyRecord(ticker, "zero_volume", cnt, "Volume = 0"))
    except duckdb.IOException:
        pass

    try:
        rows = conn.execute(
            """
            SELECT filename, COUNT(*) AS cnt
            FROM read_parquet(?, filename=true, hive_partitioning=false)
            WHERE "Close" IS NULL OR isnan("Close")
            GROUP BY filename
            """,
            [pattern],
        ).fetchall()
        for fname, cnt in rows:
            ticker, _ = _parse_ticker_from_filename(fname)
            records.append(AnomalyRecord(ticker, "null_close", cnt, "Close is NULL/NaN"))
    except duckdb.IOException:
        pass

    return records


def scan_staleness(
    stale_days: int = 3,
    data_dir: Path = DATA_DIR,
) -> list[dict[str, object]]:
    """Find tickers whose latest data is older than *stale_days* calendar days."""
    pattern = _glob_pattern(data_dir)
    if not data_dir.exists() or not list(data_dir.glob("*.parquet")):
        return []

    conn = _cursor(data_dir)
    try:
        rows = conn.execute(
            """
            SELECT
                filename,
                COUNT(*) AS rows,
                MIN("Date") AS first_date,
                MAX("Date") AS last_date
            FROM read_parquet(?, filename=true, hive_partitioning=false)
            GROUP BY filename
            ORDER BY MAX("Date") ASC
            """,
            [pattern],
        ).fetchall()
    except duckdb.IOException:
        return []

    today = date.today()
    stale: list[dict[str, object]] = []
    for fname, row_count, first_dt, last_dt in rows:
        ticker, interval = _parse_ticker_from_filename(fname)
        last_d = pd.Timestamp(last_dt).date()
        delta = (today - last_d).days
        if delta > stale_days:
            stale.append(
                {
                    "ticker": ticker,
                    "interval": interval,
                    "rows": row_count,
                    "last_date": last_d.isoformat(),
                    "days_stale": delta,
                }
            )
    return stale


def scan_completeness(data_dir: Path = DATA_DIR) -> list[dict[str, object]]:
    """Per-file NaN density and field fill rates."""
    pattern = _glob_pattern(data_dir)
    if not data_dir.exists() or not list(data_dir.glob("*.parquet")):
        return []

    conn = _cursor(data_dir)
    try:
        rows = conn.execute(
            """
            SELECT
                filename,
                COUNT(*) AS total,
                COUNT("Open") AS open_ok,
                COUNT("High") AS high_ok,
                COUNT("Low") AS low_ok,
                COUNT("Close") AS close_ok,
                COUNT("Volume") AS vol_ok
            FROM read_parquet(?, filename=true, hive_partitioning=false)
            GROUP BY filename
            """,
            [pattern],
        ).fetchall()
    except duckdb.IOException:
        return []

    items: list[dict[str, object]] = []
    for fname, total, o_ok, h_ok, l_ok, c_ok, v_ok in rows:
        ticker, interval = _parse_ticker_from_filename(fname)
        if total == 0:
            continue
        fill_pct = round((o_ok + h_ok + l_ok + c_ok + v_ok) / (total * 5) * 100, 2)
        nan_pct = round(100 - fill_pct, 2)
        items.append(
            {
                "ticker": ticker,
                "interval": interval,
                "rows": total,
                "fill_pct": fill_pct,
                "nan_pct": nan_pct,
                "open_fill": round(o_ok / total * 100, 2),
                "high_fill": round(h_ok / total * 100, 2),
                "low_fill": round(l_ok / total * 100, 2),
                "close_fill": round(c_ok / total * 100, 2),
                "volume_fill": round(v_ok / total * 100, 2),
            }
        )
    return items


def detect_gaps(
    ticker: str,
    interval: str = "1d",
    exchange: str = "XNYS",
    data_dir: Path = DATA_DIR,
) -> list[str]:
    """Detect missing trading days for a single ticker.

    Uses exchange_calendars if available, otherwise falls back to a simple
    weekday-only heuristic.

    Returns list of missing date strings (YYYY-MM-DD).
    """
    from market_data.store import validate_ticker

    safe = validate_ticker(ticker)
    fpath = data_dir / f"{safe}_{interval}.parquet"
    if not fpath.exists():
        return []

    conn = _cursor(data_dir)
    try:
        dates_raw = conn.execute(
            """
            SELECT DISTINCT CAST("Date" AS DATE) AS d
            FROM read_parquet(?, hive_partitioning=false)
            ORDER BY d
            """,
            [str(fpath)],
        ).fetchall()
    except duckdb.IOException:
        return []

    if not dates_raw:
        return []

    actual_dates: set[date] = {row[0] for row in dates_raw}
    min_date = min(actual_dates)
    max_date = max(actual_dates)

    # Only detect gaps for daily data
    if interval != "1d":
        return []

    expected = _expected_trading_days(min_date, max_date, exchange)
    missing = sorted(expected - actual_dates)
    return [d.isoformat() for d in missing]


def _expected_trading_days(start: date, end: date, exchange: str) -> set[date]:
    """Generate expected trading days between start and end.

    Tries exchange_calendars first; falls back to simple weekday heuristic.
    """
    try:
        import exchange_calendars as xcals  # type: ignore[import-untyped]

        cal = xcals.get_calendar(exchange)
        sessions = cal.sessions_in_range(
            pd.Timestamp(start),
            pd.Timestamp(end),
        )
        return {ts.date() for ts in sessions}
    except ImportError:
        logger.debug("exchange_calendars not installed, using weekday heuristic")
    except Exception as exc:
        logger.warning("exchange_calendars error (%s), using weekday heuristic", exc)

    # Fallback: weekdays only
    days: set[date] = set()
    current = start
    while current <= end:
        if current.weekday() < 5:  # Mon-Fri
            days.add(current)
        current += timedelta(days=1)
    return days


def detect_outliers(
    ticker: str,
    interval: str = "1d",
    window: int = 20,
    threshold: float = 4.0,
    data_dir: Path = DATA_DIR,
) -> list[dict[str, object]]:
    """Detect price outliers using rolling Z-score.

    A row is flagged if abs(z-score) > threshold based on a *window*-day
    rolling mean and std of daily returns.
    """
    from market_data.store import validate_ticker

    safe = validate_ticker(ticker)
    fpath = data_dir / f"{safe}_{interval}.parquet"
    if not fpath.exists():
        return []

    conn = _cursor(data_dir)
    try:
        df = conn.execute(
            """
            SELECT "Date", "Close"
            FROM read_parquet(?, hive_partitioning=false)
            ORDER BY "Date"
            """,
            [str(fpath)],
        ).df()
    except duckdb.IOException:
        return []

    if len(df) < window + 1:
        return []

    df["return"] = df["Close"].pct_change()
    df["roll_mean"] = df["return"].rolling(window).mean()
    df["roll_std"] = df["return"].rolling(window).std()
    df["zscore"] = (df["return"] - df["roll_mean"]) / df["roll_std"].replace(0, float("nan"))

    outliers_df = df[df["zscore"].abs() > threshold].dropna(subset=["zscore"])

    results: list[dict[str, object]] = []
    for _, row in outliers_df.iterrows():
        results.append(
            {
                "date": pd.Timestamp(row["Date"]).date().isoformat(),
                "close": round(float(row["Close"]), 4),
                "return_pct": round(float(row["return"]) * 100, 2),
                "zscore": round(float(row["zscore"]), 2),
            }
        )
    return results


def generate_report(
    stale_days: int = 3,
    zscore_threshold: float = 4.0,
    data_dir: Path = DATA_DIR,
) -> QualityReport:
    """Run all quality checks and produce a consolidated report."""
    report = QualityReport(
        scan_date=date.today().isoformat(),
        total_files=0,
        total_rows=0,
    )

    report.anomalies = scan_anomalies(data_dir)

    completeness = scan_completeness(data_dir)
    staleness = {(str(s["ticker"]), str(s["interval"])): s for s in scan_staleness(stale_days, data_dir)}

    report.total_files = len(completeness)
    report.total_rows = sum(int(str(c["rows"])) for c in completeness)

    anomaly_index: dict[str, list[AnomalyRecord]] = {}
    for a in report.anomalies:
        anomaly_index.setdefault(a.ticker, []).append(a)

    for c in completeness:
        ticker = str(c["ticker"])
        interval = str(c["interval"])
        key = (ticker, interval)
        stale_info = staleness.get(key)

        tq = TickerQuality(
            ticker=ticker,
            interval=interval,
            rows=int(str(c["rows"])),
            first_date="",
            last_date=str(stale_info["last_date"]) if stale_info else "",
            days_stale=int(str(stale_info["days_stale"])) if stale_info else 0,
            completeness_pct=float(str(c["fill_pct"])),
            nan_pct=float(str(c["nan_pct"])),
            anomalies=anomaly_index.get(ticker, []),
        )
        report.tickers.append(tq)

    return report
