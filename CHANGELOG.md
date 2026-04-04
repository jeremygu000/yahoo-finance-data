# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-04

### Added

**Data Fetching & Storage**
- Multi-source data fetching (Yahoo Finance, Tiingo, FMP) with automatic fallback chain
- Parquet file storage for efficient data access
- Historical backfill CLI command (`market-data backfill`)
- In-memory LRU cache with configurable TTL

**Market Data**
- Multi-timeframe support (1m, 5m, 15m, 1h, 1d intervals)
- Technical indicators API (SMA, EMA, RSI, MACD, Bollinger Bands)
- CSV export endpoint (`/api/v1/export/{ticker}`)

**Real-time Features**
- Real-time WebSocket price updates with live dashboard
- Price alerts with above/below/percent-change triggers and WebSocket notifications

**User Features**
- Persistent user watchlist (JSON storage, CRUD API + CLI)
- Portfolio tracking with holdings CRUD and P&L summary

**API & Backend**
- FastAPI REST API with Swagger UI documentation
- Optional API key authentication (`MARKET_DATA_API_KEY`)
- Exponential backoff with jitter for failed provider requests

**Frontend**
- Interactive Next.js dashboard with candlestick charts, price comparison, VIX dashboard

**CLI**
- CLI tools for data management (`fetch`, `status`, `clean`, `backfill`, `watchlist`, `alerts`, `portfolio`)

**DevOps & Testing**
- Docker and docker-compose support
- GitHub Actions CI (Python 3.12/3.13 matrix, mypy strict, black, frontend build)
- macOS launchd scheduler for automated daily fetches
- 200+ tests with mypy strict type checking

---

**Project**: Market Terminal (jeremygu000/yahoo-finance-data)  
**License**: MIT © Jeremy Gu
