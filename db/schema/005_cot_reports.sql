-- CFTC Commitments of Traders reports
CREATE TABLE IF NOT EXISTS cot_reports (
    time                    TIMESTAMPTZ NOT NULL,
    commodity               TEXT        NOT NULL,   -- 'CRUDE_OIL_WTI', 'BRENT_CRUDE'
    report_date             DATE        NOT NULL,
    commercial_long         BIGINT,
    commercial_short        BIGINT,
    noncommercial_long      BIGINT,
    noncommercial_short     BIGINT,
    noncommercial_spreads   BIGINT,
    open_interest           BIGINT,
    source                  TEXT        NOT NULL DEFAULT 'cftc'
);

SELECT create_hypertable('cot_reports', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_cot_commodity_time ON cot_reports (commodity, time DESC);
