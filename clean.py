import json
import os
import pandas as pd
def load_city_raw_files(city_name: str, raw_dir: str = "raw") -> pd.DataFrame:
    """
    Lit tous les fichiers JSON d'une ville dans raw/
    et les transforme en DataFrame.
    """
    city_dir = os.path.join(raw_dir, city_name)
    if not os.path.exists(city_dir):
        raise FileNotFoundError(f"Dossier introuvable : {city_dir}")
    all_rows = []
    for filename in os.listdir(city_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(city_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        hourly = data["hourly"]
        n_hours = len(hourly["time"])
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        for i in range(n_hours):
            row = {
                "city": city_name,
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": hourly["time"][i],
            }
            for variable in [
                "pm10",
                "pm2_5",
                "carbon_monoxide",
                "nitrogen_dioxide",
                "sulphur_dioxide",
                "ozone",
                "us_aqi",
            ]:
                values = hourly.get(variable)
                if values is not None and i < len(values):
                    row[variable] = values[i]
                else:
                    row[variable] = None
            all_rows.append(row)
    return pd.DataFrame(all_rows)
def build_clean_dataset(
    raw_dir: str = "raw",
    clean_path: str = "clean/aqi_data.csv",
) -> pd.DataFrame:
    """
    Construit le dataset propre à partir de tous les JSON présents dans raw/.
    """
    from config import CITIES
    city_dfs = []
    for city_name in CITIES:
        print(f"Chargement de {city_name}...")
        df_city = load_city_raw_files(city_name, raw_dir)
        city_dfs.append(df_city)
    if not city_dfs:
        raise ValueError("Aucune donnée trouvée dans raw/")
    df = pd.concat(city_dfs, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates(
        subset=["city", "timestamp"]
    )
    df = df.sort_values(
        by=["city", "timestamp"]
    )
    os.makedirs(
        os.path.dirname(clean_path),
        exist_ok=True,
    )
    df.to_csv(
        clean_path,
        index=False,
    )
    print("\n=== Dataset clean généré ===")
    print(f"Fichier : {clean_path}")
    print(f"Lignes : {len(df)}")
    print(f"Colonnes : {len(df.columns)}")
    return df
if __name__ == "__main__":
