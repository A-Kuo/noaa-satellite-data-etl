{{
    config(
        materialized='view',
        schema='staging'
    )
}}

-- Lightweight staging view: cast types and rename for consistency.
-- Source: raw table populated by the Python ETL pipeline.
SELECT
    acquisition_id,
    TRIM(event_name)                        AS event_name,
    acquisition_date,
    UPPER(TRIM(sensor))                     AS sensor,
    resolution_cm::NUMERIC(6,2)             AS resolution_cm,
    footprint,
    download_url,
    file_size_bytes,
    crs,
    ingested_at,

    -- Derived convenience columns
    DATE_PART('year', acquisition_date)::INT  AS acquisition_year,
    DATE_PART('month', acquisition_date)::INT AS acquisition_month,
    ST_Area(footprint::geography) / 1e6       AS footprint_area_km2
FROM {{ source('raw', 'noaa_acquisitions') }}
WHERE acquisition_id IS NOT NULL
  AND resolution_cm > 0
