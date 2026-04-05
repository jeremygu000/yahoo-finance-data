from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

from market_data.config import LOOKBACK_DAYS, MIN_ROLLING_DAYS, VALID_INTERVALS, get_tickers
from market_data.fetcher import fetch_batch
from market_data.fundamentals_store import fetch_all_fundamental_data
from market_data.logging_config import setup_logging
from market_data.store import clean, last_date, save, status
from market_data.watchlist import add_ticker, list_tickers, remove_ticker
from market_data import alerts as alerts_mod
from market_data import portfolio as portfolio_mod
from market_data import quality as quality_mod

logger = logging.getLogger(__name__)


def _filter_stale(tickers: list[str]) -> tuple[list[str], list[str]]:
    today = date.today()
    stale: list[str] = []
    fresh: list[str] = []
    for t in tickers:
        ld = last_date(t)
        if ld is None or (today - ld).days > 1:
            stale.append(t)
        else:
            fresh.append(t)
    return stale, fresh


def _fetch_fundamentals_for(tickers: list[str]) -> None:
    print(f"\nFetching fundamentals for {len(tickers)} tickers...")
    for i, ticker in enumerate(tickers, 1):
        result = fetch_all_fundamental_data(ticker)
        parts = []
        if result.get("fundamentals"):
            parts.append("info")
        if result.get("recommendations"):
            parts.append(f"recs={result['recommendations']}")
        if result.get("earnings_dates"):
            parts.append(f"earnings={result['earnings_dates']}")
        if result.get("upgrades_downgrades"):
            parts.append(f"upgrades={result['upgrades_downgrades']}")
        summary = ", ".join(parts) if parts else "no data"
        print(f"  [{i}/{len(tickers)}] {ticker}: {summary}")
    print("Fundamentals fetch complete.")


def cmd_fetch(args: argparse.Namespace) -> None:
    tickers = args.tickers.split(",") if args.tickers else get_tickers()
    tickers = [t.strip() for t in tickers]

    if args.full:
        start = date.today() - timedelta(days=LOOKBACK_DAYS)
        print(f"Full fetch: {len(tickers)} tickers from {start}")
        data = fetch_batch(tickers, start=start)
    else:
        stale, fresh = _filter_stale(tickers)
        if fresh:
            print(f"Skipping {len(fresh)} up-to-date tickers")
        if not stale:
            print("All tickers are up-to-date. Nothing to fetch.")
            if not args.skip_fundamentals:
                _fetch_fundamentals_for(tickers)
            return

        tickers = stale
        rolling_start = date.today() - timedelta(days=MIN_ROLLING_DAYS)

        starts: dict[str, date] = {}
        for ticker in tickers:
            ld = last_date(ticker)
            if ld is None:
                starts[ticker] = date.today() - timedelta(days=LOOKBACK_DAYS)
            else:
                starts[ticker] = min(ld, rolling_start)

        earliest = min(starts.values())
        print(f"Fetching {len(tickers)} stale tickers from {earliest}")
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

    if not args.skip_fundamentals:
        all_tickers = args.tickers.split(",") if args.tickers else get_tickers()
        all_tickers = [t.strip() for t in all_tickers]
        _fetch_fundamentals_for(all_tickers)


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


def cmd_fetch_fundamentals(args: argparse.Namespace) -> None:
    tickers = args.tickers.split(",") if args.tickers else get_tickers()
    tickers = [t.strip() for t in tickers]
    _fetch_fundamentals_for(tickers)


def cmd_backfill(args: argparse.Namespace) -> None:
    tickers = [t.strip() for t in args.ticker.split(",") if t.strip()]
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else date.today()
    interval: str = args.interval

    if interval not in VALID_INTERVALS:
        print(f"Error: invalid interval '{interval}'. Must be one of: {', '.join(VALID_INTERVALS)}")
        sys.exit(1)

    print(f"Fetching {len(tickers)} tickers from {start} to {end} (interval={interval})")

    data = fetch_batch(tickers, start=start, end=end, interval=interval)

    if not data:
        print("No data returned")
        sys.exit(1)

    total_new = 0
    for ticker, df in data.items():
        new_rows = save(ticker, df, interval=interval)
        total_new += new_rows
        print(f"  {ticker}: +{new_rows} rows")

    missing = set(tickers) - set(data.keys())
    if missing:
        print(f"Missing: {', '.join(sorted(missing))}")

    print(f"Done. {total_new} new rows added.")


def cmd_watchlist(_args: argparse.Namespace) -> None:
    tickers = list_tickers()
    if not tickers:
        print("Watchlist is empty.")
    else:
        for t in tickers:
            print(t)


def cmd_watchlist_add(args: argparse.Namespace) -> None:
    wl = add_ticker(args.ticker)
    print(f"Added {args.ticker.upper()}. Watchlist: {wl.tickers}")


