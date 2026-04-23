"""
Oil and commodity price ingestion coordinator.

Fetches from configured sources (eia | fred | alpha_vantage | all),
deduplicates by (series_id, time, source), and bulk-inserts into TimescaleDB.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from common.config import config
from common.db import close_pool, insert_oil_prices

logger = logging.getLogger(__name__)


async def _fetch_from_source(
    source: str,
    start_date: date | None,
    end_date: date | None,
) -> list[dict[str, Any]]:
    """Fetch price records from a single named source."""
    if source == "eia":
        from oil_prices.eia import fetch_prices
        return await fetch_prices(config.eia_api_key, start_date, end_date)

    if source == "fred":
        from oil_prices.fred import fetch_prices
        if not config.fred_api_key:
            logger.warning("FRED_API_KEY not set — skipping FRED source")
            return []
        return await fetch_prices(config.fred_api_key, start_date, end_date)

    if source == "alpha_vantage":
        from oil_prices.alpha_vantage import fetch_prices
        return await fetch_prices(config.alpha_vantage_api_key, start_date, end_date)

    raise ValueError(f"Unknown price source '{source}'. Choose: eia | fred | alpha_vantage | all")


async def run(
    start_date: date | None = None,
    end_date: date | None = None,
    dry_run: bool = False,
) -> int:
    """
    Fetch oil prices from all configured sources and write to the oil_prices table.

    Sources are controlled by the PRICE_SOURCE env var (default: 'all').
    In dry-run mode, records are logged but not written to the database.

    Returns the total number of records inserted (or would-be-inserted in dry-run).
    """
    source = config.price_source
    sources = ["eia", "fred", "alpha_vantage"] if source == "all" else [source]

    logger.info(
        "Starting oil price ingestion (sources=%s, start=%s, end=%s, dry_run=%s)",
        sources, start_date, end_date, dry_run,
    )

    all_records: list[dict[str, Any]] = []

    for src in sources:
        try:
            records = await _fetch_from_source(src, start_date, end_date)
            all_records.extend(records)
            logger.info("Source '%s' returned %d records", src, len(records))
        except Exception:
            logger.exception("Failed to fetch from source '%s', continuing", src)

    logger.info("Total records fetched: %d", len(all_records))

    if dry_run:
        for rec in all_records:
            logger.info(
                "DRY RUN: %s | %s | %s | %.4f %s/%s",
                rec["time"].date(), rec["series_id"], rec["source"],
                rec["price"], rec["currency"], rec["unit"],
            )
        return len(all_records)

    try:
        inserted = await insert_oil_prices(all_records)
        logger.info("Inserted %d oil price records into TimescaleDB", inserted)
        return inserted
    finally:
        await close_pool()
