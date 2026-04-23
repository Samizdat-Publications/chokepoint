"""Unit tests for oil price pipeline parsing logic.

Tests call internal _parse_row() functions directly — no HTTP calls made.
All tests are synchronous (no DB or network required).
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("EIA_API_KEY", "test-key")
os.environ.setdefault("FRED_API_KEY", "test-key")
os.environ.setdefault("ALPHA_VANTAGE_API_KEY", "test-key")

from oil_prices import eia, fred, alpha_vantage  # noqa: E402


# ---------------------------------------------------------------------------
# EIA parsing tests
# ---------------------------------------------------------------------------

class TestEIAParseRow:
    def test_valid_brent_row(self):
        raw = {"period": "2026-04-21", "value": "87.45"}
        result = eia._parse_row(raw, "BRENT_SPOT", "barrel")
        assert result is not None
        assert result["series_id"] == "BRENT_SPOT"
        assert result["source"] == "eia"
        assert result["price"] == 87.45
        assert result["currency"] == "USD"
        assert result["unit"] == "barrel"
        assert result["time"] == datetime(2026, 4, 21, tzinfo=timezone.utc)

    def test_valid_gasoline_row(self):
        raw = {"period": "2026-04-14", "value": "3.259"}
        result = eia._parse_row(raw, "RETAIL_GASOLINE_US", "gallon")
        assert result is not None
        assert result["unit"] == "gallon"
        assert abs(result["price"] - 3.259) < 1e-6

    def test_missing_period_returns_none(self):
        raw = {"value": "87.45"}
        assert eia._parse_row(raw, "BRENT_SPOT", "barrel") is None

    def test_missing_value_returns_none(self):
        raw = {"period": "2026-04-21"}
        assert eia._parse_row(raw, "BRENT_SPOT", "barrel") is None

    def test_non_numeric_value_returns_none(self):
        raw = {"period": "2026-04-21", "value": "N/A"}
        assert eia._parse_row(raw, "BRENT_SPOT", "barrel") is None

    def test_timestamp_is_utc(self):
        raw = {"period": "2026-01-15", "value": "85.00"}
        result = eia._parse_row(raw, "WTI_SPOT", "barrel")
        assert result is not None
        assert result["time"].tzinfo == timezone.utc

    def test_bad_period_format_returns_none(self):
        raw = {"period": "April 21 2026", "value": "87.45"}
        assert eia._parse_row(raw, "BRENT_SPOT", "barrel") is None


# ---------------------------------------------------------------------------
# FRED parsing tests
# ---------------------------------------------------------------------------

class TestFREDParseRow:
    def test_valid_brent_row(self):
        raw = {"date": "2026-04-21", "value": "87.45"}
        result = fred._parse_row(raw, "BRENT_SPOT", "barrel")
        assert result is not None
        assert result["series_id"] == "BRENT_SPOT"
        assert result["source"] == "fred"
        assert result["price"] == 87.45
        assert result["currency"] == "USD"
        assert result["unit"] == "barrel"

    def test_missing_placeholder_returns_none(self):
        """FRED uses '.' to indicate missing data — must be skipped."""
        raw = {"date": "2026-04-18", "value": "."}
        assert fred._parse_row(raw, "BRENT_SPOT", "barrel") is None

    def test_missing_date_returns_none(self):
        raw = {"value": "87.45"}
        assert fred._parse_row(raw, "BRENT_SPOT", "barrel") is None

    def test_missing_value_key_returns_none(self):
        raw = {"date": "2026-04-21"}
        assert fred._parse_row(raw, "BRENT_SPOT", "barrel") is None

    def test_non_numeric_value_returns_none(self):
        raw = {"date": "2026-04-21", "value": "n/a"}
        assert fred._parse_row(raw, "BRENT_SPOT", "barrel") is None

    def test_wti_row(self):
        raw = {"date": "2026-04-20", "value": "82.10"}
        result = fred._parse_row(raw, "WTI_SPOT", "barrel")
        assert result is not None
        assert result["series_id"] == "WTI_SPOT"
        assert abs(result["price"] - 82.10) < 1e-6

    def test_timestamp_is_utc(self):
        raw = {"date": "2026-03-01", "value": "79.99"}
        result = fred._parse_row(raw, "BRENT_SPOT", "barrel")
        assert result is not None
        assert result["time"].tzinfo == timezone.utc
        assert result["time"] == datetime(2026, 3, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Alpha Vantage parsing tests
# ---------------------------------------------------------------------------

class TestAlphaVantageParseRow:
    def _bounds(self) -> tuple[date, date]:
        return date(2026, 1, 1), date(2026, 4, 22)

    def test_valid_brent_row(self):
        raw = {"date": "2026-04-21", "value": "87.45"}
        start, end = self._bounds()
        result = alpha_vantage._parse_row(raw, "BRENT_SPOT", "barrel", start, end)
        assert result is not None
        assert result["series_id"] == "BRENT_SPOT"
        assert result["source"] == "alpha_vantage"
        assert result["price"] == 87.45
        assert result["unit"] == "barrel"

    def test_natural_gas_row(self):
        raw = {"date": "2026-04-10", "value": "2.15"}
        start, end = self._bounds()
        result = alpha_vantage._parse_row(raw, "NATURAL_GAS_HH", "mmbtu", start, end)
        assert result is not None
        assert result["unit"] == "mmbtu"
        assert result["series_id"] == "NATURAL_GAS_HH"

    def test_date_before_start_filtered(self):
        """Alpha Vantage returns full history; client-side filtering must drop old rows."""
        raw = {"date": "2025-12-31", "value": "75.00"}
        start, end = self._bounds()
        assert alpha_vantage._parse_row(raw, "BRENT_SPOT", "barrel", start, end) is None

    def test_date_after_end_filtered(self):
        raw = {"date": "2026-12-01", "value": "95.00"}
        start, end = self._bounds()
        assert alpha_vantage._parse_row(raw, "BRENT_SPOT", "barrel", start, end) is None

    def test_missing_value_returns_none(self):
        raw = {"date": "2026-04-21"}
        start, end = self._bounds()
        assert alpha_vantage._parse_row(raw, "BRENT_SPOT", "barrel", start, end) is None

    def test_non_numeric_value_returns_none(self):
        raw = {"date": "2026-04-21", "value": "NA"}
        start, end = self._bounds()
        assert alpha_vantage._parse_row(raw, "BRENT_SPOT", "barrel", start, end) is None

    def test_timestamp_is_utc(self):
        raw = {"date": "2026-02-15", "value": "80.00"}
        start, end = self._bounds()
        result = alpha_vantage._parse_row(raw, "WTI_SPOT", "barrel", start, end)
        assert result is not None
        assert result["time"].tzinfo == timezone.utc

    def test_boundary_dates_included(self):
        """start and end dates are inclusive."""
        raw_start = {"date": "2026-01-01", "value": "77.00"}
        raw_end = {"date": "2026-04-22", "value": "88.00"}
        start, end = self._bounds()
        assert alpha_vantage._parse_row(raw_start, "BRENT_SPOT", "barrel", start, end) is not None
        assert alpha_vantage._parse_row(raw_end, "BRENT_SPOT", "barrel", start, end) is not None
