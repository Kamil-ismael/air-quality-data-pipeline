"""DAG Airflow — pipeline AQI horaire.

Reprend exactement les mêmes scripts que le workflow GitHub Actions
(src/fetch_current.py, src/build_clean.py, src/load_warehouse.py),
mais orchestrés par le scheduler Airflow plutôt que par le cron GitHub.

Prérequis Airflow (à faire une fois, dans l'UI ou en CLI) :
  Admin > Variables :
    - OWM_API_KEY   -> votre clé OpenWeatherMap
    - DATABASE_URL  -> ex: postgresql://user:password@host:5432/dbname

Le dossier src/ du projet doit être monté/copié dans /opt/airflow/src
(voir docker-compose.yaml et le README pour le montage du volume).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

SRC_PATH = "/opt/airflow/src"
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

default_args = {
    "owner": "aqi-team",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def task_fetch_current(**context) -> None:
    os.environ["OWM_API_KEY"] = Variable.get("OWM_API_KEY")
    import fetch_current  # import local : l'env var doit être posée avant
    fetch_current.main()


def task_build_clean(**context) -> None:
    import build_clean
    build_clean.main()


def task_load_warehouse(**context) -> None:
    os.environ["DATABASE_URL"] = Variable.get("DATABASE_URL")
    import load_warehouse
    load_warehouse.main()


with DAG(
    dag_id="aqi_pipeline",
    description="Collecte horaire AQI -> clean/ -> data warehouse Postgres",
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 * * * *",  # toutes les heures, comme le cron GitHub Actions
    catchup=False,       # ne pas rejouer tous les runs manqués depuis start_date
    max_active_runs=1,   # évite deux runs qui se chevauchent
    default_args=default_args,
    tags=["aqi", "etl"],
) as dag:

    fetch = PythonOperator(task_id="fetch_current", python_callable=task_fetch_current)
    clean = PythonOperator(task_id="build_clean", python_callable=task_build_clean)
    load = PythonOperator(task_id="load_warehouse", python_callable=task_load_warehouse)

    fetch >> clean >> load
