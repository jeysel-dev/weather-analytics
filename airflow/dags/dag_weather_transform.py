"""
DAG: dag_weather_transform
Frequência: diária às 07:30 BRT (10:30 UTC)
             Executa após o Airbyte ter sincronizado os dados do turno das 06:30
             do PostgreSQL para o BigQuery (Airbyte schedule: a cada 6h).

Responsabilidade:
  Executa o pipeline dbt completo no target `prod` (BigQuery).
  Substitui o `docker compose run --rm dbt-build` manual.
# ─── Comando base dbt ────────────────────────────────────────────────────────
# /opt/dbt é o project-dir (montado via volume)
# /home/airflow/.dbt é o profiles-dir (montado via ${DBT_PROFILES_DIR})
"""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


DBT_CMD = "cd /opt/dbt && dbt {subcommand} --profiles-dir /home/airflow/.dbt --target prod --log-path /tmp/dbt-logs --target-path /tmp/dbt-target"

# ─── Variáveis de ambiente compartilhadas pelos BashOperators ───────────────
DBT_ENV = {
    "GOOGLE_APPLICATION_CREDENTIALS": "/secrets/gcp.json",
    "GCP_PROJECT_ID":                 os.environ.get("GCP_PROJECT_ID", ""),
    "BIGQUERY_DATASET":               os.environ.get("BIGQUERY_DATASET", "weather_dw"),
    "BIGQUERY_LOCATION":              os.environ.get("BIGQUERY_LOCATION", "southamerica-east1"),
    # Conexão PostgreSQL (usada pelo target dev, mantida por compatibilidade)
    "POSTGRES_HOST":                  os.environ.get("POSTGRES_HOST", "weather_postgres"),
    "POSTGRES_PORT":                  os.environ.get("POSTGRES_PORT", "5432"),
    "POSTGRES_DB":                    os.environ.get("POSTGRES_DB",   "weather_staging"),
    "POSTGRES_USER":                  os.environ.get("POSTGRES_USER", "weather_user"),
    "POSTGRES_PASSWORD":              os.environ.get("POSTGRES_PASSWORD", ""),
    "DBT_SOURCE_DATABASE":            os.environ.get("DBT_SOURCE_DATABASE", "weather_staging"),
    "DBT_SOURCE_SCHEMA":              os.environ.get("DBT_SOURCE_SCHEMA", "raw"),
}


# ─── DAG ────────────────────────────────────────────────────────────────────

default_args = {
    "owner": "analytics",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_weather_transform",
    default_args=default_args,
    description="dbt build diário: seed → run → test (BigQuery/prod)",
     
    schedule="30 10 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    is_paused_upon_creation=True,
    sla_miss_callback=None,
    tags=["weather", "dbt", "bigquery", "transformacao"],
) as dag:

 
    task_dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=DBT_CMD.format(subcommand="seed --show"),
        env=DBT_ENV,
        append_env=True,
    )

     
    task_dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=DBT_CMD.format(subcommand="run"),
        env=DBT_ENV,
        append_env=True,
         
        sla=timedelta(minutes=30),
    )

  
    task_dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=DBT_CMD.format(subcommand="test"),
        env=DBT_ENV,
        append_env=True,
    )

    task_dbt_seed >> task_dbt_run >> task_dbt_test
