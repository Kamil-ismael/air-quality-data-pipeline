import json
import os
import sys
from datetime import datetime, timezone

import requests

from config import CITIES, HOURLY_VARIABLES, BASE_URL, RAW_DIR, TIMEZONE


def fetch_city_data(city_name: str, latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,
        "past_hours": 1,
        "forecast_hours": 1,
    }
    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def save_raw(city_name: str, data: dict) -> str:
    city_dir = os.path.join(RAW_DIR, city_name)
    os.makedirs(city_dir, exist_ok=True)

    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filepath = os.path.join(city_dir, f"{run_timestamp}.json")

    if os.path.exists(filepath):
        print(f"  [SKIP] {filepath} already exists, skipping save.")
        return filepath

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def run() -> int:
    print(f"=== Collecte AQI — {datetime.now(timezone.utc).isoformat()} ===")
    errors = 0

    for city_name, coords in CITIES.items():
        try:
            data = fetch_city_data(city_name, coords["latitude"],
                                   coords["longitude"])
            filepath = save_raw(city_name, data)
            print(f"  [OK] {city_name} -> {filepath}")
        except requests.exceptions.RequestException as exc:
            print(f"  [ERREUR] {city_name}: {exc}")
            errors += 1

    print(f"=== Terminé : {len(CITIES) - errors}/{len(CITIES)} villes collectées ===")
    return 1 if errors == len(CITIES) else 0


if __name__ == "__main__":
    sys.exit(run())
