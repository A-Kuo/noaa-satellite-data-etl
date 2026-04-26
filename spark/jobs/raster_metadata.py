"""PySpark job: extract metadata from staged GeoTIFF files at scale.

Scans the staging directory (local or object store) for .tif files,
extracts raster metadata using rasterio (distributed via UDF), and
writes a metadata Parquet table for downstream ingestion.

Usage:
    spark-submit \\
        --master spark://spark-master:7077 \\
        spark/jobs/raster_metadata.py \\
        --staging-path /data/staging \\
        --output /data/raster_metadata
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

METADATA_SCHEMA = StructType(
    [
        StructField("file_path", StringType(), False),
        StructField("filename", StringType(), False),
        StructField("width_px", IntegerType(), True),
        StructField("height_px", IntegerType(), True),
        StructField("band_count", IntegerType(), True),
        StructField("crs", StringType(), True),
        StructField("resolution_x", DoubleType(), True),
        StructField("resolution_y", DoubleType(), True),
        StructField("bbox_west", DoubleType(), True),
        StructField("bbox_south", DoubleType(), True),
        StructField("bbox_east", DoubleType(), True),
        StructField("bbox_north", DoubleType(), True),
        StructField("file_size_bytes", IntegerType(), True),
        StructField("error", StringType(), True),
    ]
)


def extract_metadata_udf(paths: Iterator[str]) -> Iterator[tuple]:
    """Per-partition UDF: call rasterio without importing at driver."""
    import rasterio  # noqa: PLC0415 — deferred to worker

    for path in paths:
        try:
            with rasterio.open(path) as src:
                bounds = src.bounds
                res = src.res
                yield (
                    path,
                    Path(path).name,
                    src.width,
                    src.height,
                    src.count,
                    str(src.crs),
                    float(res[0]),
                    float(res[1]),
                    float(bounds.left),
                    float(bounds.bottom),
                    float(bounds.right),
                    float(bounds.top),
                    int(Path(path).stat().st_size) if Path(path).exists() else None,
                    None,
                )
        except Exception as exc:
            yield (path, Path(path).name, None, None, None, None, None, None,
                   None, None, None, None, None, str(exc))


def discover_tif_files(staging_path: str) -> list[str]:
    return [
        str(p)
        for p in Path(staging_path).rglob("*.tif")
        if p.is_file()
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--partitions", type=int, default=8)
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("noaa_raster_metadata")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )

    files = discover_tif_files(args.staging_path)
    if not files:
        print(f"No .tif files found under {args.staging_path}")
        spark.stop()
        return

    print(f"Processing {len(files)} GeoTIFF files")

    paths_df = spark.createDataFrame([(f,) for f in files], ["file_path"])

    metadata_df = paths_df.repartition(args.partitions).mapInPandas(
        lambda it: (
            dict(zip(METADATA_SCHEMA.fieldNames(), row))
            for row in extract_metadata_udf(r["file_path"] for r in it)
        ),
        schema=METADATA_SCHEMA,
    )

    (
        metadata_df.write.mode("overwrite")
        .parquet(args.output)
    )

    print(f"Metadata written to {args.output}")
    spark.stop()


if __name__ == "__main__":
    main()
