-- Enable PostGIS extension (idempotent)
CREATE EXTENSION IF NOT EXISTS postgis;

-- ---------------------------------------------------------------------------
-- Raw acquisition metadata ingested from the NOAA catalog
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS noaa_acquisitions (
    acquisition_id   TEXT        PRIMARY KEY,
    event_name       TEXT        NOT NULL,
    acquisition_date DATE        NOT NULL,
    sensor           TEXT        NOT NULL,
    resolution_cm    NUMERIC(6,2) NOT NULL CHECK (resolution_cm > 0),
    footprint        GEOMETRY(Polygon, 4326) NOT NULL,
    download_url     TEXT        NOT NULL,
    file_size_bytes  BIGINT,
    crs              TEXT        NOT NULL DEFAULT 'EPSG:4326',
    ingested_at      TIMESTAMPTZ NOT NULL DEFAULT now()
)
PARTITION BY RANGE (acquisition_date);

-- Monthly partitions for the most common query range (add more as needed)
CREATE TABLE IF NOT EXISTS noaa_acquisitions_2024_q1
    PARTITION OF noaa_acquisitions
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE IF NOT EXISTS noaa_acquisitions_2024_q2
    PARTITION OF noaa_acquisitions
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

CREATE TABLE IF NOT EXISTS noaa_acquisitions_2024_q3
    PARTITION OF noaa_acquisitions
    FOR VALUES FROM ('2024-07-01') TO ('2024-10-01');

CREATE TABLE IF NOT EXISTS noaa_acquisitions_2024_q4
    PARTITION OF noaa_acquisitions
    FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');

CREATE TABLE IF NOT EXISTS noaa_acquisitions_2025
    PARTITION OF noaa_acquisitions
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE IF NOT EXISTS noaa_acquisitions_default
    PARTITION OF noaa_acquisitions DEFAULT;

-- ---------------------------------------------------------------------------
-- Pre-aggregated coverage statistics (refreshed by dbt)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coverage_statistics (
    stat_id          BIGSERIAL   PRIMARY KEY,
    event_name       TEXT        NOT NULL,
    stat_date        DATE        NOT NULL,
    acquisition_count INT        NOT NULL DEFAULT 0,
    total_area_km2   NUMERIC(12,4),
    avg_resolution_cm NUMERIC(6,2),
    coverage_union   GEOMETRY(MultiPolygon, 4326),
    computed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (event_name, stat_date)
);

-- ---------------------------------------------------------------------------
-- Discrete spatial footprints (denormalised for fast spatial lookups)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS acquisition_footprints (
    footprint_id     BIGSERIAL   PRIMARY KEY,
    acquisition_id   TEXT        NOT NULL REFERENCES noaa_acquisitions(acquisition_id) ON DELETE CASCADE,
    footprint        GEOMETRY(Polygon, 4326) NOT NULL,
    area_km2         NUMERIC(12,4) GENERATED ALWAYS AS (
                         ST_Area(footprint::geography) / 1e6
                     ) STORED
);
