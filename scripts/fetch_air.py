import requests
import pandas as pd
from datetime import datetime, timedelta

HEADERS = {"X-API-Key": "e4c4498cda2dcdf6594d5f14f6e040ec610cfb1a83987baddb38883eca7d1ff3"}
BASE = "https://api.openaq.org/v3"

CITIES = {
    "Delhi":     {"bbox": "76.84,28.40,77.35,28.88"},
    "Mumbai":    {"bbox": "72.77,18.89,73.00,19.27"},
    "Bengaluru": {"bbox": "77.46,12.83,77.75,13.14"},
    "Hyderabad": {"bbox": "78.35,17.25,78.60,17.55"},
    "Pune":      {"bbox": "73.75,18.42,73.98,18.62"},
    "Chennai":   {"bbox": "80.15,12.90,80.30,13.15"},
}

PARAM_MAP = {
    "pm25": "pm25", "pm2.5": "pm25", "pm_25": "pm25",
    "pm10": "pm10", "pm_10": "pm10",
    "no2":  "no2",  "no2 mass": "no2",
}


def get_location_ids(city_name, bbox):
    r = requests.get(
        f"{BASE}/locations",
        headers=HEADERS,
        params={"bbox": bbox, "limit": 15, "iso": "IN", "monitor": "true"},
        timeout=15,
    )
    r.raise_for_status()
    ids = [loc["id"] for loc in r.json().get("results", [])]
    print(f"  Found {len(ids)} locations for {city_name}: {ids}")
    return ids


def get_sensors(location_id):
    r = requests.get(
        f"{BASE}/locations/{location_id}/sensors",
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def get_hourly(sensor_id, days=90):
    date_from = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
    date_to   = datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z")
    r = requests.get(
        f"{BASE}/sensors/{sensor_id}/hours",
        headers=HEADERS,
        params={"datetime_from": date_from, "datetime_to": date_to, "limit": 1000},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("results", [])


rows = []

for city_name, cfg in CITIES.items():
    print(f"\nFetching {city_name}...")
    try:
        loc_ids = get_location_ids(city_name, cfg["bbox"])
    except Exception as e:
        print(f"  Location lookup failed: {e}")
        continue

    for loc_id in loc_ids:
        try:
            sensors = get_sensors(loc_id)
        except Exception as e:
            print(f"  Sensors fetch failed for loc {loc_id}: {e}")
            continue

        for sensor in sensors:
            raw_param = sensor.get("parameter", {}).get("name", "").lower()
            param = PARAM_MAP.get(raw_param)
            if not param:
                continue
            sensor_id = sensor.get("id")
            print(f"  Sensor {sensor_id} ({raw_param} → {param})")
            try:
                hourly = get_hourly(sensor_id)
            except Exception as e:
                print(f"    Hourly fetch failed: {e}")
                continue
            for h in hourly:
                rows.append({
                    "city_name":    city_name,
                    "measure_date": h.get("period", {}).get("datetimeFrom", {}).get("local", "")[:10],
                    "parameter":    param,
                    "value":        h.get("value"),
                })

if not rows:
    print("\nNo data found.")
else:
    df = pd.DataFrame(rows).dropna(subset=["value"])
    df_pivot = (
        df.groupby(["city_name", "measure_date", "parameter"])["value"]
        .mean().unstack("parameter").reset_index()
    )
    df_pivot.columns.name = None
    for col in ["pm25", "pm10", "no2"]:
        if col not in df_pivot.columns:
            df_pivot[col] = None
    df_pivot.to_csv("air_quality_daily.csv", index=False)
    print(f"\nSaved air_quality_daily.csv with {len(df_pivot)} rows")