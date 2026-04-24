# NOAA Satellite Data ETL to Data Warehouse

Building a scalable ETL pipeline to ingest, transform, and warehouse NOAA Emergency Response Imagery and geospatial metadata.

## Overview

This project demonstrates **data engineering infrastructure** for satellite data ingestion and warehouse management:
- NOAA Emergency Response Imagery (15-30cm resolution)
- Geospatial metadata and coverage tracking
- PostGIS-enabled warehouse for spatial analysis
- dbt transformations for reproducibility

**Future Integration:** This DW layer will feed into the neural-network-human-geography repo for ML preprocessing and analysis.

## Architecture

```
NOAA API / Remote Server
        ↓
   Download Pipeline
        ↓
   Local Storage (Staged)
        ↓
   PostgreSQL (PostGIS)
   ├── noaa_acquisitions (raw metadata)
   ├── coverage_statistics (aggregations)
   └── geometry (spatial footprints)
        ↓
   dbt Transformations
   (Quality, Lineage, Documentation)
        ↓
   Data Warehouse (Ready for ML)
```

## Key Features

- **Metadata-First Approach:** Catalog imagery before processing
- **PostGIS Integration:** Spatial queries (intersection, buffer, distance)
- **dbt Transformations:** Data lineage and quality checks
- **Partition Strategy:** By date and geographic region
- **Integration Ready:** Schema designed for ML preprocessing

## SQL Capabilities Demonstrated

- Geospatial queries (ST_Intersects, ST_DWithin, ST_Union)
- Window functions for temporal aggregation
- CTEs for multi-stage transformations
- Partitioning for performance at scale
- Data quality assertions in dbt

---

**Status:** Schema design and ingestion planning  
**Next:** NOAA API integration and metadata ingestion
