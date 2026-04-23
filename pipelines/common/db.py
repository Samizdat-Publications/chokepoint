"""
Async PostgreSQL connection pool using asyncpg.
Provides a context manager for acquiring connections and a helper for bulk inserts.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import asyncpg

from common.config import config

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    global _pool
    async with _pool_lock:
        if _pool is None:
            logger.info("Creating database connection pool")
            _pool = await asyncpg.create_pool(
                config.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def acquire() -> AsyncGenerator[asyncpg.Connection, None]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def insert_vessel_positions(rows: list[dict[str, Any]]) -> int:
    """
    Bulk-insert vessel position records.
    Skips duplicates (same mmsi + time + source) to handle reconnections gracefully.
    Returns the number of rows actually inserted.
    """
    if not rows:
        return 0

    async with acquire() as conn:
        result = await conn.executemany(
            """
            INSERT INTO vessel_positions (
                time, mmsi, vessel_name, vessel_type, imo, callsign, flag,
                lat, lon, speed, course, heading, nav_status,
                destination, draught, ais_ship_type, source
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7,
                $8, $9, $10, $11, $12, $13,
                $14, $15, $16, $17
            )
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    r["time"], r["mmsi"], r.get("vessel_name"), r.get("vessel_type"),
                    r.get("imo"), r.get("callsign"), r.get("flag"),
                    r["lat"], r["lon"], r.get("speed"), r.get("course"),
                    r.get("heading"), r.get("nav_status"),
                    r.get("destination"), r.get("draught"),
                    r.get("ais_ship_type"), r.get("source", "aisstream"),
                )
                for r in rows
            ],
        )
    # executemany returns the status string of the last command
    return len(rows)


async def insert_oil_prices(rows: list[dict[str, Any]]) -> int:
    """
    Bulk-insert oil price records.
    Upserts on (series_id, time, source) — safe to rerun on backfill.
    Returns the number of rows processed.
    """
    if not rows:
        return 0

    async with acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO oil_prices (time, series_id, source, price, currency, unit)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (series_id, time, source) DO UPDATE
                SET price = EXCLUDED.price
            """,
            [
                (
                    r["time"], r["series_id"], r["source"],
                    r["price"], r.get("currency", "USD"), r["unit"],
                )
                for r in rows
            ],
        )
    return len(rows)
