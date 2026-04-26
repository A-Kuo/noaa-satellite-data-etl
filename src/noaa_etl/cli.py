"""CLI entry point for the NOAA ETL pipeline."""

from __future__ import annotations

import click
import structlog

from noaa_etl.config import settings
from noaa_etl.extract.noaa_client import NOAAClient
from noaa_etl.load.warehouse import get_engine, load_acquisitions
from noaa_etl.transform.metadata import transform

log = structlog.get_logger(__name__)


@click.group()
@click.option("--log-level", default=settings.log_level, show_default=True)
def main(log_level: str) -> None:
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(
        __import__("logging").getLevelName(log_level.upper())
    ))


@main.command()
@click.argument("event_id")
def ingest(event_id: str) -> None:
    """Fetch all acquisitions for EVENT_ID and load them into the warehouse."""
    client = NOAAClient()
    engine = get_engine()

    log.info("starting ingestion", event_id=event_id)
    raw = client.fetch_all_acquisitions(event_id)
    rows = transform(raw)
    loaded = load_acquisitions(rows, engine)
    log.info("ingestion complete", event_id=event_id, loaded=loaded)


@main.command("list-events")
def list_events() -> None:
    """Print all available NOAA events."""
    client = NOAAClient()
    events = client.list_events()
    for evt in events:
        click.echo(f"{evt.get('id')}\t{evt.get('name')}")
