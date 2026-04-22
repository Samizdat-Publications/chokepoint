"""
Cron-mode scheduler for AIS polling sources (MarineTraffic / Spire).

For streaming sources (aisstream.io), the ingester runs continuously and
does not need this scheduler. Use this module when deploying on a cron
job or task scheduler that invokes the pipeline on a fixed interval.

Usage (run once and exit):
    python -m vessel_positions.scheduler

Deploy as a cron job every 15 minutes:
    */15 * * * * /path/to/.venv/bin/python -m vessel_positions.scheduler >> /var/log/chokepoint-ais.log 2>&1
"""
from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone

from common.config import config
from common.db import close_pool, insert_vessel_positions

logger = logging.getLogger(__name__)


async def run_once() -> None:
    """
    Execute a single poll cycle for the configured AIS source and write results to DB.
    Designed to be invoked by an external cron scheduler every 15 minutes.
    """
    source = config.ais_source
    logger.info("Cron run started at %s (source=%s)", datetime.now(timezone.utc).isoformat(), source)

    try:
        if source == "marinetraffic":
            from vessel_positions.marinetraffic import poll_positions

            api_key = config.marinetraffic_api_key
            if not api_key:
                raise RuntimeError("MARINETRAFFIC_API_KEY is required")

            # poll_positions is an async generator; take the first (and only) batch
            async for batch in poll_positions(api_key):
                if batch:
                    inserted = await insert_vessel_positions(batch)
                    logger.info("Inserted %d records (source=marinetraffic)", inserted)
                break  # One poll, then exit

        elif source == "aisstream":
            logger.warning(
                "aisstream is a streaming source — run 'python -m vessel_positions' instead of the scheduler."
            )
            sys.exit(1)

        else:
            raise RuntimeError(f"Unknown AIS_SOURCE '{source}'")

    finally:
        await close_pool()
        logger.info("Cron run complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        stream=sys.stdout,
    )
    asyncio.run(run_once())
