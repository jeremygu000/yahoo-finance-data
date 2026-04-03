import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("MARKET_DATA_DIR", str(Path.home() / ".market_data" / "parquet")))
LOG_DIR = Path(os.environ.get("MARKET_DATA_LOG_DIR", str(Path.home() / ".market_data" / "logs")))

DEFAULT_TICKERS: list[str] = [
    "QQQ",
    "^VIX",
    "USO",
    "XOM",
    "XLE",
    "CRM",
]

LOOKBACK_DAYS = int(os.environ.get("MARKET_DATA_LOOKBACK_DAYS", "365"))
MIN_ROLLING_DAYS = 30
FETCH_INTERVAL = "1d"
MAX_RETRIES = int(os.environ.get("MARKET_DATA_MAX_RETRIES", "3"))
RETRY_DELAY_RANGE = (1.0, 3.0)

_default_cors = "http://localhost:3000,http://127.0.0.1:3000"
CORS_ORIGINS: list[str] = [
    o.strip() for o in os.environ.get("MARKET_DATA_CORS_ORIGINS", _default_cors).split(",") if o.strip()
]

WS_POLL_INTERVAL = int(os.environ.get("MARKET_DATA_WS_POLL_INTERVAL", "30"))
