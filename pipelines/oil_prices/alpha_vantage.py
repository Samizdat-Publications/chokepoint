"""
Alpha Vantage commodity price API client.

Fetches Brent crude, WTI crude, and Henry Hub natural gas prices and returns
normalized oil_prices row dicts ready for insertion into TimescaleDB.

Free API key (25 req/day): https://www.alphavantage.co/support/#api-key
Docs: https://www.alphavantage.co/documentation/#energy

Rate limits (free tier): 25 requests/day, 5 requests/minute.
This module inserts a short sleep between requests to avoid hitting the per-minute limit.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.alphavantage.co/query"

# Seconds to pause between API calls to respect the 5 req/min free-tier limit.
_REQUEST_DELAY_SECONDS = 1.2

# (av_function, series_id label, unit)
_SERIES: list[tuple[str, str, str]] = [
    ("BRENT", "BRENT_SPOT", "barrel"),
    ("WTI", "WTI_SPOT", "barrel"),
    ("NATURAL_GAS", "NATURAL_GAS_HH", "mmbtu"),
]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    reraise=True,
)
async def _fetch_series(
    session: aiohttp.ClientSession,
    function: str,
    api_key: str,
) -> list[dict[str, Any]]:
    """Fetch one Alpha Vantage commodity series and return raw data rows."""
    params = {
        "function": function,
        "interval": "daily",
        "apikey": api_key,
    }

    async with session.get(_BASE_URL, params=params) as resp:
        resp.raise_for_status()
        payload = await resp.json()

    # Alpha Vantage surfaces API errors in JSON body, not HTTP status
    if "Information" in payload:
        raise RuntimeError(f"Alpha Vantage rate limit or auth error: {payload['Information']}")
    if "Note" in payload:
        raise RuntimeError(f"Alpha Vantage API note (rate limit): {payload['Note']}")

    return payload.get("data", [])


def _parse_row(
    raw: dict[str, Any],
    series_id: str,
    unit: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any] | None:
    """Convert one Alpha Vantage data point into an oil_prices dict."""
    obs_date = raw.get("date")
    value = raw.get("value")

    if obs_date is None or value is None:
        return None

    try:
        price = float(value)
    except (ValueError, TypeError):
        return None

    try:
        time = datetime.strptime(obs_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        logger.warning("Alpha Vantage: unexpected date format '%s', skipping", obs_date)
        return None

    # Filter to requested date range (AV returns full history)
    if not (start_date <= time.date() <= end_date):
        return None

    return {
        "time": time,
        "series_id": series_id,
        "source": "alpha_vantage",
        "price": price,
        "currency": "USD",
        "unit": unit,
    }


async def fetch_prices(
    api_key: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch Alpha Vantage commodity price series for the given date range.

    Note: Alpha Vantage always returns full history regardless of date params.
    Date filtering is applied client-side.

    Args:
        api_key:    Alpha Vantage API key (required).
        start_date: Inclusive start date (defaults to 365 days before end_date).
        end_date:   Inclusive end date (defaults to today).

    Returns:
        List of oil_prices row dicts with keys:
        time, series_id, source, price, currency, unit.
    """
    from datetime import timedelta

    if not api_key:
        logger.warning("Alpha Vantage: ALPHA_VANTAGE_API_KEY not set, skipping")
        return []

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=365)

    records: list[dict[str, Any]] = []

    async with aiohttp.ClientSession() as session:
        for i, (function, series_id, unit) in enumerate(_SERIES):
            # Throttle requests to avoid the 5/min free-tier rate limit
            if i > 0:
                await asyncio.sleep(_REQUEST_DELAY_SECONDS)

            try:
                raw_rows = await _fetch_series(session, function, api_key)
            except Exception:
                logger.exception("Alpha Vantage: failed to fetch function '%s'", function)
                continue

            fetched = 0
            for raw in raw_rows:
                row = _parse_row(raw, series_id, unit, start_date, end_date)
                if row is not None:
                    records.append(row)
                    fetched += 1

            logger.info(
                "Alpha Vantage: fetched %d records for %s (%s)",
                fetched, function, series_id,
            )

    return records
