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


def vwap(df: pd.DataFrame, column: str = "Close", period: int = 20) -> pd.DataFrame:
    """Volume Weighted Average Price.

    Uses typical price ``(High + Low + Close) / 3`` weighted by volume.
    The *period* parameter is accepted for API compatibility but ignored;
    VWAP is a cumulative indicator.

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Unused (kept for API compatibility).
        period: Unused (kept for API compatibility).

    Returns:
        DataFrame with a single column ``VWAP``.
    """
    col_name = "VWAP"
    if df.empty:
        return pd.DataFrame(index=df.index, columns=[col_name], dtype=float)

    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    cum_tp_vol = (typical_price * df["Volume"]).cumsum()
    cum_vol = df["Volume"].cumsum()
    vwap_values = cum_tp_vol / cum_vol.replace(0.0, np.nan)
    return pd.DataFrame({col_name: vwap_values}, index=df.index)


def atr(df: pd.DataFrame, column: str = "Close", period: int = 14) -> pd.DataFrame:
    """Average True Range (Wilder smoothing).

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Unused (kept for API compatibility).
        period: Smoothing window (default: 14).

    Returns:
        DataFrame with a single column ``ATR_{period}``.
        First ``period`` rows are NaN.
    """
    col_name = f"ATR_{period}"
    if df.empty:
        return pd.DataFrame(index=df.index, columns=[col_name], dtype=float)

    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_values = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return pd.DataFrame({col_name: atr_values}, index=df.index)


def stochastic(
    df: pd.DataFrame,
    column: str = "Close",
    period: int = 14,
    smooth_k: int = 3,
) -> pd.DataFrame:
    """Stochastic Oscillator (%K and %D).

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Unused (uses High/Low/Close).
        period: Lookback window for %K (default: 14).
        smooth_k: SMA smoothing for %D (default: 3).

    Returns:
        DataFrame with columns ``Stoch_K`` and ``Stoch_D`` on 0-100 scale.
    """
    if df.empty:
        return pd.DataFrame(index=df.index, columns=["Stoch_K", "Stoch_D"], dtype=float)

    lowest_low = df["Low"].rolling(window=period, min_periods=period).min()
    highest_high = df["High"].rolling(window=period, min_periods=period).max()

    denom = highest_high - lowest_low
    k = ((df["Close"] - lowest_low) / denom.replace(0.0, np.nan)) * 100.0
    d = k.rolling(window=smooth_k, min_periods=smooth_k).mean()

    return pd.DataFrame({"Stoch_K": k, "Stoch_D": d}, index=df.index)


def obv(df: pd.DataFrame, column: str = "Close", period: int = 20) -> pd.DataFrame:
    """On Balance Volume.

    Cumulative volume: added when price rises, subtracted when it falls.
    The *period* parameter is accepted for API compatibility but ignored.

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Price column for direction (default: "Close").
        period: Unused (kept for API compatibility).

    Returns:
        DataFrame with a single column ``OBV``.
    """
    col_name = "OBV"
    if df.empty:
        return pd.DataFrame(index=df.index, columns=[col_name], dtype=float)

    direction = np.sign(df[column].diff())
    obv_values = (direction * df["Volume"]).fillna(0.0).cumsum()
    return pd.DataFrame({col_name: obv_values}, index=df.index)


def adx(df: pd.DataFrame, column: str = "Close", period: int = 14) -> pd.DataFrame:
    """Average Directional Index (Wilder smoothing).

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        column: Unused (uses High/Low/Close).
        period: Smoothing window (default: 14).

    Returns:
        DataFrame with columns ``ADX_{period}``, ``Plus_DI``, ``Minus_DI``.
        First ``2 * period`` rows are NaN for ADX.
    """
    col_name = f"ADX_{period}"
    if df.empty:
        return pd.DataFrame(index=df.index, columns=[col_name, "Plus_DI", "Minus_DI"], dtype=float)

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    # Directional movement
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=df.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=df.index,
    )

    # True Range
    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    alpha = 1.0 / period

    # Wilder smoothing
    atr_smooth = tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    plus_dm_smooth = plus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    plus_di = (plus_dm_smooth / atr_smooth.replace(0.0, np.nan)) * 100.0
    minus_di = (minus_dm_smooth / atr_smooth.replace(0.0, np.nan)) * 100.0

    di_sum = plus_di + minus_di
    dx = ((plus_di - minus_di).abs() / di_sum.replace(0.0, np.nan)) * 100.0
    adx_values = dx.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    return pd.DataFrame(
        {col_name: adx_values, "Plus_DI": plus_di, "Minus_DI": minus_di},
        index=df.index,
    )
