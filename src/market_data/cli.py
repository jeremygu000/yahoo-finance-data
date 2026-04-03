from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

from market_data.config import DEFAULT_TICKERS, LOOKBACK_DAYS, MIN_ROLLING_DAYS
from market_data.fetcher import fetch_batch
from market_data.logging_config import setup_logging
from market_data.store import clean, last_date, save, status

logger = logging.getLogger(__name__)


def cmd_fetch(args: argparse.Namespace) -> None:
    tickers = args.tickers.split(",") if args.tickers else DEFAULT_TICKERS
    tickers = [t.strip() for t in tickers]

    print(f"Fetching {len(tickers)} tickers: {', '.join(tickers)}")

    rolling_start = date.today() - timedelta(days=MIN_ROLLING_DAYS)

    if args.full:
        start = date.today() - timedelta(days=LOOKBACK_DAYS)
        print(f"Full fetch from {start}")
        data = fetch_batch(tickers, start=start)
    else:
        starts: dict[str, date] = {}
        for ticker in tickers:
            ld = last_date(ticker)
            if ld is None:
                starts[ticker] = date.today() - timedelta(days=LOOKBACK_DAYS)
            else:
                starts[ticker] = min(ld, rolling_start)

        earliest = min(starts.values())
        print(f"Incremental fetch from {earliest} (rolling {MIN_ROLLING_DAYS}d)")
        data = fetch_batch(tickers, start=earliest)

    if not data:
        print("No data returned from Yahoo Finance")
        sys.exit(1)

    total_new = 0
    for ticker, df in data.items():
        new_rows = save(ticker, df)
        total_new += new_rows
        print(f"  {ticker}: +{new_rows} rows")

    missing = set(tickers) - set(data.keys())
    if missing:
        print(f"Missing: {', '.join(sorted(missing))}")

    print(f"Done. {total_new} new rows added.")


def cmd_status(_args: argparse.Namespace) -> None:
    entries = status()
    if not entries:
        print("No cached data. Run 'market-data fetch' first.")
        return

    print(f"{'Ticker':<10} {'Rows':>6} {'First':>12} {'Last':>12} {'Size':>8}")
    print("-" * 52)

    for entry in entries:
        print(
            f"{entry['ticker']:<10} "
            f"{entry['rows']:>6} "
            f"{entry['first_date']:>12} "
            f"{entry['last_date']:>12} "
            f"{entry['size_kb']:>6.1f} KB"
        )


def cmd_clean(args: argparse.Namespace) -> None:
    removed = clean(keep_days=args.keep_days)
    if not removed:
        print(f"Nothing to clean (all data within {args.keep_days} days).")
        return

    for ticker, count in removed.items():
        print(f"  {ticker}: removed {count} rows")
    print(f"Total: {sum(removed.values())} rows removed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="market-data",
        description="Shared Yahoo Finance market data provider",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    sub = parser.add_subparsers(dest="command")

    p_fetch = sub.add_parser("fetch", help="Fetch market data from Yahoo Finance")
    p_fetch.add_argument("--tickers", type=str, help="Comma-separated ticker list")
    p_fetch.add_argument("--full", action="store_true", help="Full historical fetch (ignore cache)")

    sub.add_parser("status", help="Show cached data status")

    p_clean = sub.add_parser("clean", help="Remove old data")
    p_clean.add_argument("--keep-days", type=int, default=365, help="Keep data within N days")

    args = parser.parse_args()
    setup_logging(json_format=False, level=logging.DEBUG if args.verbose else logging.INFO)

    commands = {
        "fetch": cmd_fetch,
        "status": cmd_status,
        "clean": cmd_clean,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)
