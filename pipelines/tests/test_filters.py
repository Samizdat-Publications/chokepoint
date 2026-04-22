"""Unit tests for vessel filtering logic."""
import os

import pytest

# Set required env vars before importing config
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from vessel_positions.filters import (  # noqa: E402
    classify_vessel,
    in_hormuz_bbox,
    is_target_vessel,
)


class TestHormuzBbox:
    def test_inside_strait(self):
        assert in_hormuz_bbox(26.6, 56.2) is True

    def test_outside_lat_low(self):
        assert in_hormuz_bbox(26.0, 56.2) is False

    def test_outside_lat_high(self):
        assert in_hormuz_bbox(27.0, 56.2) is False

    def test_outside_lon_low(self):
        assert in_hormuz_bbox(26.6, 55.0) is False

    def test_outside_lon_high(self):
        assert in_hormuz_bbox(26.6, 57.0) is False

    def test_boundary_min(self):
        assert in_hormuz_bbox(26.5, 56.0) is True

    def test_boundary_max(self):
        assert in_hormuz_bbox(26.8, 56.5) is True


class TestVesselClassification:
    def test_tanker_no_dimensions(self):
        result = classify_vessel(ais_ship_type=80)
        assert result == "Tanker"

    def test_vlcc_by_length(self):
        result = classify_vessel(ais_ship_type=80, length_m=320)
        assert result == "VLCC"

    def test_suezmax_by_length(self):
        result = classify_vessel(ais_ship_type=80, length_m=270)
        assert result == "Suezmax"

    def test_tanker_short_vessel(self):
        result = classify_vessel(ais_ship_type=80, length_m=180)
        assert result == "Tanker"

    def test_non_tanker_returns_none(self):
        result = classify_vessel(ais_ship_type=30)  # Fishing
        assert result is None

    def test_none_ship_type_returns_none(self):
        result = classify_vessel(ais_ship_type=None)
        assert result is None

    def test_all_tanker_codes(self):
        for code in range(80, 90):
            assert classify_vessel(ais_ship_type=code) is not None


class TestIsTargetVessel:
    def test_tanker_is_target(self):
        assert is_target_vessel(80) is True
        assert is_target_vessel(84) is True
        assert is_target_vessel(89) is True

    def test_non_tanker_not_target(self):
        assert is_target_vessel(30) is False  # Fishing
        assert is_target_vessel(70) is False  # Cargo

    def test_none_not_target(self):
        assert is_target_vessel(None) is False
