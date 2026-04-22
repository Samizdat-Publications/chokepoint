"""
Daily transit count metrics for the Strait of Hormuz.

Provides two approaches:
1. TimescaleDB continuous aggregate (preferred in production) — defined in 002_vessel_positions.sql
2. On-demand query for a specific date range (useful for backfill and analytics)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from common.db import acquire

logger = logging.getLogger(__name__)


async def get_daily_transits(
    start_date: date | None = None,
    end_date: date | None = None,
    vessel_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Query daily transit counts directly from vessel_positions.

    Falls back to raw aggregation if the continuous aggregate
    (daily_hormuz_transits) is not yet populated.

    Args:
        start_date: Inclusive lower bound (defaults to 30 days ago)
        end_date:   Inclusive upper bound (defaults to today)
        vessel_type: Filter to a specific class (e.g. 'VLCC', 'Suezmax')

    Returns:
        List of dicts with keys: day, vessel_type, vessel_count, position_count, avg_speed_knots
    """
    from common.config import config

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    where_clauses = [
        "time >= $1",
        "time < $2",
        f"lat BETWEEN {config.hormuz_lat_min} AND {config.hormuz_lat_max}",
        f"lon BETWEEN {config.hormuz_lon_min} AND {config.hormuz_lon_max}",
    ]
    params: list[Any] = [
        start_date.isoformat(),
        (end_date + timedelta(days=1)).isoformat(),
    ]

    if vessel_type:
        where_clauses.append(f"vessel_type = ${len(params) + 1}")
        params.append(vessel_type)
    else:
        where_clauses.append("vessel_type IN ('VLCC', 'Suezmax', 'Tanker')")

    sql = f"""
        SELECT
            time_bucket('1 day', time)     AS day,
            vessel_type,
            COUNT(DISTINCT mmsi)            AS vessel_count,
            COUNT(*)                        AS position_count,
            ROUND(AVG(speed)::numeric, 2)   AS avg_speed_knots
        FROM vessel_positions
        WHERE {' AND '.join(where_clauses)}
        GROUP BY day, vessel_type
        ORDER BY day DESC, vessel_type
    """

    async with acquire() as conn:
        rows = await conn.fetch(sql, *params)

    return [dict(r) for r in rows]


async def get_transit_summary(days: int = 7) -> dict[str, Any]:
    """
    Return a summary dict suitable for the API layer / dashboard widget.

    Includes total transit count, breakdown by vessel class, and trend
    vs. prior period.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    prior_start = start_date - timedelta(days=days)

    current = await get_daily_transits(start_date, end_date)
    prior = await get_daily_transits(prior_start, start_date)

    def _total_vessels(rows: list[dict[str, Any]]) -> int:
        # Sum unique vessel-days (distinct mmsi per day is already aggregated)
        return sum(r["vessel_count"] for r in rows)

    current_total = _total_vessels(current)
    prior_total = _total_vessels(prior)

    trend_pct: float | None = None
    if prior_total > 0:
        trend_pct = round((current_total - prior_total) / prior_total * 100, 1)

    breakdown: dict[str, int] = {}
    for row in current:
        vt = row["vessel_type"] or "Unknown"
        breakdown[vt] = breakdown.get(vt, 0) + row["vessel_count"]

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_vessel_transits": current_total,
        "prior_period_transits": prior_total,
        "trend_percent": trend_pct,
        "by_vessel_type": breakdown,
        "daily": current,
    }
