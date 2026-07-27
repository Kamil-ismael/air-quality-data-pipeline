# Déploiement & hébergement

Ce document résume les choix d'hébergement pour faire tourner le pipeline en
continu, et pour la base de données en ligne (voir aussi `ARCHITECTURE.md`
et `README.md`).

## Tester en local avant de pousser en ligne

```bash
# Airflow (Docker Compose) — voir dags/aqi_pipeline_dag.py
docker compose up airflow-init
docker compose up -d
```

Mettre les vraies valeurs dans `.env` local (jamais commité) :
`OWM_API_KEY`, `DATABASE_URL`. On peut pointer `DATABASE_URL` vers la base
en ligne (Supabase, voir plus bas) dès la phase de test local, pour valider
le chargement réel sans encore rien pousser sur GitHub.

Une fois que le DAG tourne correctement en local (`localhost:8080`), on
pousse `dags/`, `src/`, `docker-compose.yaml` — jamais `.env`.

## Orchestrateur : où le faire tourner 24h/24 ?

| Solution | Gratuit ? | Limite principale |
|---|---|---|
| **GitHub Actions** (recommandé, déjà en place) | Oui, sans condition | N'est pas "Airflow" à proprement parler, mais aucun serveur à gérer, aucune coupure possible |
| Oracle Cloud Always Free (VM ARM) | Oui sur le papier | Carte bancaire exigée à l'inscription ; capacité parfois indisponible selon la région ; instance parfois réclamée si jugée inactive |
| Google Cloud e2-micro Always Free | Oui | Carte bancaire exigée ; une seule VM par compte ; régions limitées (us-west1 / us-central1 / us-east1) |
| Render / Railway / Fly.io (free) | Partiel | Crédits limités ou mise en veille après inactivité, pas fiable pour un cron continu 24h/24 |

**Recommandation** : garder GitHub Actions comme orchestrateur de production
(déjà fonctionnel, zéro serveur, zéro risque de coupure) et n'utiliser
Airflow qu'en local, pour la démonstration/le test, sauf si le sujet exige
explicitement un déploiement Airflow en continu — dans ce cas, GCP e2-micro
est un peu plus fiable qu'Oracle en pratique.

## Base de données en ligne : Supabase (Postgres gratuit)

- 500 Mo de stockage gratuit — largement suffisant pour 5 villes ×
  plusieurs mois de données horaires.
- Accessible depuis n'importe où via une `DATABASE_URL` standard : par
  `load_warehouse.py`, par IA1 pour requêter, ou en local pour tester.
- Un projet Supabase se met en pause après 7 jours sans activité — mais
  comme le pipeline écrit dedans toutes les heures, ce cas ne se produit
  jamais tant que le pipeline tourne.

Setup :
1. Créer un compte sur supabase.com, nouveau projet.
2. Récupérer la chaîne de connexion : *Project Settings → Database →
   Connection string* (mode "Session" ou "Transaction pooler").
3. La coller dans `DATABASE_URL` (local `.env`, GitHub Secrets, et/ou
   Airflow Variable).
4. Lancer `python src/load_warehouse.py` une fois : les tables `dim_city`,
   `dim_time`, `fact_aqi` sont créées automatiquement (le script exécute
   `src/schema.sql`).

Alternative : **Neon** (Postgres serverless, se réveille automatiquement à
la première connexion) — un peu plus tolérant à l'inactivité, mais
Supabase reste plus simple à prendre en main pour ce projet.
