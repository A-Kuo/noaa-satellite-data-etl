"""Coverage statistics endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.auth import require_api_key
from api.db import get_db
from api.models.schemas import CoverageStatOut

router = APIRouter(prefix="/coverage", tags=["coverage"])


@router.get("", response_model=list[CoverageStatOut])
def list_coverage(
    event_name: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    _key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> list[CoverageStatOut]:
    clauses = ["1=1"]
    params: dict = {"limit": limit}

    if event_name:
        clauses.append("event_name = :event_name")
        params["event_name"] = event_name
    if date_from:
        clauses.append("stat_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("stat_date <= :date_to")
        params["date_to"] = date_to

    where = " AND ".join(clauses)
    rows = db.execute(
        text(f"""
            SELECT event_name, stat_date, acquisition_count,
                   avg_resolution_cm, total_area_km2, cumulative_acquisitions
            FROM marts.coverage_statistics
            WHERE {where}
            ORDER BY event_name, stat_date DESC
            LIMIT :limit
        """),
        params,
    ).mappings().all()

    return [CoverageStatOut(**dict(r)) for r in rows]


@router.get("/summary", response_model=list[dict])
def coverage_summary(
    _key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Per-event totals across all time."""
    rows = db.execute(text("""
        SELECT
            event_name,
            MIN(stat_date)             AS first_date,
            MAX(stat_date)             AS last_date,
            SUM(acquisition_count)     AS total_acquisitions,
            ROUND(AVG(avg_resolution_cm)::NUMERIC, 2) AS overall_avg_resolution_cm,
            ROUND(SUM(total_area_km2)::NUMERIC, 2)    AS total_area_km2
        FROM marts.coverage_statistics
        GROUP BY event_name
        ORDER BY total_acquisitions DESC
    """)).mappings().all()

    return [dict(r) for r in rows]
