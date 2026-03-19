"""Configuration helpers for the backend services."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    postgres_dsn: str = os.getenv(
        "POSTGRES_DSN",
        "postgresql://solar:solar123@127.0.0.1:5432/solar",
    )
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://127.0.0.1:5174").split(",")
        if origin.strip()
    )


settings = Settings()
