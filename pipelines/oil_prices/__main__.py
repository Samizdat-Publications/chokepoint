"""
Entry point: python -m oil_prices

Fetches oil and commodity prices from configured sources (EIA, FRED, Alpha Vantage)
and inserts them into the oil_prices TimescaleDB table.

Usage:
    # Fetch last 365 days from all configured sources
    EIA_API_KEY=xxx FRED_API_KEY=xxx DATABASE_URL=postgresql://... python -m oil_prices

    # Backfill a specific date range
    DATABASE_URL=postgresql://... python -m oil_prices --start 2020-01-01 --end 2026-04-22

    # Use only a specific source
    python -m oil_prices --source eia

    # Dry run — print records without writing to DB
    python -m oil_prices --dry-run

    # Combine flags
    python -m oil_prices --source fred --start 2024-01-01 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date

from common.config import config


def _setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch oil and commodity prices into TimescaleDB"
    )
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="Inclusive start date for backfill (default: 365 days ago)",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="Inclusive end date (default: today)",
    )
    parser.add_argument(
        "--source",
        choices=["eia", "fred", "alpha_vantage", "all"],
        default=None,
        help="Override PRICE_SOURCE env var",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print records without writing to the database",
    )
    return parser.parse_args()


async def _main() -> None:
    _setup_logging()
    args = _parse_args()

    # Allow --source flag to override the env var at runtime
    if args.source is not None:
        import os
        os.environ["PRICE_SOURCE"] = args.source
        # Re-create config singleton with the overridden value.
        # Config is frozen, so we monkey-patch via the module.
        import common.config as cfg_module
        cfg_module.config = cfg_module.Config()

    from oil_prices.ingester import run

    total = await run(
        start_date=args.start,
        end_date=args.end,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"Dry run complete. Would have inserted {total} records.")
    else:
        print(f"Done. Inserted {total} records.")


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nShutdown requested — exiting.")
        sys.exit(0)
