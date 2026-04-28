"""ML feature export endpoint — stream mart_ml_features rows for model training."""

from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.auth import require_api_key
from api.db import get_db
from api.models.schemas import MLExportResponse, MLFeatureRow

router = APIRouter(prefix="/features", tags=["ml-features"])

_FEATURE_COLS = """
    acquisition_id, event_name, acquisition_date, sensor, resolution_cm,
    footprint_area_km2, centroid_lon, centroid_lat,
    bbox_west, bbox_south, bbox_east, bbox_north,
    bbox_width_deg, bbox_height_deg,
    acquisition_year, acquisition_month, day_of_year, day_of_week,
    event_avg_resolution_cm, event_daily_area_km2, event_cumulative_count,
    resolution_delta_cm, area_rank_in_event_day
"""


@router.get("", response_model=MLExportResponse)
def export_features(
    event_name: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(10_000, ge=1, le=100_000),
    _key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> MLExportResponse:
    """Return ML features as JSON. For large exports use /features/parquet."""
    clauses = ["1=1"]
    params: dict = {"limit": limit}
    if event_name:
        clauses.append("event_name = :event_name")
        params["event_name"] = event_name
    if date_from:
        clauses.append("acquisition_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("acquisition_date <= :date_to")
        params["date_to"] = date_to

    where = " AND ".join(clauses)
    rows = db.execute(
        text(f"SELECT {_FEATURE_COLS} FROM marts.mart_ml_features WHERE {where} LIMIT :limit"),
        params,
    ).mappings().all()

    results = [MLFeatureRow(**dict(r)) for r in rows]
    return MLExportResponse(
        event_name=event_name,
        date_from=date_from,
        date_to=date_to,
        row_count=len(results),
        rows=results,
    )


@router.get("/parquet")
def export_features_parquet(
    event_name: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    _key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> Response:
    """Stream mart_ml_features as a Parquet file (binary download)."""
    try:
        import pandas as pd  # noqa: PLC0415
    except ImportError:
        return Response(
            content='{"detail": "pandas not installed on server"}',
            media_type="application/json",
            status_code=500,
        )

    clauses = ["1=1"]
    params: dict = {}
    if event_name:
        clauses.append("event_name = :event_name")
        params["event_name"] = event_name
    if date_from:
        clauses.append("acquisition_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("acquisition_date <= :date_to")
        params["date_to"] = date_to

    where = " AND ".join(clauses)
    result = db.execute(
        text(f"SELECT {_FEATURE_COLS} FROM marts.mart_ml_features WHERE {where}"),
        params,
    )
    df = pd.DataFrame(result.mappings().all())

    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    buf.seek(0)

    filename = f"ml_features_{event_name or 'all'}.parquet"
    return Response(
        content=buf.read(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
