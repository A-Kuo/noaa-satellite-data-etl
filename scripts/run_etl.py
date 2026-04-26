#!/usr/bin/env python3
"""Convenience wrapper: run a full ingest for one or more NOAA event IDs.

Usage:
    python scripts/run_etl.py <event_id> [<event_id> ...]

Or via the installed CLI:
    noaa-etl ingest <event_id>
"""

import sys
from pathlib import Path

# Allow running without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import structlog

from noaa_etl.extract.noaa_client import NOAAClient
from noaa_etl.load.warehouse import get_engine, load_acquisitions
from noaa_etl.transform.metadata import transform

log = structlog.get_logger()


def run(event_ids: list[str]) -> None:
    client = NOAAClient()
    engine = get_engine()
    total = 0

    for event_id in event_ids:
        log.info("ingesting event", event_id=event_id)
        raw = client.fetch_all_acquisitions(event_id)
        rows = transform(raw)
        loaded = load_acquisitions(rows, engine)
        total += loaded
        log.info("event complete", event_id=event_id, loaded=loaded)

    log.info("pipeline finished", total_loaded=total)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    run(sys.argv[1:])
