# Competitive Analysis: Open-Source Financial Data Projects

> Last updated: 2026-04-04

A detailed feature-by-feature comparison of yahoo-finance-data against similar high-star open-source projects.

---

## Project Overview

| Project | ⭐ Stars | Positioning | One-liner |
|---|---|---|---|
| **yahoo-finance-data** | — | Data Pipeline + Dashboard | Fetch → Parquet → API → Visualization, lightweight & self-hosted |
| **[OpenBB](https://github.com/OpenBB-finance/OpenBB)** | 60.6k | Financial Data Platform | 35+ data sources, "open-source Bloomberg" for professional analysts |
| **[OpenStock](https://github.com/Open-Dev-Society/OpenStock)** | 10.2k | Stock Tracking Web App | Finnhub + TradingView-powered personal stock tracker |
| **[QuantDinger](https://github.com/brokermr810/QuantDinger)** | 1k | AI Quant Trading Platform | 7-Agent AI system + fully automated trade execution |
| **[OpenAlice](https://github.com/TraderAlice/OpenAlice)** | 3.1k | AI Trading Engine | File-driven AI Agent with self-evolving code modification |
| **[yfinance](https://github.com/ranaroussi/yfinance)** | 22.6k | Data Fetching Library | Python wrapper for Yahoo Finance |
| **[yahooquery](https://github.com/dpguthrie/yahooquery)** | 900 | Data Fetching Library | Alternative Yahoo Finance wrapper with async support |
| **[TradingView-Screener](https://github.com/shner-elmo/TradingView-Screener)** | 851 | Screener Library | TradingView 3000+ indicators with SQL-like filtering |

---

## Feature Matrix

### Data Capabilities

| Feature | yahoo-finance-data | OpenBB | OpenStock | QuantDinger | OpenAlice | yfinance | yahooquery | TV-Screener |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Data Source Count** | 1 (Yahoo) | 35+ | 1 (Finnhub) | 10+ | OpenBB | 1 (Yahoo) | 1 (Yahoo) | 1 (TV) |
| **OHLCV** | ✅ | ✅ | ⚠️ Chart only | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Fundamentals** | ❌ | ✅ | ⚠️ Widget | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Options** | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Crypto** | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Forex** | ❌ | ✅ | ❌ | ✅ (MT5) | ❌ | ✅ | ✅ | ✅ |
| **News** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Real-time Data** | ❌ | ✅ WS | ⚠️ Delayed | ✅ | ✅ SSE | ✅ WS | ❌ | ✅ (auth) |

### Technical Analysis & Indicators

| Feature | yahoo-finance-data | OpenBB | OpenStock | QuantDinger | OpenAlice | yfinance | yahooquery | TV-Screener |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Technical Indicators** | ✅ 5 types | ✅ 30+ | ✅ TV embed | ✅ TA-Lib | ✅ Built-in | ❌ External | ❌ External | ✅ 3000+ |
| **Candlestick Charts** | ✅ lightweight-charts | ✅ Multiple | ✅ TV embed | ✅ KlineCharts | ✅ | ❌ Data only | ❌ Data only | ❌ Data only |
| **Backtesting** | ❌ | ⚠️ Basic | ❌ | ✅ Full engine | ⚠️ Git-style | ❌ | ❌ | ❌ |
| **Screener/Search** | ✅ Search | ✅ | ⚠️ Basic | ❌ | ❌ | ✅ Basic | ✅ Predefined | ✅ SQL-like |

### Storage & Architecture

| Feature | yahoo-finance-data | OpenBB | OpenStock | QuantDinger | OpenAlice | yfinance | yahooquery | TV-Screener |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Storage** | Parquet files | None (on-demand) | MongoDB | PostgreSQL | JSON/JSONL files | SQLite cache | In-memory | In-memory |
| **REST API** | ✅ FastAPI | ✅ FastAPI | Next.js Actions | ✅ Flask | MCP Server | ❌ | ❌ | ❌ |
| **WebSocket** | ✅ | ✅ | ❌ | ✅ | ✅ SSE | ✅ | ❌ | ❌ |
| **CSV Export** | ✅ | ✅ | ❌ | ⚠️ pg_dump | JSONL | DataFrame | DataFrame | DataFrame |

### Frontend & User Experience

| Feature | yahoo-finance-data | OpenBB | OpenStock | QuantDinger | OpenAlice | yfinance | yahooquery | TV-Screener |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Web Frontend** | ✅ Next.js | ✅ React | ✅ Next.js 15 | ✅ Vue.js | ✅ Hono | ❌ | ❌ | ❌ |
| **UI Framework** | MUI | Custom | shadcn/ui | Ant Design | Custom | — | — | — |
| **Portfolio Page** | ✅ | ✅ | ✅ Watchlist | ✅ | ✅ | — | — | — |
| **Dark Mode** | ✅ | ✅ | ✅ Default | ✅ | ✅ | — | — | — |
| **Cmd+K Search** | ❌ | ❌ | ✅ | ❌ | ❌ | — | — | — |

### Operations & Deployment

| Feature | yahoo-finance-data | OpenBB | OpenStock | QuantDinger | OpenAlice | yfinance | yahooquery | TV-Screener |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Deployment** | Local (launchd) | Local/Docker/Cloud | Docker/Vercel | Docker Compose | Local (Node.js) | pip install | pip install | pip install |
| **Multi-user** | ❌ | ✅ Enterprise | ✅ Better Auth | ✅ OAuth+RBAC | ❌ | — | — | — |
| **Scheduled Tasks** | ✅ launchd | ❌ | ✅ Inngest | ✅ AI radar | ✅ Cron | — | — | — |
| **Alerts** | ❌ | ❌ | ✅ Email | ✅ TG/Discord/Email | ✅ Telegram | — | — | — |

### AI & Trading

| Feature | yahoo-finance-data | OpenBB | OpenStock | QuantDinger | OpenAlice | yfinance | yahooquery | TV-Screener |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **AI Features** | ❌ | ✅ Copilot+MCP | ✅ Gemini summaries | ✅ 7-Agent system | ✅ Cognitive brain | ❌ | ❌ | ❌ |
| **Live Trading** | ❌ | ❌ | ❌ | ✅ 10+ exchanges | ✅ CCXT/Alpaca/IBKR | ❌ | ❌ | ❌ |
| **Paper Trading** | ❌ | ❌ | ❌ | ✅ Virtual positions | ✅ Mock Broker | ❌ | ❌ | ❌ |

### Tech Stack & License

| Project | Backend | Frontend | License |
|---|---|---|---|
| **yahoo-finance-data** | Python / FastAPI | Next.js / MUI | — |
| **OpenBB** | Python / FastAPI | React | AGPL-3.0 |
| **OpenStock** | Next.js (fullstack) | Next.js / shadcn | AGPL-3.0 |
| **QuantDinger** | Python / Flask | Vue.js / Ant Design | Apache 2.0 |
| **OpenAlice** | TypeScript / Node.js | Hono / Custom | AGPL-3.0 |
| **yfinance** | Python | — | Apache 2.0 |
| **yahooquery** | Python | — | MIT |
| **TV-Screener** | Python | — | MIT |

---

## Competitive Positioning

### Our Unique Strengths

| Strength | Why It Matters |
|---|---|
| **Parquet local storage** | No database setup; columnar format ideal for time-series; direct read by pandas/polars |
| **Zero-dependency architecture** | No Docker, no Kubernetes, no Airflow — just `pip install` and go |
| **launchd scheduling** | Native macOS integration, no external scheduler needed |
| **FastAPI + lightweight-charts** | Modern, performant stack without bloat |
| **Cross-project compatibility** | Parquet files consumed directly by algorithmic-trading project |

### Potential Growth Directions

| Direction | Reference Project | Effort |
|---|---|---|
| Cmd+K global search | OpenStock | ⭐⭐ |
| Price alerts + Telegram/Email notifications | QuantDinger | ⭐⭐⭐ |
| Multi-data-source support (Polygon, Finnhub) | OpenBB's Provider architecture | ⭐⭐⭐⭐ |
| AI market summaries | OpenStock (Gemini) / QuantDinger (7-Agent) | ⭐⭐⭐ |
| Backtesting engine | QuantDinger | ⭐⭐⭐⭐ |
| Multi-user authentication | OpenStock (Better Auth) | ⭐⭐⭐ |

---

## Detailed Project Profiles

### OpenBB (60.6k ⭐)

- **Data Sources**: 35+ providers — Yahoo Finance, Polygon, Alpha Vantage, FMP, Tiingo, FRED, SEC, ECB, IMF, OECD, etc.
- **Data Types**: OHLCV, fundamentals, options, crypto, forex, ETFs, fixed income, commodities, economic indicators, news, SEC filings
- **Storage**: On-demand fetching (connector model), no built-in database
- **API**: REST (FastAPI), Python SDK, CLI, MCP Server, Excel add-in, Jupyter
- **UI**: OpenBB Workspace (web), Desktop (Electron), CLI, Excel add-in
- **Indicators**: 30+ via `openbb-technical` extension (pandas-ta fork)
- **AI**: Copilot, MCP tools, Orchestrator mode, custom agent support
- **Deployment**: Local, Docker, Cloud, Enterprise (SOC 2 Type II)
- **License**: AGPL-3.0

### OpenStock (10.2k ⭐)

- **Data Sources**: Finnhub (primary), Adanos (sentiment, optional), TradingView (charts)
- **Data Types**: Stock quotes, company profiles, market news, technical indicators (via TV)
- **Storage**: MongoDB + Mongoose
- **API**: Next.js Server Actions + Finnhub REST
- **UI**: Next.js 15, React 19, shadcn/ui, Tailwind v4, dark mode default
- **AI**: Gemini-powered welcome emails, daily news summaries, sentiment via Adanos
- **Auth**: Better Auth (email/password), MongoDB adapter
- **Deployment**: Docker Compose, Vercel, local dev
- **License**: AGPL-3.0

### QuantDinger (1k ⭐)

- **Data Sources**: 10+ crypto exchanges, IBKR (US stocks), MT5 (forex), Yahoo Finance, Finnhub
- **Data Types**: Crypto, US stocks, forex, futures, prediction markets (Polymarket)
- **Storage**: PostgreSQL 16 + Redis
- **API**: REST API (Flask) on port 5000
- **UI**: Vue.js + Ant Design + ECharts + KlineCharts, Nginx SPA on port 8888
- **AI**: 7-Agent system (Technical/Fundamental/News/Sentiment/Risk → Bull/Bear debate → TraderAgent), 5+ LLM providers, vibe coding (NL → Python strategy)
- **Trading**: Live on 10+ exchanges, paper trading via virtual positions
- **Alerts**: Telegram, Discord, Email, SMS, Webhook
- **Deployment**: Docker Compose (one-click)
- **License**: Apache 2.0

### OpenAlice (3.1k ⭐)

- **Data Sources**: Multi-provider via OpenBB integration
- **Data Types**: Equity, crypto, commodity, currency, macro data
- **Storage**: JSON/JSONL files (no database, no containers)
- **API**: MCP Server, embedded HTTP API, SSE streaming
- **UI**: Hono + custom web UI, portfolio dashboard, equity curves
- **AI**: Multi-provider (Claude/Vercel AI SDK), cognitive brain (frontal lobe memory, emotion tracking), evolution mode (self-code modification)
- **Trading**: Live via CCXT (100+ crypto), Alpaca (US equities), IBKR; paper via mock broker
- **Deployment**: Local only (Node.js 22+), runs 24/7 on laptop
- **License**: AGPL-3.0

### yfinance (22.6k ⭐)

- **Data Types**: OHLCV, options, dividends, splits, fundamentals, earnings, insider/institutional holders, news, crypto, forex
- **Storage**: SQLite timezone cache (peewee), optional requests_cache
- **API Style**: Sync + WebSocket for real-time streaming
- **Unique**: Live WebSocket streaming, ISIN lookup, auto price repair, earnings/IPO calendar, option chains
- **License**: Apache 2.0

### yahooquery (900 ⭐)

- **Data Types**: OHLCV, fundamentals, options, earnings, crypto, forex, market summary, trending
- **Storage**: In-memory only
- **API Style**: Sync + Async (requests-futures)
- **Unique**: Async support, Yahoo Finance Premium via Selenium, formatted/unformatted data toggle
- **License**: MIT

### TradingView-Screener (851 ⭐)

- **Data Types**: OHLCV (multi-timeframe), 3000+ technical indicator fields, fundamentals
- **Storage**: In-memory only
- **API Style**: Sync, pandas integration
- **Unique**: 3000+ data fields, SQL-like filtering syntax, multi-timeframe queries, multiple markets (stocks/crypto/forex/CFDs/futures/bonds)
- **License**: MIT
