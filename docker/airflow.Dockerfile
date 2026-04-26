FROM apache/airflow:2.9.0-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install Airflow providers + dbt + the noaa_etl package
COPY airflow/requirements.txt /tmp/airflow-requirements.txt
RUN pip install --no-cache-dir -r /tmp/airflow-requirements.txt

# Copy DAGs, plugins, and the ETL source
COPY airflow/dags        /opt/airflow/dags
COPY airflow/plugins     /opt/airflow/plugins
COPY dbt                 /opt/airflow/dbt
COPY src                 /opt/noaa-etl/src
COPY pyproject.toml      /opt/noaa-etl/pyproject.toml
RUN pip install --no-cache-dir /opt/noaa-etl
