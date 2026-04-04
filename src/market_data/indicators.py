"""Technical indicators computed from OHLCV DataFrames using pure pandas/numpy."""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(df: pd.DataFrame, column: str = "Close", period: int = 20) -> pd.DataFrame:
    """Simple Moving Average.

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Column to compute the indicator on (default: "Close").
        period: Rolling window size (default: 20).

    Returns:
        DataFrame with a single column ``SMA_{period}``.
        Rows with insufficient history are NaN.
    """
    if df.empty:
        return pd.DataFrame(index=df.index, columns=[f"SMA_{period}"], dtype=float)

    result = df[[column]].copy()
    col_name = f"SMA_{period}"
    result[col_name] = result[column].rolling(window=period, min_periods=period).mean()
    return result[[col_name]]


def ema(df: pd.DataFrame, column: str = "Close", period: int = 20) -> pd.DataFrame:
    """Exponential Moving Average.

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Column to compute the indicator on (default: "Close").
        period: Span for EWM (default: 20).

    Returns:
        DataFrame with a single column ``EMA_{period}``.
        Rows with insufficient history (< period rows) are NaN.
    """
    if df.empty:
        return pd.DataFrame(index=df.index, columns=[f"EMA_{period}"], dtype=float)

    col_name = f"EMA_{period}"
    values = df[column].ewm(span=period, adjust=False, min_periods=period).mean()
    return pd.DataFrame({col_name: values}, index=df.index)


def rsi(df: pd.DataFrame, column: str = "Close", period: int = 14) -> pd.DataFrame:
    """Relative Strength Index (Wilder smoothing).

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Column to compute the indicator on (default: "Close").
        period: RSI window (default: 14).

    Returns:
        DataFrame with a single column ``RSI_{period}`` on 0-100 scale.
        First ``period`` rows are NaN.
    """
    col_name = f"RSI_{period}"
    if df.empty:
        return pd.DataFrame(index=df.index, columns=[col_name], dtype=float)

    delta = df[column].diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # Wilder smoothing: first avg = simple mean of first `period` values, then EWM
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi_values = 100.0 - (100.0 / (1.0 + rs))

    # When avg_loss is 0, RSI = 100 (pure up-trend)
    rsi_values = rsi_values.where(avg_loss != 0.0, other=100.0)

    return pd.DataFrame({col_name: rsi_values}, index=df.index)


def macd(
    df: pd.DataFrame,
    column: str = "Close",
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Moving Average Convergence/Divergence.

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Column to compute the indicator on (default: "Close").
        fast: Fast EMA period (default: 12).
        slow: Slow EMA period (default: 26).
        signal: Signal line EMA period (default: 9).

    Returns:
        DataFrame with columns ``MACD``, ``Signal``, ``Histogram``.
        Rows with insufficient history are NaN.
    """
    if df.empty:
        return pd.DataFrame(index=df.index, columns=["MACD", "Signal", "Histogram"], dtype=float)

    fast_ema = df[column].ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = df[column].ewm(span=slow, adjust=False, min_periods=slow).mean()

    macd_line = fast_ema - slow_ema
    # Signal line only valid once macd_line has enough non-NaN points
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame(
        {"MACD": macd_line, "Signal": signal_line, "Histogram": histogram},
        index=df.index,
    )


def bollinger_bands(
    df: pd.DataFrame,
    column: str = "Close",
    period: int = 20,
    std_dev: float = 2.0,
) -> pd.DataFrame:
    """Bollinger Bands.

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Column to compute the indicator on (default: "Close").
        period: Rolling window size (default: 20).
        std_dev: Number of standard deviations (default: 2.0).

    Returns:
        DataFrame with columns ``BB_Upper``, ``BB_Middle``, ``BB_Lower``.
        Rows with insufficient history are NaN.
    """
    if df.empty:
        return pd.DataFrame(index=df.index, columns=["BB_Upper", "BB_Middle", "BB_Lower"], dtype=float)

    rolling = df[column].rolling(window=period, min_periods=period)
    middle = rolling.mean()
    std = rolling.std(ddof=1)

    upper = middle + std_dev * std
    lower = middle - std_dev * std

    return pd.DataFrame(
        {"BB_Upper": upper, "BB_Middle": middle, "BB_Lower": lower},
        index=df.index,
    )
