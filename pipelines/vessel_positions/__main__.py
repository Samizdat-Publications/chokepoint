"""
Entry point: python -m vessel_positions

Usage:
    # Stream AIS positions (aisstream.io default)
    AISSTREAM_API_KEY=xxx DATABASE_URL=postgresql://... python -m vessel_positions

    # Use MarineTraffic polling
    AIS_SOURCE=marinetraffic MARINETRAFFIC_API_KEY=xxx DATABASE_URL=postgresql://... python -m vessel_positions

    # Print last 7-day transit summary and exit
    DATABASE_URL=postgresql://... python -m vessel_positions --metrics
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys

from common.config import config


def _setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


async def _print_metrics() -> None:
    from vessel_positions.metrics import get_transit_summary
    summary = await get_transit_summary(days=7)
    print(json.dumps(summary, indent=2, default=str))


async def _main() -> None:
    _setup_logging()

    if "--metrics" in sys.argv:
        await _print_metrics()
        return

    from vessel_positions.ingester import run
    await run()


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nShutdown requested — exiting.")
        sys.exit(0)
