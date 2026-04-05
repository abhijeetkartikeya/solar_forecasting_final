"""FastAPI application for solar forecast persistence and demo seeding."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ml.services.demo_seed import generate_demo_prediction_frame
from ml.storage.timescaledb import timescaledb_service
from ml.utils.config import settings

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class PredictionRecord(BaseModel):
    """Single forecast row for upsert requests."""

    timestamp: str
    latitude: float
    longitude: float
    predicted_power_kw: float
    baseline_power_kw: float
    model_power_kw: float
    global_horizontal_irradiance: float
    diffuse_horizontal_irradiance: float
    global_tilted_irradiance: float
    temperature_2m: float
    wind_speed_10m: float
    cloud_cover: float
    humidity: float
    pressure: float
    generation_type: str = "solar"
    solar_data_source: str = "api"
    model_name: str = "manual-upsert"


class PredictionUpsertRequest(BaseModel):
    """Batch upsert payload."""

    rows: list[PredictionRecord] = Field(default_factory=list)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialise storage on startup and close connections on shutdown."""

    timescaledb_service.initialise()
    yield
    timescaledb_service.close()


app = FastAPI(
    title="Solar Forecast API",
    description="FastAPI service for TimescaleDB-backed solar forecast storage and demo seeding.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Return API and database health state."""

    database_ok = timescaledb_service.health_check()
    return {"status": "ok" if database_ok else "degraded", "database": database_ok}


@app.get("/api/predictions")
def get_predictions(
    lat: float = Query(..., alias="lat"),
    lon: float = Query(..., alias="lon"),
    hours: int = Query(240, ge=1, le=24 * 90),
) -> dict[str, Any]:
    """Fetch recent predictions for a plant coordinate."""

    rows = timescaledb_service.fetch_predictions(latitude=lat, longitude=lon, hours=hours)
    return {"count": len(rows), "rows": rows}


@app.post("/api/predictions/upsert")
def upsert_predictions(payload: PredictionUpsertRequest) -> dict[str, Any]:
    """Upsert explicit forecast rows from an API payload."""

    if not payload.rows:
        raise HTTPException(status_code=400, detail="rows must not be empty")

    frame = pd.DataFrame(row.model_dump() for row in payload.rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    inserted = timescaledb_service.upsert_predictions(frame)
    return {"upserted": inserted}


@app.post("/api/demo/seed")
def seed_demo_predictions(
    lat: float = Query(..., alias="lat"),
    lon: float = Query(..., alias="lon"),
    hours: int = Query(240, ge=24, le=24 * 90),
) -> dict[str, Any]:
    """Generate and store synthetic series for one coordinate."""

    deleted = timescaledb_service.delete_predictions(latitude=lat, longitude=lon)
    frame = generate_demo_prediction_frame(latitude=lat, longitude=lon, hours=hours)
    inserted = timescaledb_service.upsert_predictions(frame)
    return {"deleted": deleted, "seeded": inserted, "lat": lat, "lon": lon, "hours": hours}


@app.post("/api/demo/seed-defaults")
def seed_default_sites(hours: int = Query(240, ge=24, le=24 * 90)) -> dict[str, Any]:
    """Seed the default frontend plant coordinates with demo data."""

    default_sites = [
        (22.25, 72.74),
        (13.32, 78.66),
        (28.61, 77.23),
        (27.81, 71.40),
        (14.16, 77.18),
        (24.54, 81.36),
        (23.94, 72.41),
    ]
    total = 0
    deleted_total = 0
    for latitude, longitude in default_sites:
        deleted_total += timescaledb_service.delete_predictions(latitude=latitude, longitude=longitude)
        frame = generate_demo_prediction_frame(latitude=latitude, longitude=longitude, hours=hours)
        total += timescaledb_service.upsert_predictions(frame)

    LOGGER.info("Seeded %s demo rows across default plants", total)
    return {"deleted": deleted_total, "seeded": total, "sites": len(default_sites), "hours": hours}


# --- NEW FORECASTING ENDPOINTS TO USE V2 PIPELINE DATA ---

from ml.services.solar_forecast import generate_solar_prediction_frame

@app.post("/api/forecast/sync-v2")
def sync_v2_forecast(
    lat: float = Query(..., alias="lat"),
    lon: float = Query(..., alias="lon")
) -> dict[str, Any]:
    """Sync real 3-day weather from V2, predict solar output, and cache locally."""
    deleted = timescaledb_service.delete_predictions(latitude=lat, longitude=lon)
    frame = generate_solar_prediction_frame(latitude=lat, longitude=lon)
    inserted = timescaledb_service.upsert_predictions(frame) if not frame.empty else 0
    return {"deleted": deleted, "upserted": inserted, "lat": lat, "lon": lon}


@app.post("/api/forecast/sync-v2-defaults")
def sync_v2_default_sites() -> dict[str, Any]:
    """Seed the default frontend plant coordinates cleanly drawing 3 days ahead from V2."""
    default_sites = [
        (22.25, 72.74),
        (13.32, 78.66),
        (28.61, 77.23),
        (27.81, 71.40),
        (14.16, 77.18),
        (24.54, 81.36),
        (23.94, 72.41),
    ]
    total = 0
    deleted_total = 0
    for latitude, longitude in default_sites:
        deleted_total += timescaledb_service.delete_predictions(latitude=latitude, longitude=longitude)
        frame = generate_solar_prediction_frame(latitude=latitude, longitude=longitude)
        total += timescaledb_service.upsert_predictions(frame) if not frame.empty else 0

    LOGGER.info("Synced %s 3-day future solar rows across default plants from V2", total)
    return {"deleted": deleted_total, "upserted": total, "sites": len(default_sites)}
