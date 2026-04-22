"""
Main AIS ingestion coordinator.

Selects the configured AIS source (aisstream | marinetraffic | spire),
batches incoming position records, and writes them to TimescaleDB.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from common.config import config
from common.db import close_pool, insert_vessel_positions

logger = logging.getLogger(__name__)

# Flush to DB when we've accumulated this many records, or after FLUSH_INTERVAL_SECONDS
BATCH_SIZE = 50
FLUSH_INTERVAL_SECONDS = 30.0


async def _run_aisstream() -> None:
    """Stream positions from aisstream.io and bulk-insert in batches."""
    from vessel_positions.aisstream import stream_positions

    api_key = config.aisstream_api_key
    if not api_key:
        raise RuntimeError("AISSTREAM_API_KEY is required for AIS_SOURCE=aisstream")

    batch: list[dict[str, Any]] = []
    last_flush = asyncio.get_event_loop().time()

    async for record in stream_positions(api_key):
        batch.append(record)

        now = asyncio.get_event_loop().time()
        if len(batch) >= BATCH_SIZE or (now - last_flush) >= FLUSH_INTERVAL_SECONDS:
            inserted = await insert_vessel_positions(batch)
            logger.info("Flushed %d records to vessel_positions (%d rows)", len(batch), inserted)
            batch.clear()
            last_flush = now


async def _run_marinetraffic() -> None:
    """Poll MarineTraffic API and insert each batch."""
    from vessel_positions.marinetraffic import poll_positions

    api_key = config.marinetraffic_api_key
    if not api_key:
        raise RuntimeError("MARINETRAFFIC_API_KEY is required for AIS_SOURCE=marinetraffic")

    async for batch in poll_positions(api_key):
        if batch:
            inserted = await insert_vessel_positions(batch)
            logger.info("Inserted %d MarineTraffic records (%d rows written)", len(batch), inserted)


async def run() -> None:
    """Entry point: start the configured AIS pipeline and run until cancelled."""
    source = config.ais_source
    logger.info("Starting AIS ingestion pipeline (source=%s)", source)

    try:
        if source == "aisstream":
            await _run_aisstream()
        elif source == "marinetraffic":
            await _run_marinetraffic()
        else:
            raise RuntimeError(f"Unknown AIS_SOURCE '{source}'. Choose: aisstream | marinetraffic")
    finally:
        await close_pool()
        logger.info("Database pool closed.")
