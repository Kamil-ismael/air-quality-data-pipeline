import argparse
import json
import os
import sys
import time
from datetime import date, timedelta
import requests
from config import CITIES, HOURLY_VARIABLES, BASE_URL, RAW_DIR, TIMEZONE


def month_chunks(start: date, end: date):
    """
    Découpe la période [start, end) en tranches mensuelles.

    Le backfill est exécuté mois par mois afin de :
    - limiter la taille des réponses API ;
    - faciliter la reprise après une interruption ;
    - rendre chaque mois rejouable indépendamment.
    """
    current = start
    while current < end:
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(current.year, current.month + 1, 1)
        chunk_end = min(next_month, end)
        yield current, chunk_end
        current = next_month


def fetch_chunk(
    latitude: float, longitude: float, start: date, end: date
) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,
        "start_date": start.isoformat(),
        # L'API traite end_date comme INCLUSIF(elle inclut les 24h de ce jour).
        # Comme nos tranches sont exclusives à droite (ex: 1er juillet -> 1er
        # août exclu), on recule d'un jour pour ne pas déborder.
        "end_date": (end - timedelta(days=1)).isoformat(),
    }
    response = requests.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def save_raw(city_name: str, start: date, data: dict) -> str:
    city_dir = os.path.join(RAW_DIR, city_name)
    os.makedirs(city_dir, exist_ok=True)
    # Nom de fichier = le mois couvert (pas un timestamp d'exécution comme
    # dans collect.py). C'est ce qui rend le script IDEMPOTENT : relancer
    # backfill.py deux fois ne télécharge jamais deux fois le même mois.
    filename = f"backfill_{start.strftime('%Y-%m')}.json"
    filepath = os.path.join(city_dir, filename)
    if os.path.exists(filepath):
        print(f" [SKIP] {filepath} déjà présent")
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
            month_str = chunk_start.strftime("%Y-%m")
            target = os.path.join(
                RAW_DIR, city_name, f"backfill_{month_str}.json"
            )
            # Check fait AVANT l'appel API (pas seulement dans save_raw) pour
            # éviter de consommer un appel réseau inutile sur un mois déjà fait
            if os.path.exists(target):
                print(f" [SKIP] {month_str} already exists")
                continue
            try:
                data = fetch_chunk(
                    coords["latitude"], coords["longitude"],
                    chunk_start, chunk_end
                )
                filepath = save_raw(city_name, chunk_start, data)
                print(f" [OK] {month_str} -> {filepath}")
                # Pause de courtoisie : évite de spammer une API gratuite
                # avec des dizaines d'appels à la suite (5 villes x 12 mois)
                time.sleep(1)
            except requests.exceptions.RequestException as exc:
                print(f" [ERREUR] {month_str}: {exc}")
                errors += 1
    print(f"=== Backfill terminé ({errors} erreur(s)) ===")
    return 1 if errors else 0


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill historique AQI")
    parser.add_argument(
        "--months", type=int,
        help="Nombre de mois à remonter depuis aujourd'hui"
    )
    parser.add_argument("--start", type=str, help="Date de début YYYY-MM-DD")
    parser.add_argument(
        "--end", type=str,
        help="Date de fin YYYY-MM-DD (exclusive)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    today = date.today()
    if args.start and args.end:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    elif args.months:
        end_date = today
        # Approximation volontaire (30 jours/mois) : suffisant ici puisque
        # month_chunks() redécoupe de toute façon en vrais mois calendaires
        start_date = today - timedelta(days=args.months * 30)
    else:
        # Valeur par défaut = 12 mois, comme recommandé par le sujet
        end_date = today
        start_date = today - timedelta(days=365)
    sys.exit(run(start_date, end_date))
