# market-data

Shared Yahoo Finance market data provider. Fetches daily OHLCV data, stores as Parquet, and exposes it to local Python projects via a simple API. Includes a web dashboard for visualization.

## Architecture

```
market-data fetch (CLI / launchd)
    ↓ yfinance batch download
~/.market_data/parquet/*.parquet
    ↓ read
Python API (get_ohlcv / get_latest)    ←  other local projects import this
FastAPI server (:8100)                 ←  web dashboard consumes this
Next.js dashboard (:3000)
```

## Quick Start

```bash
# Install
uv sync

# Fetch all default tickers (QQQ, ^VIX, USO, XOM, XLE, CRM)
uv run market-data fetch

# Check what's cached
uv run market-data status
```

## CLI

```bash
market-data fetch                    # Incremental fetch (rolling 30-day window)
market-data fetch --full             # Full 1-year historical fetch
market-data fetch --tickers AAPL,MSFT  # Custom tickers
market-data status                   # Show cached data summary
market-data clean                    # Remove data older than 365 days
market-data clean --keep-days 180    # Custom retention
```

## Python API

Use from any local Python project:

```python
from market_data import get_ohlcv, get_latest, list_tickers

# Get last 30 days of QQQ OHLCV data as DataFrame
df = get_ohlcv("QQQ", days=30)

# Latest data point as dict
latest = get_latest("CRM")

# All cached tickers
tickers = list_tickers()
```

## Web Dashboard

Interactive data visualization at `http://localhost:3000`:

- **Ticker Overview** — Cards with latest price, daily change, volume
- **Candlestick Chart** — K-line with volume bars (Lightweight Charts)
- **Price Comparison** — Multi-ticker overlay line chart
- **Data Table** — Sortable OHLCV table with pagination
- **VIX Dashboard** — Current VIX, zone gauge, historical chart

```bash
# Terminal 1: Start API server
uv run uvicorn market_data.server:app --port 8100

# Terminal 2: Start web dashboard
cd web && pnpm dev
```

## Scheduled Fetch (macOS)

Auto-fetch Mon–Fri after US market close:

```bash
bash install_schedule.sh
```

Installs a launchd plist that runs `market-data fetch` at 20:35 UTC (4:35 PM ET). Logs to `~/.market_data/logs/`.

## Data Storage

| Item            | Detail                                         |
| --------------- | ---------------------------------------------- |
| Location        | `~/.market_data/parquet/`                      |
| Format          | Apache Parquet (pyarrow)                       |
| Schema          | DatetimeIndex + Open, High, Low, Close, Volume |
| Default tickers | QQQ, ^VIX, USO, XOM, XLE, CRM                  |
| Retention       | 1 year (configurable)                          |
| Rolling window  | Last 30 days always refreshed                  |

## Project Structure

```
yahoo-finance-data/
├── src/market_data/
│   ├── __init__.py       # Public API re-exports
│   ├── api.py            # get_ohlcv, get_latest, list_tickers
│   ├── cli.py            # CLI entry point
│   ├── config.py         # Paths, tickers, constants
│   ├── fetcher.py        # yfinance batch download + retry
│   ├── server.py         # FastAPI REST endpoints
│   └── store.py          # Parquet read/write/dedup
├── web/                  # Next.js dashboard
│   └── src/
│       ├── app/          # App Router pages
│       ├── components/   # Chart + table components
│       └── lib/          # API client + types
├── tests/                # pytest suite (22 tests)
├── install_schedule.sh   # launchd installer
└── pyproject.toml
```

## Development

```bash
# Run tests
uv run pytest -v

# Build web
cd web && pnpm build
```

## Requirements

- Python 3.12+
- Node.js 18+ / pnpm (for web dashboard)
- uv (Python package manager)
