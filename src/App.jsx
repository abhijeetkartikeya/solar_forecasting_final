import { useEffect, useMemo, useState } from 'react'
import { MapContainer, Marker, TileLayer, Tooltip } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const STORAGE_KEY = 'solar-plants-v1'
const grafanaBaseUrl = import.meta.env.VITE_GRAFANA_URL || 'http://127.0.0.1:3000'
const grafanaDashboardPath =
  import.meta.env.VITE_GRAFANA_DASHBOARD_PATH || '/d/solar-energy-forecast/solar-energy-forecast'
const grafanaOrgId = import.meta.env.VITE_GRAFANA_ORG_ID || '1'
const grafanaTheme = import.meta.env.VITE_GRAFANA_THEME || 'dark'
const grafanaKioskMode = import.meta.env.VITE_GRAFANA_KIOSK_MODE || 'tv'
const grafanaRefresh = import.meta.env.VITE_GRAFANA_REFRESH || '30s'
const grafanaWindowHours = import.meta.env.VITE_GRAFANA_WINDOW_HOURS || '240'
const grafanaFutureHours = import.meta.env.VITE_GRAFANA_FUTURE_HOURS || '72'

const defaultPlants = [
  {
    id: 'dhuaran2',
    name: 'Dhuaran2 (Gujarat)',
    region: 'West Grid',
    status: 'Healthy',
    lat: 22.25,
    lon: 72.74,
    capacity: 30,
    tilt: 25,
    azimuth: 180,
    availability: 99.2,
  },
  {
    id: 'punganur',
    name: 'Punganur (Andhra Pradesh)',
    region: 'South Grid',
    status: 'Healthy',
    lat: 13.32,
    lon: 78.66,
    capacity: 42,
    tilt: 22,
    azimuth: 175,
    availability: 98.8,
  },
  {
    id: 'delhi',
    name: 'Delhi Solar Plant',
    region: 'North Grid',
    status: 'Watch',
    lat: 28.61,
    lon: 77.23,
    capacity: 25,
    tilt: 20,
    azimuth: 185,
    availability: 97.6,
  },
  {
    id: 'bhadla',
    name: 'Bhadla Solar Park (Rajasthan)',
    region: 'North West Grid',
    status: 'Healthy',
    lat: 27.81,
    lon: 71.4,
    capacity: 100,
    tilt: 24,
    azimuth: 180,
    availability: 99.5,
  },
  {
    id: 'pavagada',
    name: 'Pavagada Solar Park (Karnataka)',
    region: 'South Grid',
    status: 'Healthy',
    lat: 14.16,
    lon: 77.18,
    capacity: 70,
    tilt: 22,
    azimuth: 178,
    availability: 99.1,
  },
  {
    id: 'rewa',
    name: 'Rewa Solar Park (Madhya Pradesh)',
    region: 'Central Grid',
    status: 'Healthy',
    lat: 24.54,
    lon: 81.36,
    capacity: 50,
    tilt: 23,
    azimuth: 180,
    availability: 98.9,
  },
  {
    id: 'charanka',
    name: 'Charanka Solar Park (Gujarat)',
    region: 'West Grid',
    status: 'Watch',
    lat: 23.94,
    lon: 72.41,
    capacity: 50,
    tilt: 22,
    azimuth: 180,
    availability: 97.9,
  },
]

const statusToneMap = {
  Healthy: 'emerald',
  Watch: 'amber',
  Critical: 'rose',
}

function getIcon() {
  return new L.Icon({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    iconSize: [25, 41],
  })
}

function buildGrafanaUrl(plant) {
  const normalizedBase = grafanaBaseUrl.endsWith('/')
    ? grafanaBaseUrl.slice(0, -1)
    : grafanaBaseUrl
  const normalizedPath = grafanaDashboardPath.startsWith('/')
    ? grafanaDashboardPath
    : `/${grafanaDashboardPath}`
  const url = new URL(`${normalizedBase}${normalizedPath}`)

  url.searchParams.set('orgId', grafanaOrgId)
  url.searchParams.set('theme', grafanaTheme)
  url.searchParams.set('refresh', grafanaRefresh)
  url.searchParams.set('kiosk', grafanaKioskMode)
  url.searchParams.set('from', `now-${grafanaWindowHours}h`)
  url.searchParams.set('to', `now+${grafanaFutureHours}h`)
  url.searchParams.set('var-plant', plant.name)
  url.searchParams.set('var-region', plant.region)
  url.searchParams.set('var-lat', String(plant.lat))
  url.searchParams.set('var-lon', String(plant.lon))
  url.searchParams.set('var-window', grafanaWindowHours)
  url.searchParams.set('var-capacity', String(plant.capacity))
  url.searchParams.set('var-status', plant.status)

  return url.toString()
}

