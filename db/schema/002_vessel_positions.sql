-- Vessel positions table for AIS tracking data
-- Stores every position report received for vessels transiting the Strait of Hormuz
CREATE TABLE IF NOT EXISTS vessel_positions (
    time            TIMESTAMPTZ     NOT NULL,
    mmsi            BIGINT          NOT NULL,       -- Maritime Mobile Service Identity (vessel ID)
    vessel_name     TEXT,
    vessel_type     TEXT,                           -- e.g. 'VLCC', 'Suezmax', 'Tanker'
    imo             BIGINT,                         -- IMO ship number (permanent vessel ID)
    callsign        TEXT,
    flag            TEXT,                           -- ISO 3166-1 alpha-2 country code
    lat             DOUBLE PRECISION NOT NULL,      -- degrees, WGS84
    lon             DOUBLE PRECISION NOT NULL,      -- degrees, WGS84
    speed           REAL,                           -- knots (SOG)
    course          REAL,                           -- degrees true (COG)
    heading         REAL,                           -- degrees true (HDG)
    nav_status      INTEGER,                        -- AIS navigational status (0=underway, 1=anchored, etc.)
    destination     TEXT,
    draught         REAL,                           -- metres (loaded draught)
    ais_ship_type   INTEGER,                        -- AIS ship type code (80-89 = tanker)
    source          TEXT NOT NULL DEFAULT 'aisstream'
);

-- Convert to TimescaleDB hypertable partitioned by time
SELECT create_hypertable('vessel_positions', 'time', if_not_exists => TRUE);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_vessel_positions_mmsi_time
    ON vessel_positions (mmsi, time DESC);

CREATE INDEX IF NOT EXISTS idx_vessel_positions_vessel_type_time
    ON vessel_positions (vessel_type, time DESC);

-- Daily transit count materialized view
-- Counts distinct VLCC/Suezmax vessels crossing the Strait bounding box per day
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_hormuz_transits
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time)     AS day,
    vessel_type,
    COUNT(DISTINCT mmsi)            AS vessel_count,
    COUNT(*)                        AS position_count,
    AVG(speed)                      AS avg_speed_knots
FROM vessel_positions
WHERE vessel_type IN ('VLCC', 'Suezmax', 'Tanker')
  AND lat BETWEEN 26.5 AND 26.8
  AND lon BETWEEN 56.0 AND 56.5
GROUP BY day, vessel_type
WITH NO DATA;

-- Refresh policy: update daily view once per hour
SELECT add_continuous_aggregate_policy(
    'daily_hormuz_transits',
    start_offset => INTERVAL '3 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);
