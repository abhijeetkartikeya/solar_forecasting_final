import os
from datetime import datetime
import pandas as pd
import psycopg
from psycopg.rows import dict_row

# Configuration manually pointing securely to the V2 Database instance
WEATHER_DB_DSN = os.getenv(
    "WEATHER_DB_DSN", 
    "postgresql://solar_ro_user:solar_ro_pass@127.0.0.1:5434/weather_ml_v2"
)

MERGED_WEATHER_SQL = """
WITH latest_forecasts AS (
    -- Get the most recent forecast issue for each future timestamp
    SELECT 
        forecast_time, lat, lon, MAX(issue_time) AS max_issue
    FROM weather_forecast
    WHERE forecast_type = 'provider'
      AND forecast_time >= NOW()
    GROUP BY forecast_time, lat, lon
)
-- 1. Historical & Real-Time Actuals
SELECT 
    time AS timestamp,
    lat, lon,
    temperature_2m,
    cloud_cover,
    wind_speed_10m,
    shortwave_radiation,
    diffuse_radiation,
    direct_normal_irradiance,
    'actual' AS data_source
FROM weather_observations
WHERE time < NOW()
  AND ABS(lat - %(lat)s) < 0.1 AND ABS(lon - %(lon)s) < 0.1

UNION ALL

-- 2. Future Forecasts (3 days ahead) seamlessly appended
SELECT 
    wf.forecast_time AS timestamp,
    wf.lat, wf.lon,
    wf.temperature_2m,
    wf.cloud_cover,
    wf.wind_speed_10m,
    wf.shortwave_radiation,
    wf.diffuse_radiation,
    wf.direct_normal_irradiance,
    'forecast_provider' AS data_source
FROM weather_forecast wf
JOIN latest_forecasts lf 
  ON wf.forecast_time = lf.forecast_time 
 AND wf.lat = lf.lat 
 AND wf.lon = lf.lon 
 AND wf.issue_time = lf.max_issue
WHERE wf.forecast_type = 'provider'
  AND ABS(wf.lat - %(lat)s) < 0.1 AND ABS(wf.lon - %(lon)s) < 0.1
ORDER BY timestamp ASC;
"""

def fetch_continuous_weather_dataset(lat: float, lon: float) -> pd.DataFrame:
    """
    Connects seamlessly (read-only) to the Version 2 Weather Prediction database.
    Returns a continuous 15-minute interval DataFrame blending past actuals into future forecasts.
    """
    try:
        # Utilizing the explicit readonly user to guarantee zero side-effects
        with psycopg.connect(WEATHER_DB_DSN) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(MERGED_WEATHER_SQL, {"lat": lat, "lon": lon})
                rows = cur.fetchall()
                
        df = pd.DataFrame(rows)
        
        # Ensure 15-minute consistency and deduplicate any overlapping edge cases
        if not df.empty:
            df.loc[:, 'timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df = df.drop_duplicates(subset=['timestamp', 'lat', 'lon'], keep='first')
            df = df.set_index('timestamp').resample('15min').asfreq().reset_index()
            
        return df
        
    except psycopg.Error as e:
        print(f"Failed connecting to V2 Database: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Example usage for New Delhi
    print("Fetching continuous V2 Weather Dataset (Read-Only)...")
    df = fetch_continuous_weather_dataset(lat=28.6139, lon=77.2090)
    print(f"\\nMerged Dataset Rows: {len(df)}")
    print("\\nSample Tail (Future Forecasts transitioning from Actuals):")
    if not df.empty:
        print(df.tail(10)[['timestamp', 'temperature_2m', 'data_source']])
