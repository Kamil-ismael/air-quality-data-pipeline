import os
import csv
import sys
from datetime import datetime
import psycopg2

CITIES = {
    "Antananarivo": {"latitude": -18.8792, "longitude": 47.5079},
    "Toamasina": {"latitude": -18.1492, "longitude": 49.4023},
    "Mahajanga": {"latitude": -15.7167, "longitude": 46.3167},
    "Fianarantsoa": {"latitude": -21.4536, "longitude": 47.0854},
    "Antsiranana": {"latitude": -12.2787, "longitude": 49.2917},
}

def get_or_create_city(cur, city_name):
    city_name = city_name.strip().capitalize()
    cur.execute("SELECT id_city FROM DimCity WHERE city_name = %s", (city_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    info = CITIES.get(city_name)
    if not info:
        raise ValueError(f"Ville '{city_name}' non trouvée dans CITIES.")
    cur.execute(
        "INSERT INTO DimCity (city_name, latitude, longitude) VALUES (%s, %s, %s) RETURNING id_city",
        (city_name, info["latitude"], info["longitude"])
    )
    return cur.fetchone()[0]

def get_or_create_date(cur, dt):
    cur.execute("SELECT id_date FROM DimDate WHERE full_date = %s", (dt,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO DimDate (full_date, year, month, day) VALUES (%s, %s, %s, %s) RETURNING id_date",
        (dt, dt.year, dt.month, dt.day)
    )
    return cur.fetchone()[0]

def load_warehouse(csv_path):
    if not os.path.exists(csv_path):
        print(f"[ERREUR] Fichier {csv_path} introuvable.")
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERREUR] DATABASE_URL non définie.")
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    total = 0
    ignores = 0

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Afficher les colonnes pour déboguer
            print(f"Colonnes du CSV : {reader.fieldnames}")
            for row in reader:
                try:
                    city_id = get_or_create_city(cur, row["city"])
                    dt = datetime.fromisoformat(row["timestamp"])
                    date_id = get_or_create_date(cur, dt)

                    cur.execute(
                        "SELECT id_fact FROM FactAirQuality WHERE id_city = %s AND id_date = %s",
                        (city_id, date_id)
                    )
                    if cur.fetchone():
                        ignores += 1
                        continue

                    cur.execute(
                        """
                        INSERT INTO FactAirQuality (
                            id_city, id_date, pm10, pm2_5, carbon_monoxide,
                            nitrogen_dioxide, sulphur_dioxide, ozone, us_aqi
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            city_id, date_id,
                            float(row["pm10"]) if row["pm10"] else None,
                            float(row["pm2_5"]) if row["pm2_5"] else None,
                            float(row["carbon_monoxide"]) if row["carbon_monoxide"] else None,
                            float(row["nitrogen_dioxide"]) if row["nitrogen_dioxide"] else None,
                            float(row["sulphur_dioxide"]) if row["sulphur_dioxide"] else None,
                            float(row["ozone"]) if row["ozone"] else None,
                            int(row["us_aqi"]) if row["us_aqi"] else None
                        )
                    )
                    total += 1
                    if total % 500 == 0:
                        conn.commit()
                        print(f"  {total} lignes chargées...")
                except Exception as e:
                    print(f"  [IGNORÉ] Ligne avec erreur : {e}")
                    continue
        conn.commit()
        print(f"[OK] {total} faits insérés, {ignores} doublons ignorés.")
    except Exception as e:
        conn.rollback()
        print(f"[ERREUR] {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python load_warehouse.py clean/aqi_data.csv")
        sys.exit(1)
    load_warehouse(sys.argv[1])