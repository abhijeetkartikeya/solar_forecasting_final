# Tata Power Solar Monitoring Gateway

This repo now includes the whole local stack:

- React frontend with the India solar asset map
- direct same-tab redirect from plant click to Grafana
- FastAPI backend for forecast persistence and demo seeding
- TimescaleDB storage for `solar_power_predictions`
- Grafana datasource + starter dashboard provisioning

There is no in-app dashboard wrapper anymore. Clicking a site sends the browser directly to Grafana.

## Frontend

```bash
npm install
npm run dev
```

Vite will run on `http://127.0.0.1:5173` or the next open port.

## Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-backend.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API endpoints:

- `GET /api/health`
- `GET /api/predictions?lat=22.25&lon=72.74&hours=240`
- `POST /api/predictions/upsert`
- `POST /api/demo/seed?lat=22.25&lon=72.74&hours=240`
- `POST /api/demo/seed-defaults?hours=240`

## Docker Stack

Start TimescaleDB and Grafana:

```bash
docker compose up -d
```

Services:

- Grafana: `http://127.0.0.1:3000`
- TimescaleDB: `127.0.0.1:5432`

Default Grafana login:

- user: `admin`
- password: `admin`

Grafana is provisioned with:

- datasource: `TimescaleDB`
- dashboard UID: `solar-energy-forecast`
- dashboard path: `/d/solar-energy-forecast/solar-energy-forecast`
- dashboard variables: `lat`, `lon`, `window`

## Quick Start End To End

1. Start Docker:

```bash
docker compose up -d
```

2. Start the backend:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

3. Seed demo data:

```bash
curl -X POST "http://127.0.0.1:8000/api/demo/seed-defaults?hours=240"
```

4. Start the frontend:

```bash
npm run dev
```

5. Open the frontend and click a map marker. It will redirect directly to the Grafana dashboard for that plant.

## Environment Variables

Copy `.env.example` to `.env` if you want to override defaults.

Frontend:

```env
VITE_GRAFANA_URL=http://127.0.0.1:3000
VITE_GRAFANA_DASHBOARD_PATH=/d/solar-energy-forecast/solar-energy-forecast
VITE_GRAFANA_ORG_ID=1
VITE_GRAFANA_THEME=dark
VITE_GRAFANA_KIOSK_MODE=tv
VITE_GRAFANA_REFRESH=30s
VITE_GRAFANA_WINDOW_HOURS=240
VITE_GRAFANA_FUTURE_HOURS=72
```

The frontend redirect sends these Grafana query params:

- `var-lat`
- `var-lon`
- `var-window`
- optional context vars like `var-plant`, `var-region`, `var-capacity`, `var-status`

It also forces the dashboard time range in the URL so Grafana opens on a predictable horizon instead of reusing the last browser-selected range:

- `from=now-${VITE_GRAFANA_WINDOW_HOURS}h`
- `to=now+${VITE_GRAFANA_FUTURE_HOURS}h`

Backend:

```env
POSTGRES_DSN=postgresql://solar:solar123@127.0.0.1:5432/solar
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://127.0.0.1:5173,http://127.0.0.1:5174
```

Grafana datasource overrides:

```env
GRAFANA_POSTGRES_URL=timescaledb:5432
GRAFANA_POSTGRES_USER=solar
GRAFANA_POSTGRES_PASSWORD=solar123
GRAFANA_POSTGRES_DB=solar
```

Use those only if Grafana needs to point at an existing Postgres or TimescaleDB instance instead of the local `timescaledb` service. For example, the currently running Grafana container is attached to the existing host database via `host.docker.internal:55432`.

## Key Files

- `src/App.jsx`: direct Grafana redirect from map/list clicks
- `app/main.py`: FastAPI API
- `ml/storage/timescaledb.py`: TimescaleDB persistence
- `ml/services/demo_seed.py`: synthetic dashboard seed data
- `grafana/dashboards/solar-energy-forecast.json`: starter Grafana dashboard
- `docker-compose.yml`: local Grafana + TimescaleDB stack
# solar_forecasting_final
