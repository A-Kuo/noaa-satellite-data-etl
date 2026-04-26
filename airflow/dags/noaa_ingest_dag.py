"""Daily NOAA acquisition ingestion DAG.

Schedule: 06:00 UTC every day.
For each configured event ID the DAG fans out parallel ingest tasks, then
waits for all to complete before triggering the dbt refresh DAG.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

# Installed via airflow/requirements.txt
from plugins.operators.noaa_operator import NOAAIngestOperator

# ---------------------------------------------------------------------------
# Configuration — extend this list as new NOAA events are catalogued
# ---------------------------------------------------------------------------
NOAA_EVENT_IDS: list[str] = [
    "2024_hurricane_helene",
    "2024_hurricane_milton",
    "2024_california_wildfires",
]

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="noaa_ingest",
    description="Fetch and load NOAA Emergency Response acquisitions into PostGIS",
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["noaa", "ingest", "etl"],
) as dag:

    ingest_tasks = [
        NOAAIngestOperator(
            task_id=f"ingest_{event_id}",
            event_id=event_id,
            db_conn_id="noaa_postgres",
        )
        for event_id in NOAA_EVENT_IDS
    ]

    trigger_dbt = TriggerDagRunOperator(
        task_id="trigger_dbt_refresh",
        trigger_dag_id="dbt_transform",
        wait_for_completion=False,
    )

    # All ingest tasks run in parallel, then trigger dbt
    ingest_tasks >> trigger_dbt
