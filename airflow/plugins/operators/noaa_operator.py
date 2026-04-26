"""Custom Airflow operator that wraps the NOAA ETL pipeline for a single event."""

from __future__ import annotations

from airflow.models import BaseOperator
from airflow.utils.context import Context


class NOAAIngestOperator(BaseOperator):
    """Fetch all acquisitions for *event_id* and load them into PostGIS.

    Parameters
    ----------
    event_id:
        NOAA event identifier (e.g. ``"2024_hurricane_helene"``).
    db_conn_id:
        Airflow connection ID pointing to the PostGIS warehouse.
        The connection extras must supply ``db_name``, ``user``, and ``password``.
    """

    template_fields = ("event_id",)
    ui_color = "#4e9fd1"

    def __init__(self, *, event_id: str, db_conn_id: str = "noaa_postgres", **kwargs) -> None:
        super().__init__(**kwargs)
        self.event_id = event_id
        self.db_conn_id = db_conn_id

    def execute(self, context: Context) -> int:
        # Import here so Airflow workers only need the package installed, not at parse time.
        from airflow.hooks.base import BaseHook
        from sqlalchemy import create_engine

        from noaa_etl.extract.noaa_client import NOAAClient
        from noaa_etl.load.warehouse import load_acquisitions
        from noaa_etl.transform.metadata import transform

        conn = BaseHook.get_connection(self.db_conn_id)
        db_url = (
            f"postgresql+psycopg2://{conn.login}:{conn.password}"
            f"@{conn.host}:{conn.port}/{conn.schema}"
        )
        engine = create_engine(db_url, pool_pre_ping=True)

        self.log.info("Ingesting event %s", self.event_id)
        client = NOAAClient()
        raw = client.fetch_all_acquisitions(self.event_id)
        rows = transform(raw)
        loaded = load_acquisitions(rows, engine)
        self.log.info("Loaded %d rows for event %s", loaded, self.event_id)
        return loaded
