"""
Filtering logic for AIS vessel data.

Handles:
  - Strait of Hormuz bounding box containment check
  - VLCC / Suezmax / tanker classification from AIS ship-type codes
"""
from __future__ import annotations

from common.config import config

# ---------------------------------------------------------------------------
# AIS ship type codes (ITU-R M.1371-5, Table 53)
# ---------------------------------------------------------------------------
# 80-89 are all "Tanker" categories; 84 = Tanker carrying dangerous goods
TANKER_AIS_TYPES: frozenset[int] = frozenset(range(80, 90))

# Vessel type classification by ship-type code.
# Distinguishing VLCC/Suezmax from AIS alone is approximate —
# the AIS standard encodes broad categories, not DWT.
# We use ship-type code + name/dimension heuristics where available.
_AIS_TYPE_LABEL: dict[int, str] = {
    80: "Tanker",
    81: "Tanker — Hazardous A",
    82: "Tanker — Hazardous B",
    83: "Tanker — Hazardous C",
    84: "Tanker — Hazardous D",
    85: "Tanker",
    86: "Tanker",
    87: "Tanker",
    88: "Tanker",
    89: "Tanker — No additional info",
}

# VLCC: beam ≥ 50m or length ≥ 300m; Suezmax: beam 40-49m or length 250-299m.
# These thresholds are approximate; exact DWT requires external vessel DB lookup.
_VLCC_MIN_LENGTH_M = 300
_SUEZMAX_MIN_LENGTH_M = 250


def in_hormuz_bbox(lat: float, lon: float) -> bool:
    """Return True if the coordinate is inside the Strait of Hormuz bounding box."""
    return (
        config.hormuz_lat_min <= lat <= config.hormuz_lat_max
        and config.hormuz_lon_min <= lon <= config.hormuz_lon_max
    )


def classify_vessel(
    ais_ship_type: int | None,
    vessel_name: str | None = None,
    length_m: float | None = None,
) -> str | None:
    """
    Return a vessel-type label for a position record, or None if not a tanker.

    Priority:
    1. If ais_ship_type is not in the tanker range → None (skip)
    2. If dimensional data is available → VLCC / Suezmax / Tanker
    3. Otherwise → 'Tanker' (generic)
    """
    if ais_ship_type is None or ais_ship_type not in TANKER_AIS_TYPES:
        return None

    label = _AIS_TYPE_LABEL.get(ais_ship_type, "Tanker")

    if length_m is not None:
        if length_m >= _VLCC_MIN_LENGTH_M:
            return "VLCC"
        if length_m >= _SUEZMAX_MIN_LENGTH_M:
            return "Suezmax"

    return label


def is_target_vessel(ais_ship_type: int | None) -> bool:
    """Return True if this vessel is in scope (any tanker class)."""
    return ais_ship_type is not None and ais_ship_type in TANKER_AIS_TYPES
