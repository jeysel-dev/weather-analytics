"""
DAG: dag_weather_collection
Frequência: 4x por dia às 00:30, 06:30, 12:30 e 18:30 BRT
             (cron em UTC — BRT = UTC-3: 03:30, 09:30, 15:30, 21:30)

Responsabilidade:
  Coleta dados meteorológicos de todos os 295 municípios de Santa Catarina
  via API Open-Meteo e faz UPSERT no PostgreSQL (weather_staging.raw.*).
  As localidades são carregadas do seed dbt/seeds/locations.csv (montado em /opt/dbt).
"""

import os
import logging
from datetime import datetime, timedelta, date, timezone

import psycopg2
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)




def verify_rows_inserted(**context) -> None:
    """
    Confirma que o collector inseriu/atualizou registros nos últimos 30 minutos.
    Falha a task (e dispara retry) caso nenhuma linha seja encontrada.
    """
    janela_minutos = 30
    limite = datetime.now(timezone.utc) - timedelta(minutes=janela_minutos)

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM raw.open_meteo_hourly WHERE _extracted_at >= %s",
                (limite,),
            )
            qtd_hourly = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM raw.open_meteo_daily WHERE _extracted_at >= %s",
                (limite,),
            )
            qtd_daily = cur.fetchone()[0]
    finally:
        conn.close()

    log.info(
        "Linhas inseridas nos últimos %d min — hourly: %d | daily: %d",
        janela_minutos, qtd_hourly, qtd_daily,
    )

    if qtd_hourly == 0 and qtd_daily == 0:
        raise ValueError(
            f"Nenhuma linha inserida nos últimos {janela_minutos} minutos. "
            "Verifique os logs da task collect_open_meteo."
        )




default_args = {
    "owner": "analytics",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_weather_collection",
    default_args=default_args,
    description="Coleta Open-Meteo 4x/dia → PostgreSQL (substitui container collector --mode scheduled)",
    
    schedule="30 3,9,15,21 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    is_paused_upon_creation=True,
    tags=["weather", "coleta", "open-meteo", "postgresql"],
) as dag:


    task_collect = BashOperator(
        task_id="collect_open_meteo",
        bash_command="python3 /opt/collector/collector.py --mode once",
        env={
            
            "POSTGRES_HOST":     os.environ.get("POSTGRES_HOST", "weather_postgres"),
            "POSTGRES_PORT":     os.environ.get("POSTGRES_PORT", "5432"),
            "POSTGRES_DB":       os.environ.get("POSTGRES_DB",   "weather_staging"),
            "POSTGRES_USER":     os.environ.get("POSTGRES_USER", "weather_user"),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        },
        append_env=True,
    )

   
    task_verify = PythonOperator(
        task_id="verify_rows_inserted",
        python_callable=verify_rows_inserted,
    )

    task_collect >> task_verify
