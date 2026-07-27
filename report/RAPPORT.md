# Rapport de projet — Pipeline AQI

## Équipe et répartition des tâches

| Membre | Tâches principales |
|---|---|
| ... | ... |

## Méthode de travail

- Fréquence des points d'équipe :
- Outil de gestion de tâches (Trello, GitHub Projects, etc.) :
- Convention de commits / branches :

## Choix techniques justifiés

- Pourquoi cette API plutôt qu'une autre :
- Pourquoi cet orchestrateur :
- Pourquoi ce warehouse / cette modélisation :

## Difficultés rencontrées et solutions

| Difficulté | Solution apportée |
|---|---|
| ... | ... |

## Preuves d'automatisation

- Lien vers l'onglet Actions du repo :
- Captures d'écran des runs réussis sur ≥ 5 jours différents : (à insérer)

## Requête SQL de démonstration

```sql
-- Exemple : évolution de l'AQI moyen par ville sur les 7 derniers jours
SELECT c.name, d.date, ROUND(AVG(f.aqi), 2) AS aqi_moyen
FROM fact_aqi f
JOIN dim_city c ON c.city_id = f.city_id
JOIN dim_time d ON d.time_id = f.time_id
WHERE d.date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY c.name, d.date
ORDER BY d.date, c.name;
```
