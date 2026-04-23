"""
U.S. Energy Information Administration (EIA) Open Data API v2 client.

Fetches daily/weekly oil and gasoline price series and returns normalized
oil_prices row dicts ready for insertion into TimescaleDB.

Free API key: https://www.eia.gov/opendata/register.php
Docs: https://www.eia.gov/opendata/documentation.php
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.eia.gov/v2/seriesid"

# EIA series to fetch, with their metadata
# (eia_series_id, series_id label, unit, frequency)
_SERIES: list[tuple[str, str, str, str]] = [
    ("PET.RBRTE.D", "BRENT_SPOT", "barrel", "daily"),
    ("PET.RWTC.D", "WTI_SPOT", "barrel", "daily"),
    ("PET.EMM_EPM0_PTE_NUS_DPG.W", "RETAIL_GASOLINE_US", "gallon", "weekly"),
]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _fetch_series(
    session: aiohttp.ClientSession,
    eia_series_id: str,
    api_key: str,
    start_date: date,
    end_date: date,
    frequency: str,
) -> list[dict[str, Any]]:
    """Fetch one EIA series and return raw data rows."""
    params: dict[str, str] = {
        "data[0]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "frequency": frequency,
        "length": "365",
    }
    if api_key:
        params["api_key"] = api_key

    url = f"{_BASE_URL}/{eia_series_id}"
    async with session.get(url, params=params) as resp:
        resp.raise_for_status()
        payload = await resp.json()

    return payload.get("response", {}).get("data", [])


def _parse_row(
    raw: dict[str, Any],
    series_id: str,
    unit: str,
) -> dict[str, Any] | None:
    """Convert one EIA data row into an oil_prices dict."""
    period = raw.get("period")
    value = raw.get("value")

    if period is None or value is None:
        return None

    try:
        price = float(value)
    except (ValueError, TypeError):
        return None

    # EIA periods are 'YYYY-MM-DD' for daily/weekly
    try:
        time = datetime.strptime(period, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        logger.warning("EIA: unexpected period format '%s', skipping", period)
        return None

    return {
        "time": time,
        "series_id": series_id,
        "source": "eia",
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
    Fetch EIA oil price series for the given date range.

    Args:
        api_key:    EIA API key (empty string is accepted; key improves rate limits).
        start_date: Inclusive start date (defaults to 365 days before end_date).
        end_date:   Inclusive end date (defaults to today).

    Returns:
        List of oil_prices row dicts with keys:
        time, series_id, source, price, currency, unit.
    """
    from datetime import timedelta

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=365)

    records: list[dict[str, Any]] = []

    async with aiohttp.ClientSession() as session:
        for eia_series_id, series_id, unit, frequency in _SERIES:
            try:
                raw_rows = await _fetch_series(
                    session, eia_series_id, api_key, start_date, end_date, frequency
                )
            except Exception:
                logger.exception("EIA: failed to fetch series '%s'", eia_series_id)
                continue

            for raw in raw_rows:
                row = _parse_row(raw, series_id, unit)
                if row is not None:
                    records.append(row)

            logger.info(
                "EIA: fetched %d records for %s (%s)",
                len(raw_rows), eia_series_id, series_id,
            )

    return records
