# Pipeline Qualité de l'Air — n8n + Open-Meteo + PostgreSQL (Neon)

Pipeline de collecte automatisée de la qualité de l'air (toutes les 3h) pour 5 villes de Madagascar : Antananarivo, Toamasina, Mahajanga, Fianarantsoa, Antsiranana.

## ⚠️ Prérequis avant d'importer le workflow

Ce workflow utilise le Code node en JavaScript avec accès au système de fichiers (`fs`, `path`) et aux variables d'environnement. Ces accès sont **désactivés par défaut** depuis n8n 2.x et doivent être activés manuellement.

### 1. Variables d'environnement à définir

Sur Windows, ouvrir **cmd** et exécuter :

```cmd
setx N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES "false"
setx NODE_FUNCTION_ALLOW_BUILTIN "fs,path"
setx N8N_BLOCK_ENV_ACCESS_IN_NODE "false"
```

Fermer et rouvrir le terminal, puis relancer n8n avec `n8n start`.

Sur Mac/Linux, utiliser `export` dans le fichier de configuration du shell (`.bashrc`, `.zshrc`) à la place de `setx`.

### 2. Adapter le chemin du data lake local

Dans le node **"Code (villes)"**, modifier uniquement cette ligne selon votre système :

```javascript
const config = {
  baseDir: 'C:\\n8n-datalake\\raw'  // Windows
  // baseDir: '/Users/votre-nom/n8n-datalake/raw'  // Mac
  // baseDir: '/home/votre-nom/n8n-datalake/raw'   // Linux
};
```

Créer ensuite ce dossier s'il n'existe pas déjà.

### 3. Créer ses propres credentials Postgres (Neon)

L'export du workflow ne contient **jamais** les mots de passe. Chaque personne doit créer sa propre credential :

1. n8n → **Credentials** → **New** → **Postgres**
2. Renseigner Host / Database / User / Password fournis par Neon
3. Activer **SSL** (obligatoire pour Neon)
4. Dans le node Postgres du workflow, sélectionner cette credential


## Architecture

```
[Schedule Trigger (3h)]
        ↓
[Code JS → Liste des villes + config baseDir]
        ↓
[HTTP Request → Open-Meteo Air Quality API]
        ↓
[Code JS → Création dossiers + écriture RAW via fs]
        ↓
[Code JS → Nettoyage + dédoublonnage + filtre historique]
        ↓
[Postgres (Neon) → Insertion dans le modèle en étoile]
```

## Structure de la base (schéma en étoile)

Voir `database/schema.sql` pour la création complète des tables `dim_city`, `dim_date`, `dim_time`, `fact_air_quality`.

## Erreurs connues et déjà résolues

| Erreur | Cause | Solution |
|---|---|---|
| `Python runner unavailable: Virtual environment is missing` | Bug n8n 2.x npm/Windows | Utiliser JavaScript au lieu de Python dans le Code node |
| `Execute Command` node introuvable | Désactivé par défaut depuis n8n 2.0 | Utiliser `fs.mkdirSync` dans le Code node JS |
| `Module 'fs' is disallowed` | Sécurité n8n 2.x | Variable d'environnement `NODE_FUNCTION_ALLOW_BUILTIN=fs,path` |
| `process is not defined` | Sécurité n8n 2.x | Variable d'environnement `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` |
| `The file "..." is not writable` | Bug connu du node "Read/Write Files from Disk" sur Windows | Écrire directement avec `fs.writeFileSync` dans le Code node, sans passer par ce node |

## Notes sur les données API

- `forecast_days=1` est utilisé pour limiter les prévisions futures (minimum accepté par l'API)
- Un filtre supplémentaire dans le node de nettoyage exclut les timestamps futurs (`new Date(r.timestamp) <= now`), pour ne conserver que des mesures réellement passées dans `fact_air_quality`
