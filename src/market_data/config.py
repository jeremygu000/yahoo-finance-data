import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("MARKET_DATA_DIR", str(Path.home() / ".market_data" / "parquet")))
LOG_DIR = Path(os.environ.get("MARKET_DATA_LOG_DIR", str(Path.home() / ".market_data" / "logs")))

DEFAULT_TICKERS: list[str] = [
    # --- Original ---
    "QQQ",
    "^VIX",
    "USO",
    "XOM",
    "XLE",
    "CRM",
    # --- Broad market & factors ---
    "SPY",
    "IWM",
    "MTUM",
    # --- Sectors ---
    "XLK",
    "XLF",
    "XLV",
    "XLI",
    "XLY",
    # --- Fixed income & commodities ---
    "TLT",
    "IEF",
    "GLD",
    # --- Mega-cap tech ---
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "TSLA",
    # --- Consumer & financials ---
    "WMT",
    "HD",
    "MCD",
    "COST",
    "JPM",
    "V",
    "MA",
    # --- Healthcare ---
    "JNJ",
    "UNH",
]

LOOKBACK_DAYS = int(os.environ.get("MARKET_DATA_LOOKBACK_DAYS", "365"))
MIN_ROLLING_DAYS = 30
FETCH_INTERVAL = "1d"

VALID_INTERVALS: list[str] = ["1d", "1h", "15m", "5m"]
DEFAULT_INTERVAL = "1d"
MAX_RETRIES = int(os.environ.get("MARKET_DATA_MAX_RETRIES", "3"))
RETRY_DELAY_RANGE = (1.0, 3.0)

_default_cors = "http://localhost:3000,http://127.0.0.1:3000"
CORS_ORIGINS: list[str] = [
    o.strip() for o in os.environ.get("MARKET_DATA_CORS_ORIGINS", _default_cors).split(",") if o.strip()
]

WS_POLL_INTERVAL = int(os.environ.get("MARKET_DATA_WS_POLL_INTERVAL", "30"))

CACHE_TTL_SECONDS = int(os.environ.get("MARKET_DATA_CACHE_TTL", "60"))
CACHE_MAX_ENTRIES = int(os.environ.get("MARKET_DATA_CACHE_MAX_ENTRIES", "256"))

API_KEY: str | None = os.environ.get("MARKET_DATA_API_KEY")

# --- Notification channels ---
TELEGRAM_BOT_TOKEN: str | None = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_DEFAULT_CHAT_ID: str | None = os.environ.get("TELEGRAM_DEFAULT_CHAT_ID")

SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME: str | None = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD: str | None = os.environ.get("SMTP_PASSWORD")
SMTP_FROM: str | None = os.environ.get("SMTP_FROM")

# --- AI / Ollama ---
OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "qwen3:32b")
OLLAMA_TIMEOUT: int = int(os.environ.get("OLLAMA_TIMEOUT", "180"))
