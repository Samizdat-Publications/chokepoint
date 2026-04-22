"""
MarineTraffic REST API polling client (commercial API key required).

MarineTraffic API v2 docs: https://www.marinetraffic.com/en/ais-api-services
This adapter polls the Expected Arrivals or Vessel Positions endpoint
every POLL_INTERVAL_SECONDS (default 15 min).

To activate: set AIS_SOURCE=marinetraffic and MARINETRAFFIC_API_KEY in .env
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import aiohttp

from common.config import config
from vessel_positions.filters import classify_vessel, in_hormuz_bbox, is_target_vessel

logger = logging.getLogger(__name__)

# MarineTraffic v2 base URL
_MT_BASE_URL = "https://services.marinetraffic.com/api"

# Vessel positions in area endpoint (PS07)
_POSITIONS_ENDPOINT = "getVesselsInArea/v:8"


def _parse_mt_vessel(vessel: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a MarineTraffic vessel object into a vessel_positions row."""
    try:
        lat = float(vessel.get("LAT", 0))
        lon = float(vessel.get("LON", 0))
    except (TypeError, ValueError):
        return None

    if not in_hormuz_bbox(lat, lon):
        return None

    ais_ship_type_raw = vessel.get("SHIPTYPE")
    try:
        ais_ship_type = int(ais_ship_type_raw) if ais_ship_type_raw else None
    except (TypeError, ValueError):
        ais_ship_type = None

    if not is_target_vessel(ais_ship_type):
        if ais_ship_type is not None:
            return None

    vessel_name = (vessel.get("SHIPNAME") or "").strip() or None

    try:
        length_m = float(vessel.get("LENGTH") or 0) or None
    except (TypeError, ValueError):
        length_m = None

    vessel_type = classify_vessel(ais_ship_type, vessel_name=vessel_name, length_m=length_m)

    timestamp_str = vessel.get("TIMESTAMP", "")
    try:
        time_utc = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        time_utc = datetime.now(timezone.utc)

    mmsi_raw = vessel.get("MMSI")
    try:
        mmsi = int(mmsi_raw)
    except (TypeError, ValueError):
        return None

    return {
        "time": time_utc,
        "mmsi": mmsi,
        "vessel_name": vessel_name,
        "vessel_type": vessel_type or "Tanker",
        "imo": vessel.get("IMO") or None,
        "callsign": vessel.get("CALLSIGN") or None,
        "flag": vessel.get("FLAG") or None,
        "lat": lat,
        "lon": lon,
        "speed": vessel.get("SPEED"),
        "course": vessel.get("COURSE"),
        "heading": vessel.get("HEADING"),
        "nav_status": vessel.get("STATUS"),
        "destination": vessel.get("DESTINATION") or None,
        "draught": vessel.get("DRAUGHT") or None,
        "ais_ship_type": ais_ship_type,
        "source": "marinetraffic",
    }


async def poll_positions(api_key: str) -> AsyncGenerator[list[dict[str, Any]], None]:
    """
    Async generator that polls MarineTraffic for vessel positions in the Hormuz bbox.
    Yields a list of position records on each poll cycle.
    """
    params = {
        "MINLAT": config.hormuz_lat_min,
        "MAXLAT": config.hormuz_lat_max,
        "MINLON": config.hormuz_lon_min,
        "MAXLON": config.hormuz_lon_max,
        "SHIPTYPE": "6",  # Tankers
        "protocol": "jsono",
    }
    url = f"{_MT_BASE_URL}/{_POSITIONS_ENDPOINT}/{api_key}"

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                logger.info("Polling MarineTraffic API...")
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)

                records = []
                for vessel in data if isinstance(data, list) else []:
                    record = _parse_mt_vessel(vessel)
                    if record:
                        records.append(record)

                logger.info("MarineTraffic: fetched %d tanker positions in Hormuz bbox", len(records))
                yield records

            except aiohttp.ClientError as exc:
                logger.error("MarineTraffic API error: %s", exc)
                yield []

            await asyncio.sleep(config.poll_interval_seconds)
