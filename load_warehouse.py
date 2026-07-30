import os
import csv
import sys
from datetime import datetime
import psycopg2

from config import CITIES

DAYS_FR = None  # on garde les noms de jours en anglais (standard, sans accent)


def get_or_create_city(cur, city_name):
    """
    Récupère l'id de la ville, la crée si elle n'existe pas encore.
    Utilise ON CONFLICT pour être atomique : pas de SELECT puis INSERT
    séparés qui pourraient planter la transaction entre les deux.
    """
    city_name = city_name.strip()
    info = CITIES.get(city_name)
    if not info:
        raise ValueError(f"Ville '{city_name}' non trouvée dans CITIES (config.py).")

    cur.execute(
        """
        INSERT INTO dim_city (city_name, country, latitude, longitude)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (city_name) DO UPDATE
            SET city_name = EXCLUDED.city_name
        RETURNING id_city
        """,
        (city_name, info["country"], info["latitude"], info["longitude"]),
    )
    return cur.fetchone()[0]


def get_or_create_time(cur, dt: datetime):
    """
    Récupère l'id de la ligne dim_time pour cet horodatage, la crée sinon.
    Une ligne = une heure précise (pas juste un jour).
    """
    day_of_week = dt.strftime("%A")       # ex: 'Monday'
    is_weekend = dt.weekday() >= 5        # 5 = samedi, 6 = dimanche

    cur.execute(
        """
        INSERT INTO dim_time (
            full_datetime, date, hour, day, month, year, day_of_week, is_weekend
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (full_datetime) DO UPDATE
            SET full_datetime = EXCLUDED.full_datetime
        RETURNING id_time
        """,
        (
            dt, dt.date(), dt.hour, dt.day, dt.month, dt.year,
            day_of_week, is_weekend,
        ),
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
    erreurs = 0

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            print(f"Colonnes du CSV : {reader.fieldnames}")

            for row in reader:
                # SAVEPOINT : si cette ligne plante, on ne perd que
                # cette ligne, pas tout ce qui a été inséré avant dans
                # la transaction en cours.
                cur.execute("SAVEPOINT row_sp")
                try:
                    city_id = get_or_create_city(cur, row["city"])
                    dt = datetime.fromisoformat(row["timestamp"])
                    time_id = get_or_create_time(cur, dt)

                    cur.execute(
                        """
                        INSERT INTO fact_aqi (
                            id_city, id_time, pm10, pm2_5, carbon_monoxide,
                            nitrogen_dioxide, sulphur_dioxide, ozone, us_aqi
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id_city, id_time) DO NOTHING
                        """,
                        (
                            city_id, time_id,
                            float(row["pm10"]) if row["pm10"] else None,
                            float(row["pm2_5"]) if row["pm2_5"] else None,
                            float(row["carbon_monoxide"]) if row["carbon_monoxide"] else None,
                            float(row["nitrogen_dioxide"]) if row["nitrogen_dioxide"] else None,
                            float(row["sulphur_dioxide"]) if row["sulphur_dioxide"] else None,
                            float(row["ozone"]) if row["ozone"] else None,
                            int(float(row["us_aqi"])) if row["us_aqi"] else None,
                        ),
                    )
                    if cur.rowcount == 0:
                        ignores += 1
                    else:
                        total += 1

                    cur.execute("RELEASE SAVEPOINT row_sp")

                    if (total + ignores) % 500 == 0:
                        conn.commit()
                        print(f"  {total} lignes chargées, {ignores} doublons ignorés...")

                except Exception as e:
                    # On annule UNIQUEMENT cette ligne, pas toute la transaction
                    cur.execute("ROLLBACK TO SAVEPOINT row_sp")
                    erreurs += 1
                    print(f"  [IGNORÉ] Ligne avec erreur : {e}")
                    continue

        conn.commit()
        print(f"\n[OK] {total} faits insérés, {ignores} doublons ignorés, {erreurs} lignes en erreur.")

    except Exception as e:
        conn.rollback()
        print(f"[ERREUR FATALE] {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python load_warehouse.py clean/aqi_data.csv")
        sys.exit(1)
    load_warehouse(sys.argv[1])