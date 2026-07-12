CITIES = {
    "Antananarivo": {"latitude": -18.8792, "longitude": 47.5079, "country": "Madagascar"},
    "Toamasina":    {"latitude": -18.1492, "longitude": 49.4023, "country": "Madagascar"},
    "Mahajanga":    {"latitude": -15.7167, "longitude": 46.3167, "country": "Madagascar"},
    "Fianarantsoa": {"latitude": -21.4536, "longitude": 47.0854, "country": "Madagascar"},
    "Antsiranana":  {"latitude": -12.2787, "longitude": 49.2917, "country": "Madagascar"},
}

HOURLY_VARIABLES = [
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "us_aqi",
]

BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

RAW_DIR = "raw"
TIMEZONE = "Indian/Antananarivo"