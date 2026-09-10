-- FareLens fare_observations table
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS fare_observations (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    observed_at          TIMESTAMPTZ NOT NULL,
    travel_date          DATE NOT NULL,
    origin               VARCHAR(3) NOT NULL,
    destination          VARCHAR(3) NOT NULL,
    route                VARCHAR(7) NOT NULL,
    airline              VARCHAR(100) NOT NULL,
    flight_number        VARCHAR(20),
    source               VARCHAR(100) NOT NULL,
    price                NUMERIC(10,2) NOT NULL,
    currency             VARCHAR(3) NOT NULL DEFAULT 'INR',
    base_fare            NUMERIC(10,2),
    taxes                NUMERIC(10,2),
    fees                 NUMERIC(10,2),
    stops                INTEGER NOT NULL DEFAULT 0,
    duration_minutes     INTEGER,
    cabin_class          VARCHAR(30),
    passengers           INTEGER NOT NULL DEFAULT 1,
    advance_purchase_days INTEGER,
    advance_window       VARCHAR(10),   -- T+1 | T+7 | T+15 | T+30 | T+45 | NULL
    availability         VARCHAR(20) DEFAULT 'available',
    data_type            VARCHAR(10) NOT NULL CHECK (data_type IN ('LIVE', 'MOCK')),
    booking_url          TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Idempotency: same flight observed within the same minute is a duplicate.
    -- Two identical flights observed at different minutes are legitimate separate observations.
    UNIQUE (
        route,
        airline,
        COALESCE(flight_number, ''),
        source,
        data_type,
        date_trunc('minute', observed_at),
        travel_date
    )
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_fo_route          ON fare_observations(route);
CREATE INDEX IF NOT EXISTS idx_fo_observed_at    ON fare_observations(observed_at);
CREATE INDEX IF NOT EXISTS idx_fo_travel_date    ON fare_observations(travel_date);
CREATE INDEX IF NOT EXISTS idx_fo_airline        ON fare_observations(airline);
CREATE INDEX IF NOT EXISTS idx_fo_source         ON fare_observations(source);
CREATE INDEX IF NOT EXISTS idx_fo_advance_window ON fare_observations(advance_window);
CREATE INDEX IF NOT EXISTS idx_fo_data_type      ON fare_observations(data_type);

-- Enable Row Level Security
ALTER TABLE fare_observations ENABLE ROW LEVEL SECURITY;

-- Allow SELECT for anyone (read-only public access)
CREATE POLICY "allow_select" ON fare_observations
    FOR SELECT USING (true);

-- INSERT/UPDATE/DELETE only via service role (backend)
-- The frontend never writes directly to this table.