def cmd_watchlist_remove(args: argparse.Namespace) -> None:
    wl = remove_ticker(args.ticker)
    print(f"Removed {args.ticker.upper()}. Watchlist: {wl.tickers}")


def cmd_alerts(_args: argparse.Namespace) -> None:
    items = alerts_mod.list_alerts()
    if not items:
        print("No alerts configured.")
    else:
        for a in items:
            status_str = "enabled" if a.enabled else "disabled"
            print(
                f"[{a.id}] {a.ticker} {a.condition.value} {a.threshold} ({status_str}, cooldown={a.cooldown_seconds}s)"
            )


def cmd_alert_add(args: argparse.Namespace) -> None:
    alert = alerts_mod.Alert(
        ticker=args.ticker,
        condition=alerts_mod.AlertCondition(args.condition),
        threshold=args.threshold,
        cooldown_seconds=args.cooldown,
    )
    alerts_mod.add_alert(alert)
    print(f"Alert added: [{alert.id}] {alert.ticker} {alert.condition.value} {alert.threshold}")


def cmd_alert_remove(args: argparse.Namespace) -> None:
    alerts_mod.remove_alert(args.id)
    print(f"Alert {args.id} removed.")


def cmd_portfolio_list(_args: argparse.Namespace) -> None:
    holdings = portfolio_mod.list_holdings()
    if not holdings:
        print("Portfolio is empty.")
    else:
        print(f"{'Ticker':<10} {'Shares':>10} {'Avg Cost':>12} {'Added At':>30}")
        print("-" * 66)
        for h in holdings:
            print(f"{h.ticker:<10} {h.shares:>10.4f} {h.avg_cost:>12.4f} {h.added_at:>30}")


def cmd_portfolio_add(args: argparse.Namespace) -> None:
    p = portfolio_mod.add_holding(args.ticker, args.shares, args.cost)
    tickers = [h.ticker for h in p.holdings]
    print(f"Added {args.ticker.upper()}. Portfolio: {tickers}")


def cmd_portfolio_remove(args: argparse.Namespace) -> None:
    p = portfolio_mod.remove_holding(args.ticker)
    tickers = [h.ticker for h in p.holdings]
    print(f"Removed {args.ticker.upper()}. Portfolio: {tickers}")


