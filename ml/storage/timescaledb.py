"""TimescaleDB storage service for forecast persistence."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
import psycopg
from psycopg.rows import dict_row

from ml.utils.config import settings

LOGGER = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS solar_power_predictions (
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    predicted_power_kw DOUBLE PRECISION NOT NULL,
    baseline_power_kw DOUBLE PRECISION NOT NULL,
    model_power_kw DOUBLE PRECISION NOT NULL,
    global_horizontal_irradiance DOUBLE PRECISION NOT NULL,
    diffuse_horizontal_irradiance DOUBLE PRECISION NOT NULL DEFAULT 0,
    global_tilted_irradiance DOUBLE PRECISION NOT NULL,
    temperature_2m DOUBLE PRECISION NOT NULL,
    wind_speed_10m DOUBLE PRECISION NOT NULL,
    cloud_cover DOUBLE PRECISION NOT NULL,
    humidity DOUBLE PRECISION NOT NULL,
    pressure DOUBLE PRECISION NOT NULL,
    generation_type TEXT NOT NULL,
    solar_data_source TEXT NOT NULL,
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (timestamp, latitude, longitude)
);
"""

ALTER_TABLE_SQL = """
ALTER TABLE solar_power_predictions
ADD COLUMN IF NOT EXISTS diffuse_horizontal_irradiance DOUBLE PRECISION NOT NULL DEFAULT 0;
"""

CREATE_HYPERTABLE_SQL = """
SELECT create_hypertable(
    'solar_power_predictions',
    'timestamp',
    if_not_exists => TRUE
);
"""

UPSERT_SQL = """
INSERT INTO solar_power_predictions (
    timestamp,
    latitude,
    longitude,
    predicted_power_kw,
    baseline_power_kw,
    model_power_kw,
    global_horizontal_irradiance,
    diffuse_horizontal_irradiance,
    global_tilted_irradiance,
    temperature_2m,
    wind_speed_10m,
    cloud_cover,
    humidity,
    pressure,
    generation_type,
    solar_data_source,
    model_name
) VALUES (
    %(timestamp)s,
    %(latitude)s,
    %(longitude)s,
    %(predicted_power_kw)s,
    %(baseline_power_kw)s,
    %(model_power_kw)s,
    %(global_horizontal_irradiance)s,
    %(diffuse_horizontal_irradiance)s,
    %(global_tilted_irradiance)s,
    %(temperature_2m)s,
    %(wind_speed_10m)s,
    %(cloud_cover)s,
    %(humidity)s,
    %(pressure)s,
    %(generation_type)s,
    %(solar_data_source)s,
    %(model_name)s
) ON CONFLICT (timestamp, latitude, longitude) DO UPDATE SET
    predicted_power_kw = EXCLUDED.predicted_power_kw,
    baseline_power_kw = EXCLUDED.baseline_power_kw,
    model_power_kw = EXCLUDED.model_power_kw,
    global_horizontal_irradiance = EXCLUDED.global_horizontal_irradiance,
    diffuse_horizontal_irradiance = EXCLUDED.diffuse_horizontal_irradiance,
    global_tilted_irradiance = EXCLUDED.global_tilted_irradiance,
    temperature_2m = EXCLUDED.temperature_2m,
    wind_speed_10m = EXCLUDED.wind_speed_10m,
    cloud_cover = EXCLUDED.cloud_cover,
    humidity = EXCLUDED.humidity,
    pressure = EXCLUDED.pressure,
    generation_type = EXCLUDED.generation_type,
    solar_data_source = EXCLUDED.solar_data_source,
    model_name = EXCLUDED.model_name,
    created_at = NOW();
"""


class TimescaleDBService:
    """Encapsulate schema setup and forecast persistence."""

    def __init__(self) -> None:
        """Create a lazy database service."""

        self._connection: psycopg.Connection | None = None

    def _connect(self) -> psycopg.Connection:
        """Return a fresh autocommit connection for one operation."""

        return psycopg.connect(settings.postgres_dsn, autocommit=True)

    def initialise(self) -> None:
        """Ensure the required schema objects exist."""

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
                cursor.execute(CREATE_TABLE_SQL)
                cursor.execute(ALTER_TABLE_SQL)
                cursor.execute(CREATE_HYPERTABLE_SQL)
        LOGGER.info("TimescaleDB schema initialised")

    def close(self) -> None:
        """Close the open database connection if one exists."""

        if self._connection is not None and not self._connection.closed:
            self._connection.close()

    def health_check(self) -> bool:
        """Check whether the database is reachable."""

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1;")
                    cursor.fetchone()
            return True
        except Exception:
            LOGGER.exception("TimescaleDB health check failed")
            return False

    def upsert_predictions(self, prediction_frame: pd.DataFrame) -> int:
        """Upsert forecast rows into TimescaleDB."""

        if prediction_frame.empty:
            return 0

        payload = []
        for _, row in prediction_frame.iterrows():
            payload.append(
                {
                    "timestamp": pd.Timestamp(row["timestamp"]).to_pydatetime(),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "predicted_power_kw": float(row["predicted_power_kw"]),
                    "baseline_power_kw": float(row["baseline_power_kw"]),
                    "model_power_kw": float(row["model_power_kw"]),
                    "global_horizontal_irradiance": float(row["global_horizontal_irradiance"]),
                    "diffuse_horizontal_irradiance": float(row["diffuse_horizontal_irradiance"]),
                    "global_tilted_irradiance": float(row["global_tilted_irradiance"]),
                    "temperature_2m": float(row["temperature_2m"]),
                    "wind_speed_10m": float(row["wind_speed_10m"]),
                    "cloud_cover": float(row["cloud_cover"]),
                    "humidity": float(row["humidity"]),
                    "pressure": float(row["pressure"]),
                    "generation_type": str(row["generation_type"]),
                    "solar_data_source": str(row["solar_data_source"]),
                    "model_name": str(row["model_name"]),
                }
            )

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(UPSERT_SQL, payload)
        LOGGER.info("Upserted %s forecast rows", len(payload))
        return len(payload)

    def delete_predictions(self, latitude: float, longitude: float) -> int:
        """Delete all stored rows for one site."""

        sql = """
            DELETE FROM solar_power_predictions
            WHERE latitude = %(latitude)s
              AND longitude = %(longitude)s;
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, {"latitude": latitude, "longitude": longitude})
                deleted = cursor.rowcount or 0
        LOGGER.info("Deleted %s forecast rows for %s, %s", deleted, latitude, longitude)
        return deleted

    def fetch_predictions(self, latitude: float, longitude: float, hours: int) -> list[dict[str, object]]:
        """Read recent predictions for a coordinate."""

        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        sql = """
            SELECT
                timestamp,
                created_at,
                latitude,
                longitude,
                predicted_power_kw,
                baseline_power_kw,
                model_power_kw,
                global_horizontal_irradiance,
                diffuse_horizontal_irradiance,
                global_tilted_irradiance,
                temperature_2m,
                wind_speed_10m,
                cloud_cover,
                humidity,
                pressure,
                generation_type,
                solar_data_source,
                model_name
            FROM solar_power_predictions
            WHERE latitude = %(latitude)s
              AND longitude = %(longitude)s
              AND timestamp >= %(start_time)s
            ORDER BY timestamp ASC;
        """
        with self._connect() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    sql,
                    {
                        "latitude": latitude,
                        "longitude": longitude,
                        "start_time": start_time,
                    },
                )
                rows = cursor.fetchall()
        return list(rows)


timescaledb_service = TimescaleDBService()
