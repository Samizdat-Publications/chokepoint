"""
Federal Reserve Economic Data (FRED) API client.

Fetches oil and gasoline price series from the St. Louis Fed and returns
normalized oil_prices row dicts ready for insertion into TimescaleDB.

Free API key: https://fred.stlouisfed.org/docs/api/api_key.html
Docs: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# (fred_series_id, series_id label, unit)
_SERIES: list[tuple[str, str, str]] = [
    ("DCOILBRENTEU", "BRENT_SPOT", "barrel"),
    ("DCOILWTICO", "WTI_SPOT", "barrel"),
    ("GASREGCOVW", "RETAIL_GASOLINE_US", "gallon"),
]

# FRED uses "." to represent missing observations
_MISSING_VALUE = "."


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _fetch_series(
    session: aiohttp.ClientSession,
    fred_series_id: str,
    api_key: str,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    """Fetch one FRED series and return raw observation rows."""
    params = {
        "series_id": fred_series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "observation_start": start_date.isoformat(),
        "observation_end": end_date.isoformat(),
        "limit": "1000",
    }

    async with session.get(_BASE_URL, params=params) as resp:
        resp.raise_for_status()
        payload = await resp.json()

    return payload.get("observations", [])


def _parse_row(
    raw: dict[str, Any],
    series_id: str,
    unit: str,
) -> dict[str, Any] | None:
    """Convert one FRED observation into an oil_prices dict."""
    obs_date = raw.get("date")
    value = raw.get("value")

    if obs_date is None or value is None:
        return None

    # FRED uses "." for missing values — skip them
    if value == _MISSING_VALUE:
        return None

    try:
        price = float(value)
    except (ValueError, TypeError):
        return None

    try:
        time = datetime.strptime(obs_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        logger.warning("FRED: unexpected date format '%s', skipping", obs_date)
        return None

    return {
        "time": time,
        "series_id": series_id,
        "source": "fred",
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
    Fetch FRED oil price series for the given date range.

    Args:
        api_key:    FRED API key (required for production use).
        start_date: Inclusive start date (defaults to 365 days before end_date).
        end_date:   Inclusive end date (defaults to today).

    Returns:
        List of oil_prices row dicts with keys:
        time, series_id, source, price, currency, unit.
        Rows with missing FRED values ("." placeholder) are omitted.
    """
    from datetime import timedelta

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=365)

    records: list[dict[str, Any]] = []

    async with aiohttp.ClientSession() as session:
        for fred_series_id, series_id, unit in _SERIES:
            try:
                raw_rows = await _fetch_series(
                    session, fred_series_id, api_key, start_date, end_date
                )
            except Exception:
                logger.exception("FRED: failed to fetch series '%s'", fred_series_id)
                continue

            fetched = 0
            for raw in raw_rows:
                row = _parse_row(raw, series_id, unit)
                if row is not None:
                    records.append(row)
                    fetched += 1

            logger.info(
                "FRED: fetched %d records for %s (%s)",
                fetched, fred_series_id, series_id,
            )

    return records
