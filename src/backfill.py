"""Backfill historique de l'AQI pour toutes les villes.

Rejouable : relancer ce script ne casse rien, il ajoute simplement des
fichiers bruts (nommés par plage de dates) dans data/raw/. Le déduplication
finale se fait dans build_clean.py au moment de reconstruire clean/.

L'API OpenWeatherMap "air_pollution/history" fournit des données horaires
depuis le 27 novembre 2020. On découpe la période demandée en tranches de
30 jours pour rester dans les limites de l'API.

Usage :
    python src/backfill.py --months 12
    python src/backfill.py --months 3   (minimum accepté par la consigne)

Variables d'environnement requises :
  OWM_API_KEY
"""

import os
import json
import time
import argparse
from datetime import datetime, timedelta, timezone

import requests

from cities import CITIES

API_KEY = os.environ["OWM_API_KEY"]
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
URL = "https://api.openweathermap.org/data/2.5/air_pollution/history"


def fetch_history(city: dict, start_ts: int, end_ts: int) -> dict:
    params = {
        "lat": city["lat"],
        "lon": city["lon"],
        "start": start_ts,
        "end": end_ts,
        "appid": API_KEY,
    }
    resp = requests.get(URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main(months: int) -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30 * months)

    for city in CITIES:
        city_dir = os.path.join(RAW_DIR, city["name"].replace(" ", "_"))
        os.makedirs(city_dir, exist_ok=True)

        cursor = start
        while cursor < end:
            chunk_end = min(cursor + timedelta(days=30), end)
            data = fetch_history(city, int(cursor.timestamp()), int(chunk_end.timestamp()))
            data["_city_meta"] = city

            fname = f"backfill_{cursor.strftime('%Y%m%d')}_{chunk_end.strftime('%Y%m%d')}.json"
            path = os.path.join(city_dir, fname)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            n = len(data.get("list", []))
            print(f"[OK] {city['name']} {cursor.date()} -> {chunk_end.date()} ({n} points)")
            cursor = chunk_end
            time.sleep(1)  # ménage l'API, évite le rate-limit


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=3, help="Nombre de mois à backfill")
    args = parser.parse_args()
    main(args.months)
