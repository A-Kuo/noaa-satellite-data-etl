"""PySpark job: aggregate per-event daily coverage statistics at scale.

Reads raw acquisitions from the PostGIS warehouse, replicates the dbt
coverage_statistics logic in Spark, and writes Parquet output to the
configured object-store / local path.  Intended for backfill runs or
large historical datasets that exceed single-node dbt capacity.

Usage:
    spark-submit \\
        --master spark://spark-master:7077 \\
        --packages org.postgresql:postgresql:42.7.3 \\
        spark/jobs/coverage_aggregator.py \\
        --output gs://your-bucket/noaa/coverage_stats
"""

from __future__ import annotations

import argparse
import os

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("noaa_coverage_aggregator")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .getOrCreate()
    )


def read_acquisitions(spark: SparkSession, jdbc_url: str, properties: dict) -> "DataFrame":
    return (
        spark.read.jdbc(
            url=jdbc_url,
            table="noaa_acquisitions",
            properties=properties,
        )
        # Drop PostGIS geometry binary column — use pre-computed bbox floats instead
        .drop("footprint")
    )


def compute_coverage(df: "DataFrame") -> "DataFrame":
    # Daily aggregates per event
    daily = df.groupBy("event_name", "acquisition_date").agg(
        F.count("*").alias("acquisition_count"),
        F.round(F.avg("resolution_cm"), 2).alias("avg_resolution_cm"),
    )

    # Cumulative running total
    w = Window.partitionBy("event_name").orderBy("acquisition_date").rowsBetween(
        Window.unboundedPreceding, Window.currentRow
    )
    return daily.withColumn(
        "cumulative_acquisitions", F.sum("acquisition_count").over(w)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Output path for Parquet files")
    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "postgres"))
    parser.add_argument("--db-port", default=os.getenv("DB_PORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "noaa_dw"))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", "postgres"))
    args = parser.parse_args()

    jdbc_url = f"jdbc:postgresql://{args.db_host}:{args.db_port}/{args.db_name}"
    properties = {
        "user": args.db_user,
        "password": args.db_password,
        "driver": "org.postgresql.Driver",
    }

    spark = build_spark()
    df = read_acquisitions(spark, jdbc_url, properties)
    result = compute_coverage(df)

    (
        result.repartition("event_name")
        .write.mode("overwrite")
        .partitionBy("event_name")
        .parquet(args.output)
    )

    print(f"Written {result.count()} rows to {args.output}")
    spark.stop()


if __name__ == "__main__":
    main()
