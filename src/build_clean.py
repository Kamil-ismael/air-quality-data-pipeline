"""Reconstruit intégralement data/clean/aqi_data.csv à partir de data/raw/.

- Ne modifie jamais raw/ (lecture uniquement).
- Dédoublonne sur (ville, timestamp_utc) : un fichier de backfill et un
  fichier de collecte horaire peuvent se recouper, on ne garde qu'une ligne.
- Trie chronologiquement, puis par ville.

Ce script est idempotent : le relancer produit toujours le même résultat
pour un même contenu de raw/.
"""

import os
import csv
import json
from datetime import datetime, timezone

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
CLEAN_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "clean", "aqi_data.csv")

COLUMNS = [
    "city", "country", "latitude", "longitude",
    "timestamp_utc", "aqi",
    "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3",
]


def iter_records():
    seen = set()
    records = []

    for root, _, files in os.walk(RAW_DIR):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            path = os.path.join(root, fname)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            meta = data.get("_city_meta")
            if not meta:
                continue

            for entry in data.get("list", []):
                dt = datetime.fromtimestamp(entry["dt"], tz=timezone.utc)
                ts_iso = dt.isoformat()
                key = (meta["name"], ts_iso)
                if key in seen:
                    continue
                seen.add(key)

                comp = entry.get("components", {})
                records.append({
                    "city": meta["name"],
                    "country": meta["country"],
                    "latitude": meta["lat"],
                    "longitude": meta["lon"],
                    "timestamp_utc": ts_iso,
                    "aqi": entry.get("main", {}).get("aqi"),
                    "co": comp.get("co"),
                    "no": comp.get("no"),
                    "no2": comp.get("no2"),
                    "o3": comp.get("o3"),
                    "so2": comp.get("so2"),
                    "pm2_5": comp.get("pm2_5"),
                    "pm10": comp.get("pm10"),
                    "nh3": comp.get("nh3"),
                })

    records.sort(key=lambda r: (r["city"], r["timestamp_utc"]))
    return records


def main() -> None:
    os.makedirs(os.path.dirname(CLEAN_PATH), exist_ok=True)
    records = iter_records()

    with open(CLEAN_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)

    print(f"[OK] {len(records)} lignes -> {CLEAN_PATH}")


if __name__ == "__main__":
    main()
