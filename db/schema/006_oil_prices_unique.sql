-- Add unique constraint on (series_id, time, source) to enable idempotent upserts.
-- Required by insert_oil_prices() in common/db.py.
ALTER TABLE oil_prices
    ADD CONSTRAINT uq_oil_prices_series_time_source
    UNIQUE (series_id, time, source);
