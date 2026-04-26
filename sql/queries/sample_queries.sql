-- ---------------------------------------------------------------------------
-- Sample geospatial queries demonstrating PostGIS capabilities
-- ---------------------------------------------------------------------------

-- 1. Find all acquisitions that intersect a given area of interest (AOI)
--    Replace the WKT with any polygon in EPSG:4326.
SELECT
    a.acquisition_id,
    a.event_name,
    a.acquisition_date,
    a.sensor,
    a.resolution_cm,
    ST_Area(a.footprint::geography) / 1e6 AS area_km2
FROM noaa_acquisitions a
WHERE ST_Intersects(
    a.footprint,
    ST_GeomFromText(
        'POLYGON((-90.5 29.8, -89.5 29.8, -89.5 30.5, -90.5 30.5, -90.5 29.8))',
        4326
    )
)
ORDER BY a.acquisition_date DESC;


-- 2. Acquisitions within 50 km of a point (e.g., New Orleans city centre)
SELECT
    a.acquisition_id,
    a.event_name,
    a.acquisition_date,
    ST_Distance(a.footprint::geography, ST_MakePoint(-90.07, 29.95)::geography) / 1000 AS dist_km
FROM noaa_acquisitions a
WHERE ST_DWithin(
    a.footprint::geography,
    ST_MakePoint(-90.07, 29.95)::geography,
    50000   -- metres
)
ORDER BY dist_km;


-- 3. Union of all footprints per event — useful for coverage maps
SELECT
    event_name,
    ST_Union(footprint)            AS coverage_polygon,
    SUM(ST_Area(footprint::geography)) / 1e6 AS total_area_km2,
    COUNT(*)                       AS acquisition_count
FROM noaa_acquisitions
GROUP BY event_name;


-- 4. Monthly acquisition counts with running total (window function)
SELECT
    event_name,
    DATE_TRUNC('month', acquisition_date)          AS month,
    COUNT(*)                                        AS monthly_count,
    SUM(COUNT(*)) OVER (
        PARTITION BY event_name
        ORDER BY DATE_TRUNC('month', acquisition_date)
    )                                               AS running_total
FROM noaa_acquisitions
GROUP BY event_name, DATE_TRUNC('month', acquisition_date)
ORDER BY event_name, month;


-- 5. Multi-stage CTE: identify gaps in coverage (days with no acquisitions)
WITH event_dates AS (
    SELECT
        event_name,
        MIN(acquisition_date) AS first_date,
        MAX(acquisition_date) AS last_date
    FROM noaa_acquisitions
    GROUP BY event_name
),
date_series AS (
    SELECT
        e.event_name,
        generate_series(e.first_date, e.last_date, '1 day'::interval)::date AS dt
    FROM event_dates e
),
acquired AS (
    SELECT DISTINCT event_name, acquisition_date
    FROM noaa_acquisitions
)
SELECT
    ds.event_name,
    ds.dt AS gap_date
FROM date_series ds
LEFT JOIN acquired a
    ON a.event_name = ds.event_name
    AND a.acquisition_date = ds.dt
WHERE a.acquisition_date IS NULL
ORDER BY ds.event_name, ds.dt;


-- 6. Top sensors by average resolution per event
SELECT
    event_name,
    sensor,
    ROUND(AVG(resolution_cm), 2)  AS avg_resolution_cm,
    COUNT(*)                       AS acquisition_count,
    RANK() OVER (
        PARTITION BY event_name
        ORDER BY AVG(resolution_cm)
    )                              AS resolution_rank
FROM noaa_acquisitions
GROUP BY event_name, sensor
ORDER BY event_name, resolution_rank;