function formatNumber(value) {
  return new Intl.NumberFormat('en-IN').format(value)
}

function getStatusClasses(status) {
  const tone = statusToneMap[status] || 'emerald'

  if (tone === 'amber') {
    return 'border-amber-400/30 bg-amber-400/10 text-amber-200'
  }

  if (tone === 'rose') {
    return 'border-rose-400/30 bg-rose-400/10 text-rose-200'
  }

  return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
}

function SummaryCard({ label, value, hint }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-4 backdrop-blur">
      <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-sm text-slate-400">{hint}</p>
    </div>
  )
}

function PlantRow({ plant, onSelect }) {
  return (
    <button
      onClick={() => onSelect(plant)}
      className="group w-full rounded-3xl border border-white/8 bg-white/[0.035] p-4 text-left transition hover:-translate-y-0.5 hover:border-sky-400/40 hover:bg-slate-800/70"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-base font-semibold text-white">{plant.name}</p>
          <p className="mt-1 text-sm text-slate-400">
            {plant.region} • {plant.lat.toFixed(2)}, {plant.lon.toFixed(2)}
          </p>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${getStatusClasses(plant.status)}`}>
          {plant.status}
        </span>
      </div>
      <div className="mt-4 flex items-center justify-between text-sm">
        <div className="text-slate-300">{plant.capacity} MW installed</div>
        <div className="text-slate-400">Availability {plant.availability}%</div>
      </div>
    </button>
  )
}

function App() {
  const [plants, setPlants] = useState(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY)

    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed
        }
      } catch (error) {
        console.error(error)
      }
    }

    return defaultPlants
  })
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({
    name: '',
    region: '',
    status: 'Healthy',
    lat: '',
    lon: '',
    capacity: '',
    tilt: '',
    azimuth: '',
    availability: '',
  })

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(plants))
  }, [plants])

  const totals = useMemo(() => {
    const capacity = plants.reduce((sum, plant) => sum + plant.capacity, 0)
    const healthy = plants.filter((plant) => plant.status === 'Healthy').length
    const averageAvailability = plants.reduce((sum, plant) => sum + (plant.availability || 0), 0) / plants.length

    return {
      capacity,
      healthy,
      averageAvailability: averageAvailability.toFixed(1),
    }
  }, [plants])

  const handleSubmit = (event) => {
    event.preventDefault()

    const lat = Number(form.lat)
    const lon = Number(form.lon)
    const capacity = Number(form.capacity)
    const tilt = Number(form.tilt)
    const azimuth = Number(form.azimuth)
    const availability = Number(form.availability)

    if (!form.name || !form.region || Number.isNaN(lat) || Number.isNaN(lon) || Number.isNaN(capacity)) {
      return
    }

    const next = {
      id: `${form.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${Date.now()}`,
      name: form.name,
      region: form.region,
      status: form.status || 'Healthy',
      lat,
      lon,
      capacity,
      tilt: tilt || 22,
      azimuth: azimuth || 180,
      availability: Number.isNaN(availability) ? 98.5 : availability,
    }

    setPlants((prev) => [next, ...prev])
    setForm({
      name: '',
      region: '',
      status: 'Healthy',
      lat: '',
      lon: '',
      capacity: '',
      tilt: '',
      azimuth: '',
      availability: '',
    })
    setShowAdd(false)
  }

  const openPlantDashboard = (plant) => {
    window.location.assign(buildGrafanaUrl(plant))
  }

  return (
    <div className="min-h-screen bg-[#07111f] text-slate-100">
      <div className="mx-auto max-w-[1600px] px-4 py-5 md:px-6 md:py-6">
        <section className="dashboard-panel relative overflow-hidden rounded-[34px] p-5 md:p-7">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.18),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.14),transparent_24%)]" />
          <div className="relative grid gap-6 xl:grid-cols-[1.25fr_0.75fr] xl:items-end">
            <div>
              <p className="text-[11px] uppercase tracking-[0.35em] text-sky-300">Tata Power Solar Command</p>
              <h1 className="mt-3 max-w-4xl text-3xl font-semibold tracking-tight text-white md:text-5xl">
                Solar Monitoring Gateway for Site-to-Grafana Operations
              </h1>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300 md:text-base">
                A clean command surface for plant discovery, location selection, and direct transition into the live
                Grafana operational dashboard. The map stays lightweight while the second page becomes the real
                monitoring environment.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
              <SummaryCard label="Portfolio Capacity" value={`${formatNumber(totals.capacity)} MW`} hint="Across mapped solar assets" />
              <SummaryCard label="Healthy Sites" value={`${totals.healthy}/${plants.length}`} hint="Sites in normal operating state" />
              <SummaryCard label="Avg Availability" value={`${totals.averageAvailability}%`} hint="Current readiness benchmark" />
            </div>
          </div>
        </section>

        <section className="mt-5 grid gap-4 xl:grid-cols-[360px_1fr]">
          <aside className="dashboard-panel rounded-[30px] p-5 md:p-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">Asset Registry</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Plant Directory</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Choose a site from the list or map to open the live Grafana dashboard for that asset.
                </p>
              </div>
              <button
                onClick={() => setShowAdd((value) => !value)}
                className="rounded-full bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
              >
                {showAdd ? 'Close' : 'Add Site'}
              </button>
            </div>

            {showAdd && (
              <form onSubmit={handleSubmit} className="mt-5 grid gap-3 rounded-[28px] border border-white/10 bg-white/[0.04] p-4">
                <input
                  value={form.name}
                  onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                  placeholder="Plant Name"
                  className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-400/50"
                  required
                />
                <input
                  value={form.region}
                  onChange={(event) => setForm((prev) => ({ ...prev, region: event.target.value }))}
                  placeholder="Operational Region"
                  className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-400/50"
                  required
                />
                <select
                  value={form.status}
                  onChange={(event) => setForm((prev) => ({ ...prev, status: event.target.value }))}
                  className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-400/50"
                >
                  <option>Healthy</option>
                  <option>Watch</option>
                  <option>Critical</option>
                </select>
                <input
                  value={form.lat}
                  onChange={(event) => setForm((prev) => ({ ...prev, lat: event.target.value }))}
                  placeholder="Latitude"
                  type="number"
                  step="0.0001"
                  className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-400/50"
                  required
                />
                <input
                  value={form.lon}
                  onChange={(event) => setForm((prev) => ({ ...prev, lon: event.target.value }))}
                  placeholder="Longitude"
                  type="number"
                  step="0.0001"
                  className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-400/50"
                  required
                />
                <input
                  value={form.capacity}
                  onChange={(event) => setForm((prev) => ({ ...prev, capacity: event.target.value }))}
                  placeholder="Installed Capacity (MW)"
                  type="number"
                  step="0.1"
                  className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-400/50"
                  required
                />
                <input
                  value={form.availability}
                  onChange={(event) => setForm((prev) => ({ ...prev, availability: event.target.value }))}
                  placeholder="Availability (%)"
                  type="number"
                  step="0.1"
                  className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-400/50"
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <input
                    value={form.tilt}
                    onChange={(event) => setForm((prev) => ({ ...prev, tilt: event.target.value }))}
                    placeholder="Tilt Angle"
                    type="number"
                    className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-400/50"
                  />
                  <input
                    value={form.azimuth}
                    onChange={(event) => setForm((prev) => ({ ...prev, azimuth: event.target.value }))}
                    placeholder="Azimuth"
                    type="number"
                    className="rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-400/50"
                  />
                </div>
                <button
                  type="submit"
                  className="rounded-full bg-emerald-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300"
                >
                  Save Site
                </button>
              </form>
            )}

            <div className="mt-5 space-y-3">
              {plants.map((plant) => (
                <PlantRow key={plant.id} plant={plant} onSelect={openPlantDashboard} />
              ))}
            </div>
          </aside>

          <div className="dashboard-panel rounded-[30px] p-3 md:p-4">
            <div className="flex flex-col gap-3 border-b border-white/10 px-3 py-3 md:flex-row md:items-end md:justify-between md:px-4">
              <div>
                <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">Geo Operations View</p>
                <h2 className="mt-1 text-2xl font-semibold text-white">Interactive Solar Asset Map</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  The map remains the lightweight first screen. Clicking a marker opens the real Grafana experience.
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">{plants.length} mapped sites</span>
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">India portfolio view</span>
              </div>
            </div>

            <div className="map-wrap p-3 md:p-4">
              <MapContainer center={[22.0, 78.0]} zoom={5} className="h-[720px] w-full rounded-[26px] border border-white/10">
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>, OSM'
                />
                {plants.map((plant) => (
                  <Marker
                    key={plant.id}
                    position={[plant.lat, plant.lon]}
                    icon={getIcon()}
                    eventHandlers={{ click: () => openPlantDashboard(plant) }}
                  >
                    <Tooltip direction="top" offset={[0, -10]} opacity={0.95} permanent={false}>
                      <div className="space-y-1 text-xs">
                        <div className="font-semibold">{plant.name}</div>
                        <div>{plant.region}</div>
                        <div>{plant.capacity} MW</div>
                      </div>
                    </Tooltip>
                  </Marker>
                ))}
              </MapContainer>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

export default App
