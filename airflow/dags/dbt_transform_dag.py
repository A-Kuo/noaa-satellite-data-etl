"""dbt transformation DAG.

Runs the full dbt project in dependency order:
  1. dbt deps     — install packages
  2. dbt run      — execute all models (staging → marts → reporting)
  3. dbt test     — run schema + data quality assertions
  4. dbt docs gen — regenerate documentation artefacts

Can be triggered on a schedule (hourly) or on-demand by the ingest DAG.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_DIR = "/opt/airflow/dbt"
DBT_PROFILES_DIR = "/opt/airflow/dbt"
DBT_TARGET = "dev"

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
    "email_on_failure": False,
}

_dbt_cmd = (
    f"cd {DBT_DIR} && "
    f"dbt {{subcommand}} "
    f"--profiles-dir {DBT_PROFILES_DIR} "
    f"--target {DBT_TARGET}"
)

with DAG(
    dag_id="dbt_transform",
    description="Run dbt models and tests against the NOAA PostGIS warehouse",
    schedule="@hourly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["dbt", "transform"],
) as dag:

    deps = BashOperator(
        task_id="dbt_deps",
        bash_command=_dbt_cmd.format(subcommand="deps"),
    )

    run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=_dbt_cmd.format(subcommand="run --select staging"),
    )

    run_marts = BashOperator(
        task_id="dbt_run_marts",
        bash_command=_dbt_cmd.format(subcommand="run --select marts"),
    )

    run_reporting = BashOperator(
        task_id="dbt_run_reporting",
        bash_command=_dbt_cmd.format(subcommand="run --select reporting"),
    )

    test = BashOperator(
        task_id="dbt_test",
        bash_command=_dbt_cmd.format(subcommand="test"),
    )

    docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=_dbt_cmd.format(subcommand="docs generate"),
    )

    deps >> run_staging >> run_marts >> run_reporting >> test >> docs
