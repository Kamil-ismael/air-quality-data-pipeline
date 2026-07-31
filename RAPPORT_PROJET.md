# Rapport de projet — air-quality-data-pipeline

## Équipe

| Membres | Rôle principal sur le projet répartition des tâches |
|---|---|
| [Ismael] | [collecte + backfill] |
| [Ismael, Antonio] | [nettoyage + validation] |
| [Jose] | [orchestration GitHub Actions] |
| [Vahatra , Lionel] | [warehouse + modélisation] |
| [Antonio ] | [documentation + vidéo] |

## Méthode de travail du groupe

●	Division des tâches à accomplir en amont, avant que chaque membre ne travaille sur son périmètre (rôle) dédié.

●	Certaines tâches ont été effectuées conjointement entre plusieurs membres (ex. stockage & nettoyage).

●	Utilisation de GitHub comme outil de travail collaboratif commun : dépôt partagé, gestion du code et du workflow d'exécution (GitHub Actions).

## Choix techniques et justifications

| Composant | Choix | Justification |
|---|---|---|
| Source de données | [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) | API gratuite, sans clé requise pour ce niveau d'usage, couverture mondiale y compris Madagascar, historique disponible pour le backfill. |
| Langage de collecte/transformation | Python (requests, pandas) | Écosystème mature pour l'ingestion et le nettoyage de données tabulaires, lisible pour l'ensemble du groupe. |
| Orchestrateur | GitHub Actions, déclenché toutes les heures par un service de cron externe (cron-job.org) appelant workflow_dispatch via l'API GitHub | Le déclencheur natif schedule: cron de GitHub Actions n'est pas garanti à l'heure pile (retards observés jusqu'à plusieurs heures sous charge de la plateforme). Un appel externe précis à :01 chaque heure donne une cadence fiable, vérifiable dans l'historique des Actions du dépôt. |
| Stockage brut | Fichiers JSON dans raw/<ville>/, un fichier par appel API | Conserve la réponse API telle quelle (traçabilité, rejouabilité), jamais réécrit après création. |
| Stockage nettoyé | clean/aqi_data.csv, régénéré intégralement à chaque run par clean.py | Reconstruire depuis raw/ plutôt qu'ajouter (append) élimine tout risque de dérive entre raw/ et clean/, et rend la déduplication triviale (drop_duplicates sur l'ensemble complet). |
| Base de données warehouse | PostgreSQL (hébergé sur Neon) | Base relationnelle standard, gratuite pour ce volume, compatible avec psycopg2, accessible à distance (consommation "au fil de l'eau" exigée par le sujet). |
| Modélisation | Schéma en étoile (1 table de faits + 2 dimensions) | Le volume et la complexité du projet (une seule mesure horaire par ville, pas de hiérarchies imbriquées à normaliser) ne justifient pas un flocon ; l'étoile est plus simple à interroger.

## Difficultés rencontrées et solutions

- **Fiabilité du déclenchement horaire.** Le scheduler natif de GitHub Actions (`cron`) ne se déclenchait pas de façon suffisamment précise (retards observés). Solution retenue : déclenchement via un service de cron externe appelant `workflow_dispatch` par l'API GitHub. 
- **Cohérence entre plusieurs pistes d'orchestrateur explorées.** Le groupe a testé une piste less-code (n8n) en parallèle de la piste Python/GitHub Actions avant de trancher pour la seconde. L'orchéstration via n8n était simplifiée mais il y a eu quelques difficultés au cours du partage de projet, ce qui a valu de retenir Github Actions comme Orchestrateur final. 