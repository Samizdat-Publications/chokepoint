"""Unit tests for aisstream.io message parsing."""
import os
from datetime import timezone

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("AISSTREAM_API_KEY", "test-key")

from vessel_positions import aisstream  # noqa: E402


def _make_position_msg(
    mmsi: int = 123456789,
    lat: float = 26.65,
    lon: float = 56.25,
    time_utc: str = "2026-04-22T10:00:00Z",
    sog: float = 12.5,
) -> dict:
    return {
        "MessageType": "PositionReport",
        "MetaData": {
            "MMSI": mmsi,
            "time_utc": time_utc,
            "ShipName": "TEST TANKER",
        },
        "Message": {
            "PositionReport": {
                "Latitude": lat,
                "Longitude": lon,
                "Sog": sog,
                "Cog": 270.0,
                "TrueHeading": 268,
                "NavigationalStatus": 0,
            }
        },
    }


def _make_static_msg(mmsi: int = 123456789, ship_type: int = 80, length: int = 330) -> dict:
    return {
        "MessageType": "ShipStaticData",
        "MetaData": {"MMSI": mmsi},
        "Message": {
            "ShipStaticData": {
                "Name": "HORMUZ STAR",
                "ImoNumber": 9876543,
                "CallSign": "ABCD1",
                "Type": ship_type,
                "MaximumStaticDraught": 21.5,
                "Destination": "FUJAIRAH",
                "Dimension": {"A": 180, "B": 150, "C": 30, "D": 32},
            }
        },
    }


class TestParsePositionReport:
    def setup_method(self):
        # Clear vessel cache between tests
        aisstream._vessel_cache.clear()

    def test_valid_position_no_static(self):
        msg = _make_position_msg()
        record = aisstream._parse_position_report(msg)
        # Without static data we don't know ship type, so it should be included
        assert record is not None
        assert record["mmsi"] == 123456789
        assert record["lat"] == 26.65
        assert record["lon"] == 56.25
        assert record["speed"] == 12.5

    def test_position_outside_bbox(self):
        msg = _make_position_msg(lat=30.0, lon=50.0)
        assert aisstream._parse_position_report(msg) is None

    def test_enriched_with_static_data(self):
        static_msg = _make_static_msg()
        aisstream._parse_ship_static(static_msg)

        pos_msg = _make_position_msg()
        record = aisstream._parse_position_report(pos_msg)

        assert record is not None
        assert record["vessel_name"] == "HORMUZ STAR"
        assert record["vessel_type"] == "VLCC"  # 330m → VLCC
        assert record["imo"] == 9876543
        assert record["destination"] == "FUJAIRAH"

    def test_non_tanker_with_static_is_filtered(self):
        # Inject static data saying this is a fishing vessel
        aisstream._vessel_cache[123456789] = {
            "vessel_name": "FISHER",
            "imo": None,
            "callsign": None,
            "ais_ship_type": 30,  # Fishing
            "destination": None,
            "draught": None,
            "length_m": None,
            "vessel_type": None,
        }
        msg = _make_position_msg()
        assert aisstream._parse_position_report(msg) is None

    def test_timestamp_parsing(self):
        msg = _make_position_msg(time_utc="2026-04-22T12:30:00Z")
        record = aisstream._parse_position_report(msg)
        assert record is not None
        assert record["time"].tzinfo is not None
        assert record["time"].hour == 12


class TestParseShipStatic:
    def setup_method(self):
        aisstream._vessel_cache.clear()

    def test_caches_vessel_data(self):
        msg = _make_static_msg(mmsi=999888777)
        aisstream._parse_ship_static(msg)

        cached = aisstream._vessel_cache.get(999888777)
        assert cached is not None
        assert cached["vessel_name"] == "HORMUZ STAR"
        assert cached["ais_ship_type"] == 80
        assert cached["length_m"] == 330.0  # 180 + 150

    def test_no_mmsi_is_ignored(self):
        msg = {"MessageType": "ShipStaticData", "MetaData": {}, "Message": {"ShipStaticData": {}}}
        aisstream._parse_ship_static(msg)  # Should not raise
        assert len(aisstream._vessel_cache) == 0
