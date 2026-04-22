-- Geopolitical events table
CREATE TABLE IF NOT EXISTS events (
    id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    time        TIMESTAMPTZ     NOT NULL,
    title       TEXT            NOT NULL,
    description TEXT,
    event_type  TEXT            NOT NULL,   -- 'geopolitical', 'sanctions', 'attack', 'weather'
    location    TEXT,
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION,
    source      TEXT            NOT NULL,   -- 'gdelt', 'newsapi', 'manual'
    source_id   TEXT,
    severity    INTEGER CHECK (severity BETWEEN 1 AND 5),
    tags        TEXT[]          DEFAULT '{}',
    created_at  TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_time ON events (time DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON events (event_type, time DESC);
