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
        # past_hours=1 : on redemande l'heure précédente, car l'heure
        # "courante" n'a parfois pas encore de valeur calculée côté API
        "past_hours": 1,
        "forecast_hours": 1,
    }
    response = requests.get(BASE_URL, params=params, timeout=30)
    # lève une exception si l'API répond en erreur (ex. 4xx/5xx)
    response.raise_for_status()
    return response.json()


def save_raw(city_name: str, data: dict) -> str:
    city_dir = os.path.join(RAW_DIR, city_name)
    os.makedirs(city_dir, exist_ok=True)

    # Nom de fichier basé sur l'heure d'exécution : garantit un fichier
    # unique par run, sans risque d'écrasement entre deux collectes
    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filepath = os.path.join(city_dir, f"{run_timestamp}.json")

    # Règle du sujet : raw/ ne doit JAMAIS être modifié après écriture.
    # Ce check empêche tout écrasement accidentel si le script est relancé
    # deux fois dans la même seconde.
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
            data = fetch_city_data(
                city_name, coords["latitude"], coords["longitude"]
            )
            filepath = save_raw(city_name, data)
            print(f"  [OK] {city_name} -> {filepath}")
        except requests.exceptions.RequestException as exc:
            # On attrape l'erreur ICI (dans la boucle, pas autour) pour qu'une
            # ville en panne n'empêche pas la collecte des 4 autres villes
            print(f"  [ERREUR] {city_name}: {exc}")
            errors += 1

    print(
        f"=== Terminé : {len(CITIES) - errors}/{len(CITIES)} "
        f"villes collectées ==="
    )
    # Échec (code retour 1) seulement si TOUTES les villes ont échoué —
    # un échec partiel ne doit pas faire planter l'orchestrateur (tâche 3)
    return 1 if errors == len(CITIES) else 0


if __name__ == "__main__":
    sys.exit(run())
