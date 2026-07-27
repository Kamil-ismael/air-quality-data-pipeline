import os
import sys

import pandas as pd


CLEAN_FILE = "clean/aqi_data.csv"

REQUIRED_COLUMNS = [
    "city",
    "latitude",
    "longitude",
    "timestamp",
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "us_aqi",
]

EXPECTED_CITIES = [
    "Antananarivo",
    "Toamasina",
    "Mahajanga",
    "Fianarantsoa",
    "Antsiranana",
]


def validate_file_exists(filepath: str) -> bool:
    if not os.path.exists(filepath):
        print(f"[ERREUR] Fichier introuvable : {filepath}")
        return False

    print("[OK] Fichier clean trouvé")
    return True


def validate_columns(df: pd.DataFrame) -> bool:
    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing_columns:
        print(f"[ERREUR] Colonnes manquantes : {missing_columns}")
        return False

    print("[OK] Colonnes présentes")
    return True


def validate_cities(df: pd.DataFrame) -> bool:
    cities = set(df["city"].unique())

    missing_cities = set(EXPECTED_CITIES) - cities

    if missing_cities:
        print(f"[ERREUR] Villes manquantes : {missing_cities}")
        return False

    print(f"[OK] {len(cities)} villes détectées")
    return True


def validate_duplicates(df: pd.DataFrame) -> bool:
    duplicates = df.duplicated(
        subset=["city", "timestamp"]
    ).sum()

    if duplicates > 0:
        print(f"[ERREUR] {duplicates} doublons trouvés")
        return False

    print("[OK] Aucun doublon")
    return True


def validate_timestamp(df: pd.DataFrame) -> bool:
    try:
        pd.to_datetime(df["timestamp"])
        print("[OK] Timestamp valide")
        return True

    except Exception:
        print("[ERREUR] Timestamp invalide")
        return False


def validate_clean_dataset(filepath: str = CLEAN_FILE) -> int:
    print("=== Validation clean dataset ===\n")

    if not validate_file_exists(filepath):
        return 1

    df = pd.read_csv(filepath)

    validations = [
        validate_columns(df),
        validate_cities(df),
        validate_duplicates(df),
        validate_timestamp(df),
    ]

    print()

    if all(validations):
        print("Dataset conforme !")
        print(f"Lignes : {len(df)}")
        print(f"Colonnes : {len(df.columns)}")
        return 0

    print("Dataset non conforme !")
    return 1


if __name__ == "__main__":
    sys.exit(validate_clean_dataset())