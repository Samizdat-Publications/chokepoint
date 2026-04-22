-- Oil and energy price time-series table
CREATE TABLE IF NOT EXISTS oil_prices (
    time        TIMESTAMPTZ     NOT NULL,
    series_id   TEXT            NOT NULL,   -- e.g. 'BRENT_SPOT', 'WTI_FUTURES', 'RETAIL_GASOLINE_US'
    source      TEXT            NOT NULL,   -- 'eia', 'fred', 'alpha_vantage'
    price       DOUBLE PRECISION NOT NULL,
    currency    TEXT            NOT NULL DEFAULT 'USD',
    unit        TEXT            NOT NULL    -- 'barrel', 'gallon', 'mmbtu'
);

SELECT create_hypertable('oil_prices', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_oil_prices_series_time ON oil_prices (series_id, time DESC);
