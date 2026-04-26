{{
    config(
        materialized='table',
        schema='reporting',
        indexes=[
            {'columns': ['event_name', 'stat_date']},
        ]
    )
}}

-- Flat, denormalised view designed for direct Tableau consumption.
-- All geometry is pre-serialised as WKT strings (Tableau Spatial connector
-- can parse WKT via the MAKEPOINT / MAKELINE functions, or the raw WKT field
-- can be used with the built-in spatial file connector).
SELECT
    -- Dimensions
    cs.event_name,
    cs.stat_date,
    TO_CHAR(cs.stat_date, 'YYYY-MM')                          AS year_month,
    DATE_PART('year', cs.stat_date)::INT                       AS year,
    DATE_PART('month', cs.stat_date)::INT                      AS month,
    DATE_PART('quarter', cs.stat_date)::INT                    AS quarter,

    -- Measures
    cs.acquisition_count,
    cs.cumulative_acquisitions,
    cs.avg_resolution_cm,
    cs.total_area_km2,

    -- Coverage geometry as WKT for Tableau spatial import
    ST_AsText(cs.coverage_union)                               AS coverage_wkt,

    -- Centroid of daily coverage (Tableau MAKEPOINT-compatible)
    ST_X(ST_Centroid(cs.coverage_union::geometry))             AS coverage_centroid_lon,
    ST_Y(ST_Centroid(cs.coverage_union::geometry))             AS coverage_centroid_lat,

    -- Bounding box of daily coverage
    ST_XMin(cs.coverage_union::geometry)                       AS bbox_west,
    ST_YMin(cs.coverage_union::geometry)                       AS bbox_south,
    ST_XMax(cs.coverage_union::geometry)                       AS bbox_east,
    ST_YMax(cs.coverage_union::geometry)                       AS bbox_north,

    -- Metadata
    cs.computed_at

FROM {{ ref('coverage_statistics') }} cs
ORDER BY cs.event_name, cs.stat_date
