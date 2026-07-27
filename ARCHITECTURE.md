# Architecture

## Stack choisie

| Composant       | Choix                                   | Justification |
|------------------|------------------------------------------|----------------|
| **API source**   | OpenWeatherMap Air Pollution API          | Fournit l'AQI et 8 polluants, avec un endpoint `history` permettant un vrai backfill (données depuis nov. 2020), contrairement à des APIs "temps réel uniquement". |
| **Orchestrateur**| GitHub Actions (cron horaire)             | Gratuit, déjà lié au dépôt Git, workflow versionné en YAML, historique des runs consultable directement dans l'onglet Actions (preuve d'automatisation exigée par la consigne). |
| **Stockage raw/clean** | Fichiers dans le dépôt Git (`data/raw/`, `data/clean/`) | Simple, versionné, inspectable sans infra supplémentaire ; `raw/` n'est jamais réécrit, `clean/` est régénéré à chaque run par `build_clean.py`. |
| **Langage pipeline** | Python 3.11                            | Écosystème mature pour l'ETL (requests, csv, psycopg2), facile à relire et à tester. |
| **Data warehouse**| PostgreSQL hébergé (ex : Supabase ou Neon, offre gratuite) | Base relationnelle standard, accessible via `DATABASE_URL` depuis n'importe où (dont le cours IA1), supporte nativement les contraintes de clé étrangère du schéma en étoile. |
| **Modélisation**  | Schéma en étoile : `fact_aqi` + `dim_time` + `dim_city` | Le cas est simple (une seule granularité de mesure), un flocon n'apporterait pas de valeur ; respecte la règle "pas de mesure dans les dimensions, pas de descriptif dans les faits". |

## Flux de données

```
OpenWeatherMap Air Pollution API
        │  fetch_current.py (toutes les heures) + backfill.py (historique)
        ▼
data/raw/<ville>/*.json      (jamais modifié)
        │  build_clean.py (rejoue tout raw/, dédoublonne, trie)
        ▼
data/clean/aqi_data.csv      (reconstruit à chaque run)
        │  load_warehouse.py (upsert idempotent)
        ▼
PostgreSQL : dim_city, dim_time, fact_aqi
```

## Pourquoi ce découpage tient les règles du jeu

- **Clé API en secret** : `OWM_API_KEY` et `DATABASE_URL` ne sont lus que via `os.environ`, jamais écrits en dur. En CI ils sont injectés depuis les GitHub Secrets.
- **raw/ intouchable** : aucun script n'ouvre un fichier de `raw/` en écriture après sa création ; seul `build_clean.py` les lit.
- **clean/ reconstruit à chaque run** : `build_clean.py` réécrit entièrement le CSV depuis zéro à chaque exécution, pas d'append.
- **Warehouse rejouable** : `load_warehouse.py` utilise `ON CONFLICT ... DO UPDATE/DO NOTHING`, donc le recharger plusieurs fois ne duplique rien.
