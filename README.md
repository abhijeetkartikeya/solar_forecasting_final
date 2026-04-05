# Solar Forecasting Gateway

A full-stack solar energy monitoring and forecasting platform built for Tata Power solar assets across India. Features an interactive map-based React frontend, a FastAPI backend with ML-driven solar power predictions, TimescaleDB for time-series storage, and Grafana dashboards for real-time visualization.

## Features

- **Interactive India Solar Map** - Click any solar plant on the Leaflet map to instantly view its forecast dashboard in Grafana
- **3-Day Solar Power Forecasting** - ML pipeline predicts solar output using weather variables (GHI, cloud cover, temperature, wind speed)
- **Dual Data Pipeline** - Demo seeding for development + real V2 weather integration for production forecasts
- **TimescaleDB Storage** - Optimized time-series storage for predictions with upsert support
- **Grafana Dashboards** - Auto-provisioned dashboards with site-specific variables (lat/lon, time window)
- **Docker Compose Stack** - One-command deployment of the full infrastructure

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, Leaflet, ECharts, Tailwind CSS |
| Backend | FastAPI, Uvicorn, Pandas |
| Database | TimescaleDB (PostgreSQL) |
| Visualization | Grafana |
| ML | Physics-informed solar model with weather-driven predictions |
| Deployment | Docker Compose, PM2 (ecosystem.config.cjs) |

## Architecture

```
                    +------------------+
                    |  React Frontend  |
                    |  (Vite + Leaflet)|
                    +--------+---------+
                             |
                    Click plant marker
                             |
                             v
                    +------------------+        +------------------+
                    |   Grafana        |<-------| TimescaleDB      |
                    |   Dashboards     |        | solar_power_     |
                    +------------------+        | predictions      |
                             ^                  +--------+---------+
                             |                           ^
                    +--------+---------+                 |
                    |   FastAPI API    +-----------------+
                    |   /api/forecast  |
                    |   /api/predict   |
                    +--------+---------+
                             ^
                    +--------+---------+
                    | V2 Weather Data  |
                    | (Open-Meteo +    |
                    |  NASA POWER)     |
                    +------------------+
```

## Quick Start

### 1. Start Infrastructure

```bash
docker compose up -d
```

This launches:
- **TimescaleDB** on `localhost:5432`
- **Grafana** on `localhost:3000` (admin/admin)

### 2. Start the Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-backend.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Seed Demo Data

```bash
curl -X POST "http://127.0.0.1:8000/api/demo/seed-defaults?hours=240"
```

### 4. Start the Frontend

```bash
npm install
npm run dev
```

### 5. Open & Explore

Open `http://localhost:5173`, click any solar plant marker on the map - it redirects directly to the Grafana dashboard for that plant.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | API + database health check |
| `GET` | `/api/predictions?lat=&lon=&hours=` | Fetch predictions for a plant |
| `POST` | `/api/predictions/upsert` | Batch upsert forecast rows |
| `POST` | `/api/demo/seed?lat=&lon=&hours=` | Generate synthetic data for one site |
| `POST` | `/api/demo/seed-defaults?hours=` | Seed all default plant locations |
| `POST` | `/api/forecast/sync-v2?lat=&lon=` | Sync real weather + predict solar output |
| `POST` | `/api/forecast/sync-v2-defaults` | Sync all default sites from V2 pipeline |

## Project Structure

```
.
├── src/                          # React frontend
│   ├── App.jsx                   # Map + Grafana redirect logic
│   └── assets/
├── app/
│   └── main.py                   # FastAPI application
├── ml/
│   ├── services/
│   │   ├── solar_forecast.py     # V2 weather-driven solar prediction
│   │   └── demo_seed.py          # Synthetic data generator
│   ├── storage/
│   │   └── timescaledb.py        # TimescaleDB persistence layer
│   └── utils/
│       └── config.py             # Settings management
├── grafana/
│   ├── dashboards/               # Provisioned Grafana dashboards
│   └── provisioning/             # Datasource + dashboard provisioning
├── v2_data_integration.py        # Weather data fetcher (Open-Meteo + NASA)
├── docker-compose.yml            # TimescaleDB + Grafana stack
├── ecosystem.config.cjs          # PM2 process manager config
├── requirements-backend.txt      # Python dependencies
├── package.json                  # Node.js dependencies
└── .env.example                  # Environment variable template
```

## Environment Variables

Copy `.env.example` to `.env` to configure:

**Frontend:**
```env
VITE_GRAFANA_URL=http://127.0.0.1:3000
VITE_GRAFANA_DASHBOARD_PATH=/d/solar-energy-forecast/solar-energy-forecast
VITE_GRAFANA_WINDOW_HOURS=240
VITE_GRAFANA_FUTURE_HOURS=72
```

**Backend:**
```env
POSTGRES_DSN=postgresql://solar:solar123@127.0.0.1:5432/solar
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://127.0.0.1:5173,http://127.0.0.1:5174
```

## Default Solar Plant Sites

The system comes pre-configured with 7 solar plant locations across India:

| Latitude | Longitude | Region |
|----------|-----------|--------|
| 22.25 | 72.74 | Gujarat |
| 13.32 | 78.66 | Andhra Pradesh |
| 28.61 | 77.23 | Delhi NCR |
| 27.81 | 71.40 | Rajasthan |
| 14.16 | 77.18 | Karnataka |
| 24.54 | 81.36 | Madhya Pradesh |
| 23.94 | 72.41 | Gujarat |

## License

This project is proprietary. All rights reserved.