def cmd_quality(args: argparse.Namespace) -> None:
    stale_days: int = args.stale_days
    zscore: float = args.zscore

    if args.gaps:
        tickers = [t.strip() for t in args.gaps.split(",")]
        for t in tickers:
            gaps = quality_mod.detect_gaps(t, interval=args.interval)
            if gaps:
                print(f"{t}: {len(gaps)} missing trading days")
                for g in gaps[:20]:
                    print(f"  {g}")
                if len(gaps) > 20:
                    print(f"  ... and {len(gaps) - 20} more")
            else:
                print(f"{t}: no gaps detected")
        return

    if args.outliers:
        tickers = [t.strip() for t in args.outliers.split(",")]
        for t in tickers:
            hits = quality_mod.detect_outliers(t, interval=args.interval, threshold=zscore)
            if hits:
                print(f"{t}: {len(hits)} outliers (|z| > {zscore})")
                for h in hits:
                    print(f"  {h['date']}  close={h['close']}  return={h['return_pct']}%  z={h['zscore']}")
            else:
                print(f"{t}: no outliers")
        return

    report = quality_mod.generate_report(stale_days=stale_days, zscore_threshold=zscore)
    print(f"Data Quality Report — {report.scan_date}")
    print(f"Files: {report.total_files}  Rows: {report.total_rows:,}")
    print()

    if report.anomalies:
        print(f"Anomalies: {len(report.anomalies)}")
        by_type: dict[str, int] = {}
        for a in report.anomalies:
            by_type[a.issue] = by_type.get(a.issue, 0) + a.count
        for issue, count in sorted(by_type.items()):
            print(f"  {issue}: {count:,} rows")
        print()

    stale = [t for t in report.tickers if t.days_stale > stale_days]
    if stale:
        print(f"Stale tickers (>{stale_days} days): {len(stale)}")
        for t in stale[:20]:
            print(f"  {t.ticker}: last={t.last_date} ({t.days_stale}d stale)")
        if len(stale) > 20:
            print(f"  ... and {len(stale) - 20} more")
        print()

    low_fill = [t for t in report.tickers if t.completeness_pct < 99.0]
    if low_fill:
        print(f"Low completeness (<99%): {len(low_fill)}")
        for t in sorted(low_fill, key=lambda x: x.completeness_pct):
            print(f"  {t.ticker}: {t.completeness_pct}% fill, {t.nan_pct}% NaN")
        print()

    if not report.anomalies and not stale and not low_fill:
        print("All checks passed.")


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
    p_fetch.add_argument("--skip-fundamentals", action="store_true", help="Skip fundamental data fetch")

    p_fetch_fund = sub.add_parser("fetch-fundamentals", help="Fetch fundamental data for tickers")
    p_fetch_fund.add_argument("--tickers", type=str, help="Comma-separated ticker list (default: watchlist)")

    sub.add_parser("status", help="Show cached data status")

    p_clean = sub.add_parser("clean", help="Remove old data")
    p_clean.add_argument("--keep-days", type=int, default=365, help="Keep data within N days")

    p_backfill = sub.add_parser("backfill", help="Backfill historical data for specified tickers")
    p_backfill.add_argument("--ticker", type=str, required=True, help="Comma-separated ticker list (e.g. AAPL,MSFT)")
    p_backfill.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    p_backfill.add_argument("--end", type=str, default=None, help="End date (YYYY-MM-DD, default today)")
    p_backfill.add_argument(
        "--interval",
        type=str,
        default="1d",
        choices=VALID_INTERVALS,
        help=f"Data interval (default: 1d, choices: {', '.join(VALID_INTERVALS)})",
    )

    sub.add_parser("watchlist", help="Show current watchlist")

    p_wl_add = sub.add_parser("watchlist-add", help="Add ticker to watchlist")
    p_wl_add.add_argument("--ticker", type=str, required=True, help="Ticker to add")

    p_wl_remove = sub.add_parser("watchlist-remove", help="Remove ticker from watchlist")
    p_wl_remove.add_argument("--ticker", type=str, required=True, help="Ticker to remove")

    sub.add_parser("alerts", help="List all configured alerts")

    p_alert_add = sub.add_parser("alert-add", help="Add a price alert")
    p_alert_add.add_argument("--ticker", type=str, required=True, help="Ticker symbol")
    p_alert_add.add_argument(
        "--condition",
        type=str,
        required=True,
        choices=[c.value for c in alerts_mod.AlertCondition],
        help="Alert condition",
    )
    p_alert_add.add_argument("--threshold", type=float, required=True, help="Threshold value")
    p_alert_add.add_argument("--cooldown", type=int, default=300, help="Cooldown in seconds (default 300)")

    p_alert_remove = sub.add_parser("alert-remove", help="Remove an alert by ID")
    p_alert_remove.add_argument("--id", type=str, required=True, help="Alert UUID to remove")

    p_quality = sub.add_parser("quality", help="Run data quality checks")
    p_quality.add_argument(
        "--stale-days", type=int, default=3, help="Days before a ticker is considered stale (default 3)"
    )
    p_quality.add_argument(
        "--zscore", type=float, default=4.0, help="Z-score threshold for outlier detection (default 4.0)"
    )
    p_quality.add_argument("--gaps", type=str, default="", help="Comma-separated tickers to check for trading day gaps")
    p_quality.add_argument(
        "--outliers", type=str, default="", help="Comma-separated tickers to check for price outliers"
    )
    p_quality.add_argument(
        "--interval",
        type=str,
        default="1d",
        choices=VALID_INTERVALS,
        help="Data interval for gap/outlier checks (default 1d)",
    )

    sub.add_parser("portfolio", help="List portfolio holdings")

    p_portfolio_add = sub.add_parser("portfolio-add", help="Add a holding to the portfolio")
    p_portfolio_add.add_argument("ticker", type=str, help="Ticker symbol (e.g. AAPL)")
    p_portfolio_add.add_argument("--shares", type=float, required=True, help="Number of shares")
    p_portfolio_add.add_argument("--cost", type=float, required=True, help="Average cost per share")

    p_portfolio_remove = sub.add_parser("portfolio-remove", help="Remove a holding from the portfolio")
    p_portfolio_remove.add_argument("ticker", type=str, help="Ticker symbol to remove")

    args = parser.parse_args()
    setup_logging(json_format=False, level=logging.DEBUG if args.verbose else logging.INFO)

    commands = {
        "fetch": cmd_fetch,
        "fetch-fundamentals": cmd_fetch_fundamentals,
        "status": cmd_status,
        "clean": cmd_clean,
        "backfill": cmd_backfill,
        "watchlist": cmd_watchlist,
        "watchlist-add": cmd_watchlist_add,
        "watchlist-remove": cmd_watchlist_remove,
        "alerts": cmd_alerts,
        "alert-add": cmd_alert_add,
        "alert-remove": cmd_alert_remove,
        "quality": cmd_quality,
        "portfolio": cmd_portfolio_list,
        "portfolio-add": cmd_portfolio_add,
        "portfolio-remove": cmd_portfolio_remove,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)
