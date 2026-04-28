"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from api.routes import acquisitions, coverage, features, spatial

app = FastAPI(
    title="NOAA Satellite ETL API",
    description="Query and export NOAA Emergency Response Imagery metadata from the PostGIS warehouse.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Prometheus metrics at /metrics
Instrumentator().instrument(app).expose(app)

app.include_router(acquisitions.router)
app.include_router(coverage.router)
app.include_router(spatial.router)
app.include_router(features.router)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}
