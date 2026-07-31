# ARCHITECTURE.md — air-quality-data-pipeline

## Vue d'ensemble

Open-Meteo Air Quality API (5 villes malgaches)
        │  collecte horaire + backfill
        ▼
GitHub Actions (orchestrateur) — déclenché par un service de cron externe
        ▼
STOCKAGE
  raw/    JSON bruts, un fichier par ville et par appel, jamais modifiés
  clean/  clean/aqi_data.csv — reconstruit intégralement à chaque run depuis raw/
        ▼
DATA WAREHOUSE (PostgreSQL)
  Schéma en étoile : FactAirQuality + DimCity + DimTemps

## Stack choisie et justification

| Composant | Choix | Justification |
|---|---|---|
| Source de données | [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) | API gratuite, sans clé requise pour ce niveau d'usage, couverture mondiale y compris Madagascar, historique disponible pour le backfill. |
| Langage de collecte/transformation | Python (requests, pandas) | Écosystème mature pour l'ingestion et le nettoyage de données tabulaires, lisible pour l'ensemble du groupe. |
| Orchestrateur | GitHub Actions, déclenché toutes les heures par un service de cron externe (cron-job.org) appelant workflow_dispatch via l'API GitHub | Le déclencheur natif schedule: cron de GitHub Actions n'est pas garanti à l'heure pile (retards observés jusqu'à plusieurs heures sous charge de la plateforme). Un appel externe précis à :01 chaque heure donne une cadence fiable, vérifiable dans l'historique des Actions du dépôt. |
| Stockage brut | Fichiers JSON dans raw/<ville>/, un fichier par appel API | Conserve la réponse API telle quelle (traçabilité, rejouabilité), jamais réécrit après création. |
| Stockage nettoyé | clean/aqi_data.csv, régénéré intégralement à chaque run par clean.py | Reconstruire depuis raw/ plutôt qu'ajouter (append) élimine tout risque de dérive entre raw/ et clean/, et rend la déduplication triviale (drop_duplicates sur l'ensemble complet). |
| Base de données warehouse | PostgreSQL (hébergé sur Neon) | Base relationnelle standard, gratuite pour ce volume, compatible avec psycopg2, accessible à distance (consommation "au fil de l'eau" exigée par le sujet). |
| Modélisation | Schéma en étoile (1 table de faits + 2 dimensions) | Le volume et la complexité du projet (une seule mesure horaire par ville, pas de hiérarchies imbriquées à normaliser) ne justifient pas un flocon ; l'étoile est plus simple à interroger. |

## Modèle dimensionnel

### DimCity (dimension ville)
| Colonne | Type | Description |
|---|---|---|
| id_city | SERIAL PK | Identifiant technique |
| city_name | TEXT | Nom de la ville |
| country | TEXT | Pays (Madagascar pour toutes) |
| latitude | FLOAT | Latitude |
| longitude | FLOAT | Longitude |

### DimTemps (dimension temps)
| Colonne | Type | Description |
|---|---|---|
| id_temps | SERIAL PK | Identifiant technique |
| date | DATE | Jour civil (une ligne par jour, réutilisée par toutes les heures/villes) |
| heure | SMALLINT | Heure de la mesure (0–23) |
| jour_semaine | TEXT | Nom du jour (lundi, mardi, ...) |
| est_weekend | BOOLEAN | TRUE si samedi/dimanche |

Contrainte d'unicité : (date, heure) — une seule ligne par combinaison jour+heure, indépendamment de la ville (la dimension temps est partagée entre toutes les villes, conformément aux règles de modélisation : pas de duplication de la grille temporelle par ville).

### FactAirQuality (table de faits)
| Colonne | Type | Description |
|---|---|---|
| id_fact | SERIAL PK | Identifiant technique |
| id_city | INT FK → DimCity | Ville concernée |
| id_temps | INT FK → DimTemps | Horodatage de la mesure |
| pm10 | FLOAT | Particules PM10 (µg/m³) |
| pm2_5 | FLOAT | Particules PM2.5 (µg/m³) |
| carbon_monoxide | FLOAT | Monoxyde de carbone (µg/m³) |
| nitrogen_dioxide | FLOAT | Dioxyde d'azote (µg/m³) |
| sulphur_dioxide | FLOAT | Dioxyde de soufre (µg/m³) |
| ozone | FLOAT | Ozone (µg/m³) |
| us_aqi | INT | Indice de qualité de l'air (échelle US AQI, 0–500+) |

Contrainte d'unicité : (id_city, id_temps) — une seule mesure par ville et par heure.

Aucune colonne descriptive (nom de ville, date lisible, etc.) n'est stockée dans FactAirQuality : uniquement des mesures et des clés étrangères, conformément aux règles du cours. Aucune mesure n'est stockée dans les dimensions.

**État d'implémentation au 31/07/2026 :** le script `load_warehouse.py` actuel du dépôt utilise encore une version antérieure du schéma (`DimDate` sans dimension heure séparée, timestamp complet utilisé comme clé de la dimension date). Cette page documente le schéma **cible/corrigé** ; la mise à jour de `load_warehouse.py` et de `database/schema.sql` pour s'y conformer est en cours (voir issues du dépôt).


## Ce qui n'a volontairement pas été retenu

- *n8n* a été exploré par un membre du groupe (workflow exporté dans workflows/) mais n'est *pas* l'orchestrateur officiel de ce projet : il écrit sur le système de fichiers local d'un poste individuel, ce qui le rend invérifiable par un correcteur externe (contrainte explicite du sujet : "un livrable invérifiable = zéro"). Il est conservé dans le dépôt à titre exploratoire.
- *Schéma en flocon* : écarté, la faible complexité des dimensions (2 dimensions, pas de sous-hiérarchies à normaliser comme "région > pays") ne le justifiait pas.