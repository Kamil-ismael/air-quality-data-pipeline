import os
import sys
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from config import CITIES


def load_warehouse(csv_path):
    if not os.path.exists(csv_path):
        print(f"[ERREUR] Fichier {csv_path} introuvable.")
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERREUR] DATABASE_URL non définie.")
        sys.exit(1)

    print("Lecture du CSV...")
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    print(f"  {len(df)} lignes lues.")

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    try:
        # ------------------------------------------------------------
        # 1) Villes : il n'y en a que quelques-unes, upsert direct
        # ------------------------------------------------------------
        print("Chargement des villes...")
        city_rows = []
        for city_name in df["city"].unique():
            info = CITIES.get(city_name.strip())
            if not info:
                print(f"  [ATTENTION] Ville inconnue ignorée : {city_name}")
                continue
            city_rows.append((city_name, info["country"], info["latitude"], info["longitude"]))

        execute_values(
            cur,
            """
            INSERT INTO dim_city (city_name, country, latitude, longitude)
            VALUES %s
            ON CONFLICT (city_name) DO NOTHING
            """,
            city_rows,
        )
        conn.commit()

        cur.execute("SELECT id_city, city_name FROM dim_city")
        city_id_map = {name: cid for cid, name in cur.fetchall()}
        print(f"  {len(city_id_map)} villes en base.")

        # ------------------------------------------------------------
        # 2) Temps : une ligne par horodatage unique du CSV, en masse
        # ------------------------------------------------------------
        print("Chargement de la dimension temps...")
        unique_timestamps = df["timestamp"].drop_duplicates().sort_values()

        time_rows = []
        for dt in unique_timestamps:
            dt = dt.to_pydatetime()
            time_rows.append((
                dt, dt.date(), dt.hour, dt.day, dt.month, dt.year,
                dt.strftime("%A"), dt.weekday() >= 5,
            ))

        execute_values(
            cur,
            """
            INSERT INTO dim_time (
                full_datetime, date, hour, day, month, year, day_of_week, is_weekend
            ) VALUES %s
            ON CONFLICT (full_datetime) DO NOTHING
            """,
            time_rows,
            page_size=1000,
        )
        conn.commit()

        cur.execute("SELECT id_time, full_datetime FROM dim_time")
        time_id_map = {ts: tid for tid, ts in cur.fetchall()}
        print(f"  {len(time_id_map)} horodatages en base.")

        # ------------------------------------------------------------
        # 3) Faits : en masse, avec ON CONFLICT DO NOTHING
        # ------------------------------------------------------------
        print("Chargement des faits...")
        fact_rows = []
        ignores_ville_inconnue = 0

        for row in df.itertuples(index=False):
            city_id = city_id_map.get(row.city)
            if city_id is None:
                ignores_ville_inconnue += 1
                continue
            dt = row.timestamp.to_pydatetime()
            time_id = time_id_map.get(dt)
            if time_id is None:
                continue

            def clean_val(v):
                return None if pd.isna(v) else float(v)

            fact_rows.append((
                city_id, time_id,
                clean_val(row.pm10),
                clean_val(row.pm2_5),
                clean_val(row.carbon_monoxide),
                clean_val(row.nitrogen_dioxide),
                clean_val(row.sulphur_dioxide),
                clean_val(row.ozone),
                None if pd.isna(row.us_aqi) else int(row.us_aqi),
            ))

        before = _count_facts(cur)

        execute_values(
            cur,
            """
            INSERT INTO fact_aqi (
                id_city, id_time, pm10, pm2_5, carbon_monoxide,
                nitrogen_dioxide, sulphur_dioxide, ozone, us_aqi
            ) VALUES %s
            ON CONFLICT (id_city, id_time) DO NOTHING
            """,
            fact_rows,
            page_size=1000,
        )
        conn.commit()

        after = _count_facts(cur)
        inseres = after - before
        doublons = len(fact_rows) - inseres

        print(f"\n[OK] {inseres} nouveaux faits insérés, {doublons} doublons ignorés"
              f"{f', {ignores_ville_inconnue} lignes avec ville inconnue' if ignores_ville_inconnue else ''}.")

    except Exception as e:
        conn.rollback()
        print(f"[ERREUR] {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


def _count_facts(cur):
    cur.execute("SELECT COUNT(*) FROM fact_aqi")
    return cur.fetchone()[0]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python load_warehouse.py clean/aqi_data.csv")
        sys.exit(1)
    load_warehouse(sys.argv[1])