# Stockage — air-quality-data-pipeline

Documentation du stockage des données : villes couvertes, format de `clean/`,
schéma du data warehouse, couverture temporelle, trous connus et connexion
à la base.

## 1. Villes choisies

5 villes de Madagascar, coordonnées définies dans `config.py` :

| Ville         | Latitude  | Longitude | Pays       |
|---------------|-----------|-----------|------------|
| Antananarivo  | -18.8792  | 47.5079   | Madagascar |
| Toamasina     | -18.1492  | 49.4023   | Madagascar |
| Mahajanga     | -15.7167  | 46.3167   | Madagascar |
| Fianarantsoa  | -21.4536  | 47.0854   | Madagascar |
| Antsiranana   | -12.2787  | 49.2917   | Madagascar |

Note : ce sont les coordonnées demandées à l'API. L'API Open-Meteo réplique
les données sur sa propre grille et renvoie les coordonnées réelles de la
maille utilisée (légèrement différentes, ex. Antananarivo -18.900002/47.5) —
ce sont ces valeurs "grille" qui se retrouvent dans `clean/aqi_data.csv`.

## 2. Colonnes et unités — `clean/aqi_data.csv`

Généré par `clean.py` à partir de tous les fichiers JSON de `raw/`.

| Colonne             | Type    | Unité   | Description                          |
|----------------------|---------|---------|---------------------------------------|
| `city`               | string  | —       | Nom de la ville                       |
| `latitude`            | float   | degrés  | Latitude réelle (grille Open-Meteo)   |
| `longitude`           | float   | degrés  | Longitude réelle (grille Open-Meteo)  |
| `timestamp`           | datetime| —       | Heure locale (`Indian/Antananarivo`), résolution horaire |
| `pm10`                | float   | µg/m³   | Particules PM10                       |
| `pm2_5`               | float   | µg/m³   | Particules PM2.5                      |
| `carbon_monoxide`     | float   | µg/m³   | Monoxyde de carbone (CO)              |
| `nitrogen_dioxide`    | float   | µg/m³   | Dioxyde d'azote (NO₂)                 |
| `sulphur_dioxide`     | float   | µg/m³   | Dioxyde de soufre (SO₂)               |
| `ozone`               | float   | µg/m³   | Ozone (O₃)                            |
| `us_aqi`              | int     | US AQI  | Indice de qualité de l'air (échelle US EPA) |

Unités confirmées via le champ `hourly_units` renvoyé par l'API Open-Meteo
Air Quality (`https://air-quality-api.open-meteo.com/v1/air-quality`).

Règles de nettoyage appliquées par `clean.py` :
- concaténation de tous les JSON par ville (`raw/<ville>/*.json`)
- dédoublonnage sur `(city, timestamp)` — le fichier le plus récent l'emporte à la lecture
- tri par `city`, puis `timestamp`
- valeurs manquantes conservées telles quelles (`None` → vide dans le CSV)

`validate_clean.py` vérifie avant chargement : présence des 11 colonnes,
présence des 5 villes attendues, absence de doublons `(city, timestamp)`,
et validité du format `timestamp`.

## 3. Schéma du data warehouse

Modèle en étoile, défini dans `database/shema.sql` (PostgreSQL).

**`dim_city`**
| Colonne     | Type          | Contrainte              |
|-------------|---------------|--------------------------|
| id_city     | SERIAL        | PK                       |
| city_name   | VARCHAR(100)  | NOT NULL, UNIQUE         |
| country     | VARCHAR(100)  | NOT NULL                 |
| latitude    | NUMERIC(9,6)  | NOT NULL                 |
| longitude   | NUMERIC(9,6)  | NOT NULL                 |

**`dim_time`**
| Colonne        | Type          | Contrainte                        |
|----------------|---------------|-------------------------------------|
| id_time        | SERIAL        | PK                                   |
| full_datetime  | TIMESTAMP     | NOT NULL, UNIQUE                     |
| date           | DATE          | NOT NULL                             |
| hour           | SMALLINT      | NOT NULL, CHECK 0–23                 |
| day / month / year | SMALLINT | NOT NULL                             |
| day_of_week    | VARCHAR(10)   | NOT NULL (ex. `'Monday'`)            |
| is_weekend     | BOOLEAN       | NOT NULL                             |

**`fact_aqi`**
| Colonne           | Type          | Contrainte                          |
|-------------------|---------------|---------------------------------------|
| id_fact           | SERIAL        | PK                                     |
| id_city           | INTEGER       | FK → `dim_city(id_city)`, NOT NULL     |
| id_time           | INTEGER       | FK → `dim_time(id_time)`, NOT NULL     |
| pm10, pm2_5, carbon_monoxide, nitrogen_dioxide, sulphur_dioxide, ozone | NUMERIC(8,3) | nullable |
| us_aqi            | INTEGER       | nullable                               |
| —                 | —             | UNIQUE `(id_city, id_time)`            |

Index : `idx_fact_aqi_city` sur `id_city`, `idx_fact_aqi_time` sur `id_time`.

Chargement (`load_warehouse.py`) : upsert des villes et des horodatages
(`ON CONFLICT DO NOTHING`), puis insertion des faits avec
`ON CONFLICT (id_city, id_time) DO NOTHING` — le rechargement du CSV entier
est donc idempotent, aucun doublon n'est créé.

## 4. Période couverte

- **Globale : du 2025-07-13 00:00 au 2026-07-31 13:00** (heure locale
  `Indian/Antananarivo`), identique pour les 5 villes.
- Deux origines de données, visibles dans `raw/<ville>/` :
  - `backfill_YYYY-MM.json` : historique récupéré mois par mois par
    `backfill.py` (12 mois par défaut, de 2025-07 à 2026-07).
  - `YYYYMMDDThhmmssZ.json` : collectes horaires par `collect.py`, déclenchées
    manuellement (`workflow_dispatch` uniquement dans
    `.github/workflows/collecte.yml` — pas de cron), actives depuis le
    2026-07-13.
- 8 850 lignes par ville / 44 250 lignes au total dans `clean/aqi_data.csv`.

## 5. Connexion à la base

- SGBD : PostgreSQL (hébergé sur **Neon**).
- Connexion via la variable d'environnement **`DATABASE_URL`**
  (chaîne de connexion `postgresql://...`), lue par `load_warehouse.py`
  avec `os.getenv("DATABASE_URL")`.
- En local : définir `DATABASE_URL` dans un fichier `.env` (jamais commité —
  exclu via `.gitignore`) et le charger avec `python-dotenv`, ou l'exporter
  dans le shell.
- En CI/CD : stockée comme secret GitHub Actions `secrets.DATABASE_URL`,
  injectée dans l'étape « Charger le data warehouse (Neon) » du workflow
  `.github/workflows/collecte.yml`.
- Chargement : `python load_warehouse.py clean/aqi_data.csv`
- Dépendance : `psycopg2-binary` (voir `requirements.txt`).

## 6. Pipeline de bout en bout (rappel)

1. `collect.py` (manuel) ou `backfill.py` (historique) → écrit dans `raw/`
   (jamais modifié après écriture).
2. `clean.py` → reconstruit entièrement `clean/aqi_data.csv` à partir de
   tout `raw/`.
3. `validate_clean.py` → contrôle qualité avant chargement.
4. `load_warehouse.py` → charge `clean/aqi_data.csv` dans le warehouse
   PostgreSQL (Neon), de façon idempotente.
