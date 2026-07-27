"""Collecte horaire de l'AQI courant pour chaque ville.

Un fichier JSON brut est écrit par ville et par appel dans data/raw/.
Ces fichiers ne doivent JAMAIS être modifiés ni supprimés après coup :
c'est la source de vérité à partir de laquelle clean/ est reconstruit.

Variables d'environnement requises :
  OWM_API_KEY  -> clé API OpenWeatherMap (jamais commitée, jamais en dur dans le code)
"""

import os
import json
from datetime import datetime, timezone

import requests

from cities import CITIES

API_KEY = os.environ["OWM_API_KEY"]
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
URL = "https://api.openweathermap.org/data/2.5/air_pollution"


def fetch_city(city: dict) -> dict:
    params = {"lat": city["lat"], "lon": city["lon"], "appid": API_KEY}
    resp = requests.get(URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    now = datetime.now(timezone.utc)
    for city in CITIES:
        data = fetch_city(city)
        data["_city_meta"] = city
        data["_fetched_at"] = now.isoformat()

        city_dir = os.path.join(RAW_DIR, city["name"].replace(" ", "_"))
        os.makedirs(city_dir, exist_ok=True)

        fname = now.strftime("%Y%m%dT%H%M%SZ") + ".json"
        path = os.path.join(city_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] {city['name']} -> {path}")


if __name__ == "__main__":
    main()
