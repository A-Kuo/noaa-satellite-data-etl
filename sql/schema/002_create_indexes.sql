-- ---------------------------------------------------------------------------
-- Spatial indexes (GIST) — essential for ST_Intersects / ST_DWithin queries
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_noaa_acq_footprint
    ON noaa_acquisitions USING GIST (footprint);

CREATE INDEX IF NOT EXISTS idx_acq_footprints_geom
    ON acquisition_footprints USING GIST (footprint);

CREATE INDEX IF NOT EXISTS idx_coverage_stats_union
    ON coverage_statistics USING GIST (coverage_union);

-- ---------------------------------------------------------------------------
-- B-tree indexes for common filter/join columns
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_noaa_acq_event
    ON noaa_acquisitions (event_name);

CREATE INDEX IF NOT EXISTS idx_noaa_acq_date
    ON noaa_acquisitions (acquisition_date DESC);

CREATE INDEX IF NOT EXISTS idx_noaa_acq_sensor
    ON noaa_acquisitions (sensor);

CREATE INDEX IF NOT EXISTS idx_coverage_stats_event_date
    ON coverage_statistics (event_name, stat_date DESC);

CREATE INDEX IF NOT EXISTS idx_acq_footprints_acq_id
    ON acquisition_footprints (acquisition_id);
