"""
aisstream.io WebSocket client for real-time AIS vessel positions.

Protocol: https://aisstream.io/documentation
Free API key available at https://aisstream.io/authenticate

The pipeline subscribes to a bounding box around the Strait of Hormuz and
receives PositionReport and ShipStaticData messages. It applies tanker-class
filtering and yields normalized position dicts ready for DB insertion.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import websockets
from websockets.exceptions import ConnectionClosed

from common.config import config
from vessel_positions.filters import classify_vessel, in_hormuz_bbox, is_target_vessel

logger = logging.getLogger(__name__)

AISSTREAM_WS_URL = "wss://stream.aisstream.io/v0/stream"

# In-memory cache of static vessel data (MMSI → metadata) to enrich position reports
_vessel_cache: dict[int, dict[str, Any]] = {}


def _build_subscription(api_key: str) -> dict[str, Any]:
    """Build the aisstream.io subscription message."""
    return {
        "APIKey": api_key,
        "BoundingBoxes": [
            [
                [config.hormuz_lat_min, config.hormuz_lon_min],
                [config.hormuz_lat_max, config.hormuz_lon_max],
            ]
        ],
        # Request both position reports and static vessel data
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }


def _parse_position_report(msg: dict[str, Any]) -> dict[str, Any] | None:
    """
    Parse a PositionReport message into a vessel_positions row dict.
    Returns None if the message is malformed or the vessel is not a tanker.
    """
    meta = msg.get("MetaData", {})
    pos = msg.get("Message", {}).get("PositionReport", {})

    mmsi = meta.get("MMSI")
    lat = pos.get("Latitude")
    lon = pos.get("Longitude")

    if mmsi is None or lat is None or lon is None:
        return None

    if not in_hormuz_bbox(lat, lon):
        return None

    # Enrich with cached static data (may not be present yet)
    static = _vessel_cache.get(mmsi, {})
    ais_ship_type = static.get("ais_ship_type")

    if not is_target_vessel(ais_ship_type):
        # We haven't received static data yet for this vessel — include it anyway
        # so we don't miss transits, and reclassify later when static data arrives.
        # If we have static data and it's not a tanker, skip.
        if ais_ship_type is not None:
            return None

    vessel_type = classify_vessel(
        ais_ship_type,
        vessel_name=static.get("vessel_name"),
        length_m=static.get("length_m"),
    )

    # Parse timestamp (aisstream provides UTC ISO 8601)
    time_utc_str = meta.get("time_utc", "")
    try:
        time_utc = datetime.fromisoformat(time_utc_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        time_utc = datetime.now(timezone.utc)

    return {
        "time": time_utc,
        "mmsi": mmsi,
        "vessel_name": static.get("vessel_name") or meta.get("ShipName"),
        "vessel_type": vessel_type or static.get("vessel_type") or "Unknown",
        "imo": static.get("imo"),
        "callsign": static.get("callsign"),
        "flag": None,  # Not provided by aisstream position reports
        "lat": lat,
        "lon": lon,
        "speed": pos.get("Sog"),          # Speed Over Ground (knots)
        "course": pos.get("Cog"),          # Course Over Ground (degrees)
        "heading": pos.get("TrueHeading"),
        "nav_status": pos.get("NavigationalStatus"),
        "destination": static.get("destination"),
        "draught": static.get("draught"),
        "ais_ship_type": ais_ship_type,
        "source": "aisstream",
    }


def _parse_ship_static(msg: dict[str, Any]) -> None:
    """
    Cache static vessel data from a ShipStaticData message.
    This enriches future PositionReport messages for the same MMSI.
    """
    meta = msg.get("MetaData", {})
    static_msg = msg.get("Message", {}).get("ShipStaticData", {})

    mmsi = meta.get("MMSI")
    if mmsi is None:
        return

    dimension = static_msg.get("Dimension", {})
    length_m: float | None = None
    if dimension:
        bow = dimension.get("A", 0) or 0
        stern = dimension.get("B", 0) or 0
        total = bow + stern
        if total > 0:
            length_m = float(total)

    _vessel_cache[mmsi] = {
        "vessel_name": static_msg.get("Name", "").strip() or None,
        "imo": static_msg.get("ImoNumber") or None,
        "callsign": static_msg.get("CallSign", "").strip() or None,
        "ais_ship_type": static_msg.get("Type"),
        "destination": static_msg.get("Destination", "").strip() or None,
        "draught": static_msg.get("MaximumStaticDraught"),
        "length_m": length_m,
        "vessel_type": None,  # Will be resolved at classification time
    }


async def stream_positions(api_key: str) -> AsyncGenerator[dict[str, Any], None]:
    """
    Async generator that yields normalized vessel position dicts.

    Connects to aisstream.io, handles reconnections with exponential back-off,
    and continuously yields position records for tankers in the Hormuz bbox.
    """
    backoff = 1.0
    subscription = _build_subscription(api_key)

    while True:
        try:
            logger.info("Connecting to aisstream.io WebSocket...")
            async with websockets.connect(
                AISSTREAM_WS_URL,
                ping_interval=30,
                ping_timeout=10,
                open_timeout=30,
            ) as ws:
                await ws.send(json.dumps(subscription))
                logger.info(
                    "Subscribed to Hormuz bbox (%.2fN-%.2fN, %.2fE-%.2fE)",
                    config.hormuz_lat_min, config.hormuz_lat_max,
                    config.hormuz_lon_min, config.hormuz_lon_max,
                )
                backoff = 1.0  # Reset on successful connect

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("Received non-JSON message, skipping")
                        continue

                    msg_type = msg.get("MessageType")

                    if msg_type == "ShipStaticData":
                        _parse_ship_static(msg)

                    elif msg_type == "PositionReport":
                        record = _parse_position_report(msg)
                        if record is not None:
                            yield record

        except ConnectionClosed as exc:
            logger.warning("WebSocket connection closed: %s", exc)
        except OSError as exc:
            logger.error("Network error: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error in WebSocket stream: %s", exc)

        logger.info("Reconnecting in %.1f seconds...", backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60.0)
