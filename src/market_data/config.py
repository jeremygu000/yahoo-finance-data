from pathlib import Path

DATA_DIR = Path.home() / ".market_data" / "parquet"
LOG_DIR = Path.home() / ".market_data" / "logs"

DEFAULT_TICKERS: list[str] = [
    "QQQ",
    "^VIX",
    "USO",
    "XOM",
    "XLE",
    "CRM",
]

LOOKBACK_DAYS = 365
MIN_ROLLING_DAYS = 30
FETCH_INTERVAL = "1d"
MAX_RETRIES = 3
RETRY_DELAY_RANGE = (1.0, 3.0)
