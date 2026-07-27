"""Charge data/clean/aqi_data.csv dans le data warehouse Postgres.

Rejouable : chaque ligne est upsertée (ON CONFLICT ... DO UPDATE / DO NOTHING),
donc relancer ce script après une nouvelle collecte ne duplique rien.

Variables d'environnement requises :
  DATABASE_URL  -> ex: postgresql://user:password@host:5432/dbname
"""

import os
import csv
from datetime import datetime

import psycopg2

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CLEAN_PATH = os.path.join(BASE_DIR, "data", "clean", "aqi_data.csv")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

DATABASE_URL = os.environ["DATABASE_URL"]


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def ensure_schema(conn) -> None:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        ddl = f.read()
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def upsert_city(cur, name, country, lat, lon) -> int:
    cur.execute(
        """
        INSERT INTO dim_city (name, country, latitude, longitude)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (name, country) DO NOTHING
        RETURNING city_id
        """,
        (name, country, lat, lon),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT city_id FROM dim_city WHERE name=%s AND country=%s", (name, country))
    return cur.fetchone()[0]


def upsert_time(cur, ts_str: str) -> int:
    ts = datetime.fromisoformat(ts_str)
    cur.execute(
        """
        INSERT INTO dim_time (timestamp_utc, date, hour, day_of_week, is_weekend, month, year)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (timestamp_utc) DO NOTHING
        RETURNING time_id
        """,
        (ts, ts.date(), ts.hour, ts.weekday(), ts.weekday() >= 5, ts.month, ts.year),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT time_id FROM dim_time WHERE timestamp_utc=%s", (ts,))
    return cur.fetchone()[0]


def main() -> None:
    conn = get_conn()
    ensure_schema(conn)

    count = 0
    with conn.cursor() as cur, open(CLEAN_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            city_id = upsert_city(cur, row["city"], row["country"], row["latitude"], row["longitude"])
            time_id = upsert_time(cur, row["timestamp_utc"])

            cur.execute(
                """
                INSERT INTO fact_aqi (city_id, time_id, aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (city_id, time_id) DO UPDATE SET
                    aqi   = EXCLUDED.aqi,
                    co    = EXCLUDED.co,
                    no    = EXCLUDED.no,
                    no2   = EXCLUDED.no2,
                    o3    = EXCLUDED.o3,
                    so2   = EXCLUDED.so2,
                    pm2_5 = EXCLUDED.pm2_5,
                    pm10  = EXCLUDED.pm10,
                    nh3   = EXCLUDED.nh3
                """,
                (
                    city_id, time_id,
                    row["aqi"] or None, row["co"] or None, row["no"] or None,
                    row["no2"] or None, row["o3"] or None, row["so2"] or None,
                    row["pm2_5"] or None, row["pm10"] or None, row["nh3"] or None,
                ),
            )
            count += 1
        conn.commit()

    conn.close()
    print(f"[OK] {count} lignes chargées dans le warehouse")


if __name__ == "__main__":
    main()
