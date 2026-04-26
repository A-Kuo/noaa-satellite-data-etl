{{
    config(
        materialized='table',
        schema='marts',
        indexes=[
            {'columns': ['event_name', 'stat_date'], 'unique': True},
        ]
    )
}}

-- Daily coverage statistics per event, computed from the staging view.
-- Feeds the coverage_statistics warehouse table and downstream ML preprocessing.
WITH base AS (
    SELECT
        event_name,
        acquisition_date          AS stat_date,
        COUNT(*)                  AS acquisition_count,
        AVG(resolution_cm)        AS avg_resolution_cm,
        SUM(footprint_area_km2)   AS total_area_km2,
        ST_Union(footprint)       AS coverage_union
    FROM {{ ref('stg_noaa_acquisitions') }}
    GROUP BY event_name, acquisition_date
),

with_running_totals AS (
    SELECT
        event_name,
        stat_date,
        acquisition_count,
        ROUND(avg_resolution_cm::NUMERIC, 2)   AS avg_resolution_cm,
        ROUND(total_area_km2::NUMERIC, 4)       AS total_area_km2,
        coverage_union,
        SUM(acquisition_count) OVER (
            PARTITION BY event_name
            ORDER BY stat_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                        AS cumulative_acquisitions
    FROM base
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['event_name', 'stat_date']) }} AS stat_id,
    event_name,
    stat_date,
    acquisition_count,
    avg_resolution_cm,
    total_area_km2,
    cumulative_acquisitions,
    ST_Multi(coverage_union)::GEOMETRY(MultiPolygon, 4326) AS coverage_union,
    NOW()                                                   AS computed_at
FROM with_running_totals
