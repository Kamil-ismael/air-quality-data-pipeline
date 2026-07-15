import argparse
import json
import os
import sys
import time
from datetime import date, timedelta

import requests

from config import CITIES, HOURLY_VARIABLES, BASE_URL, RAW_DIR, TIMEZONE


def month_chunks(start: date, end: date):
    current = start
    while current < end:
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(current.year, current.month + 1, 1)
        chunk_end = min(next_month, end)
        yield current, chunk_end
        current = next_month


def fetch_chunk(latitude: float, longitude: float, start: date, end: date) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,
        "start_date": start.isoformat(),
        "end_date": (end - timedelta(days=1)).isoformat(),
    }
    response = requests.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def save_raw(city_name: str, start: date, data: dict) -> str:
    city_dir = os.path.join(RAW_DIR, city_name)
    os.makedirs(city_dir, exist_ok=True)

    filepath = os.path.join(city_dir, f"backfill_{start.strftime('%Y-%m')}.json")

    if os.path.exists(filepath):
        print(f"  [SKIP] {filepath} déjà présent")
        return filepath

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def run(start: date, end: date) -> int:
    print(f"=== Backfill AQI : {start.isoformat()} -> {end.isoformat()} ===")
    errors = 0

    for city_name, coords in CITIES.items():
        print(f"-- {city_name} --")
        for chunk_start, chunk_end in month_chunks(start, end):
            target = os.path.join(RAW_DIR, city_name, f"backfill_{chunk_start.strftime('%Y-%m')}.json")
            if os.path.exists(target):
                print(f"  [SKIP] {chunk_start.strftime('%Y-%m')} already exists")
                continue
            try:
                data = fetch_chunk(coords["latitude"], coords["longitude"], chunk_start, chunk_end)
                filepath = save_raw(city_name, chunk_start, data)
                print(f"  [OK] {chunk_start.strftime('%Y-%m')} -> {filepath}")
                time.sleep(1)
            except requests.exceptions.RequestException as exc:
                print(f"  [ERREUR] {chunk_start.strftime('%Y-%m')}: {exc}")
                errors += 1

    print(f"=== Backfill terminé ({errors} erreur(s)) ===")
    return 1 if errors else 0


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill historique AQI")
    parser.add_argument("--months", type=int, help="Nombre de mois à remonter depuis aujourd'hui")
    parser.add_argument("--start", type=str, help="Date de début YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="Date de fin YYYY-MM-DD (exclusive)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    today = date.today()

    if args.start and args.end:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    elif args.months:
        end_date = today
        start_date = today - timedelta(days=args.months * 30)
    else:
        end_date = today
        start_date = today - timedelta(days=365)

    sys.exit(run(start_date, end_date))