"""
Environment-based configuration for all ChokePoint pipelines.
Load a .env file or set these as real environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    # --- Database ---
    database_url: str = field(
        default_factory=lambda: _require("DATABASE_URL")
    )

    # --- AIS sources ---
    ais_source: str = field(
        default_factory=lambda: os.environ.get("AIS_SOURCE", "aisstream")
    )
    aisstream_api_key: str = field(
        default_factory=lambda: os.environ.get("AISSTREAM_API_KEY", "")
    )
    marinetraffic_api_key: str = field(
        default_factory=lambda: os.environ.get("MARINETRAFFIC_API_KEY", "")
    )
    spire_api_token: str = field(
        default_factory=lambda: os.environ.get("SPIRE_API_TOKEN", "")
    )

    # --- Strait of Hormuz bounding box ---
    # Core chokepoint as specified in HOR-3. Configurable for wider area queries.
    hormuz_lat_min: float = field(
        default_factory=lambda: float(os.environ.get("HORMUZ_LAT_MIN", "26.5"))
    )
    hormuz_lat_max: float = field(
        default_factory=lambda: float(os.environ.get("HORMUZ_LAT_MAX", "26.8"))
    )
    hormuz_lon_min: float = field(
        default_factory=lambda: float(os.environ.get("HORMUZ_LON_MIN", "56.0"))
    )
    hormuz_lon_max: float = field(
        default_factory=lambda: float(os.environ.get("HORMUZ_LON_MAX", "56.5"))
    )

    # --- Pipeline settings ---
    poll_interval_seconds: int = field(
        default_factory=lambda: int(os.environ.get("POLL_INTERVAL_SECONDS", "900"))
    )
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO")
    )


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set")
    return value


# Module-level singleton — import this everywhere
config = Config()
