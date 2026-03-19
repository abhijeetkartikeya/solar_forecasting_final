"""Synthetic forecast generation for local demos and dashboard seeding."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pandas as pd


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _site_modifiers(latitude: float, longitude: float) -> dict[str, float]:
    """Create deterministic site-specific variation from coordinates."""

    lat_norm = abs(latitude) / 30
    lon_norm = abs(longitude) / 90
    phase = latitude * 0.21 + longitude * 0.11

    return {
        "sunrise_shift": (longitude - 75) / 24,
        "capacity_bias": 0.88 + lat_norm * 0.08 + (longitude % 7) * 0.01,
        "cloud_bias": 12 + lon_norm * 10 + (abs(latitude - longitude) % 5),
        "cloud_amp": 18 + lat_norm * 9,
        "temp_base": 25 + (30 - abs(latitude - 18)) * 0.08,
        "wind_base": 4.5 + (abs(longitude - 76) * 0.06),
        "humidity_base": 42 + lon_norm * 18,
        "pressure_base": 1007 + lat_norm * 4,
        "phase": phase,
    }


def generate_demo_prediction_frame(latitude: float, longitude: float, hours: int = 240) -> pd.DataFrame:
    """Generate realistic, plant-specific 15-minute solar and weather series."""

    site = _site_modifiers(latitude=latitude, longitude=longitude)
    periods = max(1, int(hours * 4))
    end_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(minutes=15 * (periods - 1))
    timestamps = pd.date_range(start=start_time, periods=periods, freq="15min", tz="UTC")

    rows: list[dict[str, object]] = []
    for index, ts in enumerate(timestamps):
        hour = ts.hour + ts.minute / 60
        shifted_hour = hour - site["sunrise_shift"]

        if 5.0 <= shifted_hour <= 18.8:
            day_wave = max(0.0, math.sin(math.pi * ((shifted_hour - 5.0) / 13.8)))
        else:
            day_wave = 0.0

        synoptic_wave = math.sin(index / 19 + site["phase"])
        local_wave = math.cos(index / 11 + site["phase"] * 0.7)
        cloud_cover = _clamp(
            site["cloud_bias"] + site["cloud_amp"] * synoptic_wave + 14 * local_wave + 40 * (1 - day_wave),
            2,
            100,
        )

        clearness = _clamp(1 - cloud_cover / 120, 0.0, 1.0)
        ghi = round(980 * day_wave * clearness * (0.92 + 0.08 * math.cos(index / 37 + site["phase"])), 2)
        dhi = round(_clamp(ghi * (0.16 + cloud_cover / 150), 0, max(ghi * 0.92, 0)), 2)
        gti = round(max(0.0, ghi * (0.74 + 0.08 * math.sin(index / 23 + latitude * 0.09))), 2)

        baseline_power = round(site["capacity_bias"] * 2.4 * day_wave, 3)
        model_power = round(max(0.0, baseline_power * (0.84 + clearness * 0.3 + 0.03 * math.sin(index / 14))), 3)
        predicted_power = round(
            max(
                0.0,
                model_power * (0.72 + clearness * 0.24)
                + baseline_power * 0.18
                - (cloud_cover / 180) * 0.25,
            ),
            3,
        )

        temperature = round(
            site["temp_base"]
            + 5.2 * math.sin(((shifted_hour - 9) / 24) * math.pi * 2)
            + 2.4 * synoptic_wave
            + 1.1 * local_wave,
            2,
        )
        wind_speed = round(
            _clamp(site["wind_base"] + 2.8 * math.cos(index / 8 + site["phase"]) + 1.9 * synoptic_wave, 0.4, 18),
            2,
        )
        humidity = round(
            _clamp(site["humidity_base"] + 18 * math.cos(index / 17 + site["phase"] * 0.5) - 16 * day_wave, 15, 98),
            2,
        )
        pressure = round(
            site["pressure_base"] + 3.4 * math.sin(index / 29 + site["phase"]) + 1.3 * math.cos(index / 47),
            2,
        )

        rows.append(
            {
                "timestamp": ts.to_pydatetime(),
                "latitude": latitude,
                "longitude": longitude,
                "predicted_power_kw": predicted_power,
                "baseline_power_kw": baseline_power,
                "model_power_kw": model_power,
                "global_horizontal_irradiance": ghi,
                "diffuse_horizontal_irradiance": dhi,
                "global_tilted_irradiance": gti,
                "temperature_2m": temperature,
                "wind_speed_10m": wind_speed,
                "cloud_cover": round(cloud_cover, 2),
                "humidity": humidity,
                "pressure": pressure,
                "generation_type": "solar",
                "solar_data_source": "demo-seeded",
                "model_name": "demo-forecast-v2",
            }
        )

    return pd.DataFrame(rows)
