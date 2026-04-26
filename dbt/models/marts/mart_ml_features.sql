{{
    config(
        materialized='table',
        schema='marts',
        indexes=[
            {'columns': ['acquisition_id'], 'unique': True},
            {'columns': ['event_name', 'acquisition_date']},
        ]
    )
}}

-- ML-ready feature table: one row per acquisition with engineered features.
-- Downstream consumers (neural-network-human-geography repo) join on
-- acquisition_id or filter by event/date.
WITH base AS (
    SELECT
        acquisition_id,
        event_name,
        acquisition_date,
        sensor,
        resolution_cm,
        footprint,
        footprint_area_km2,
        acquisition_year,
        acquisition_month
    FROM {{ ref('stg_noaa_acquisitions') }}
),

coverage AS (
    SELECT
        event_name,
        stat_date,
        avg_resolution_cm          AS event_avg_resolution_cm,
        total_area_km2             AS event_daily_area_km2,
        cumulative_acquisitions    AS event_cumulative_count
    FROM {{ ref('coverage_statistics') }}
),

with_features AS (
    SELECT
        b.acquisition_id,
        b.event_name,
        b.acquisition_date,
        b.sensor,
        b.resolution_cm,

        -- Geospatial features
        b.footprint_area_km2,
        ST_X(ST_Centroid(b.footprint))                              AS centroid_lon,
        ST_Y(ST_Centroid(b.footprint))                              AS centroid_lat,
        ST_XMin(b.footprint)                                        AS bbox_west,
        ST_YMin(b.footprint)                                        AS bbox_south,
        ST_XMax(b.footprint)                                        AS bbox_east,
        ST_YMax(b.footprint)                                        AS bbox_north,
        ST_XMax(b.footprint) - ST_XMin(b.footprint)                AS bbox_width_deg,
        ST_YMax(b.footprint) - ST_YMin(b.footprint)                AS bbox_height_deg,

        -- Temporal features
        b.acquisition_year,
        b.acquisition_month,
        DATE_PART('doy', b.acquisition_date)::INT                  AS day_of_year,
        DATE_PART('dow', b.acquisition_date)::INT                  AS day_of_week,

        -- Event-level context
        c.event_avg_resolution_cm,
        c.event_daily_area_km2,
        c.event_cumulative_count,

        -- Resolution normalised vs event average (z-score numerator)
        b.resolution_cm - c.event_avg_resolution_cm                AS resolution_delta_cm,

        -- Rank by area within event-day partition
        RANK() OVER (
            PARTITION BY b.event_name, b.acquisition_date
            ORDER BY b.footprint_area_km2 DESC
        )                                                           AS area_rank_in_event_day

    FROM base b
    LEFT JOIN coverage c
        ON c.event_name = b.event_name
        AND c.stat_date = b.acquisition_date
)

SELECT * FROM with_features
