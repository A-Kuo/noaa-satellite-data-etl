"""NOAA Emergency Response Imagery API client."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import requests
import structlog

from noaa_etl.config import settings

log = structlog.get_logger(__name__)


@dataclass
class AcquisitionRecord:
    """Raw acquisition metadata from the NOAA catalog."""

    acquisition_id: str
    event_name: str
    acquisition_date: date
    sensor: str
    resolution_cm: float
    bbox_west: float
    bbox_south: float
    bbox_east: float
    bbox_north: float
    download_url: str
    file_size_bytes: int | None = None
    crs: str = "EPSG:4326"
    extra: dict[str, Any] = field(default_factory=dict)


class NOAAClient:
    """Thin HTTP client for the NOAA Emergency Response Imagery catalog."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_events(self) -> list[dict[str, Any]]:
        """Return all storm/disaster events available in the catalog."""
        return self._get("/events")

    def list_acquisitions(
        self,
        event_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> list[AcquisitionRecord]:
        """Fetch one page of acquisition records for *event_id*."""
        raw = self._get(
            f"/events/{event_id}/acquisitions",
            params={"page": page, "page_size": page_size},
        )
        return [self._parse_acquisition(r) for r in raw.get("results", [])]

    def fetch_all_acquisitions(self, event_id: str) -> list[AcquisitionRecord]:
        """Paginate through every acquisition for *event_id*."""
        records: list[AcquisitionRecord] = []
        page = 1
        while True:
            batch = self.list_acquisitions(event_id, page=page, page_size=settings.batch_size)
            if not batch:
                break
            records.extend(batch)
            log.info("fetched acquisitions", event_id=event_id, page=page, count=len(batch))
            page += 1
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = settings.noaa_base_url.rstrip("/") + path
        for attempt in range(1, settings.noaa_max_retries + 1):
            try:
                resp = self._session.get(url, params=params, timeout=settings.noaa_request_timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                log.warning("request failed", url=url, attempt=attempt, error=str(exc))
                if attempt == settings.noaa_max_retries:
                    raise
                time.sleep(2**attempt)
        return {}  # unreachable

    @staticmethod
    def _parse_acquisition(raw: dict[str, Any]) -> AcquisitionRecord:
        bbox = raw.get("bbox", {})
        return AcquisitionRecord(
            acquisition_id=raw["id"],
            event_name=raw.get("event_name", ""),
            acquisition_date=date.fromisoformat(raw["acquisition_date"]),
            sensor=raw.get("sensor", "unknown"),
            resolution_cm=float(raw.get("resolution_cm", 0)),
            bbox_west=float(bbox.get("west", 0)),
            bbox_south=float(bbox.get("south", 0)),
            bbox_east=float(bbox.get("east", 0)),
            bbox_north=float(bbox.get("north", 0)),
            download_url=raw.get("download_url", ""),
            file_size_bytes=raw.get("file_size_bytes"),
            crs=raw.get("crs", "EPSG:4326"),
            extra={k: v for k, v in raw.items() if k not in {
                "id", "event_name", "acquisition_date", "sensor",
                "resolution_cm", "bbox", "download_url", "file_size_bytes", "crs",
            }},
        )
