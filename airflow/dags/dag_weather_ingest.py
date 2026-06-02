"""
DAG: dag_weather_ingest
Frequência: a cada 6h (01:00, 07:00, 13:00, 19:00 BRT / 04:00, 10:00, 16:00, 22:00 UTC)
            Executa ~30min após a coleta (dag_weather_collection) para garantir
            que os dados já estão no PostgreSQL.

Responsabilidade:
  Replica as tabelas raw.open_meteo_daily e raw.open_meteo_hourly
  do PostgreSQL para o BigQuery (dataset: weather_raw).
  Substitui o Airbyte com lógica incremental baseada em _extracted_at.
"""

import os
from datetime import datetime, timedelta

import datetime as dt
from decimal import Decimal

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator
from google.cloud import bigquery
from google.oauth2 import service_account


# ─── Configuração ────────────────────────────────────────────────────────────

PG_CONFIG = {
    "host":     os.environ.get("POSTGRES_HOST", "weather_postgres"),
    "port":     int(os.environ.get("POSTGRES_PORT", "5432")),
    "dbname":   os.environ.get("POSTGRES_DB", "weather_staging"),
    "user":     os.environ.get("POSTGRES_USER", "weather_user"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
}

GCP_PROJECT    = os.environ.get("GCP_PROJECT_ID", "")
BQ_DATASET     = "weather_raw"
BQ_LOCATION    = os.environ.get("BIGQUERY_LOCATION", "southamerica-east1")
GCP_KEYFILE    = "/secrets/gcp.json"

TABLES = ["open_meteo_daily", "open_meteo_hourly"]

# Colunas a selecionar do PostgreSQL (exclui colunas internas como 'id')
TABLE_COLUMNS = {
    "open_meteo_daily": [
        "location_id", "date", "latitude", "longitude",
        "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
        "rain_sum", "wind_speed_10m_max", "sunrise", "sunset",
        "uv_index_max", "_extracted_at",
    ],
    "open_meteo_hourly": [
        "location_id", "timestamp", "latitude", "longitude", "elevation",
        "timezone", "temperature_2m", "relative_humidity_2m", "precipitation",
        "wind_speed_10m", "wind_direction_10m", "surface_pressure",
        "cloud_cover", "visibility", "weather_code", "_extracted_at",
    ],
}

# ─── Schema BigQuery por tabela ──────────────────────────────────────────────
# O schema é inferido dinamicamente do PostgreSQL — definimos apenas os tipos
# que o BigQuery não consegue inferir automaticamente de strings.

BQ_SCHEMA = {
    "open_meteo_daily": [
        bigquery.SchemaField("location_id",         "STRING"),
        bigquery.SchemaField("date",                "DATE"),
        bigquery.SchemaField("latitude",            "FLOAT64"),
        bigquery.SchemaField("longitude",           "FLOAT64"),
        bigquery.SchemaField("temperature_2m_max",  "FLOAT64"),
        bigquery.SchemaField("temperature_2m_min",  "FLOAT64"),
        bigquery.SchemaField("precipitation_sum",   "FLOAT64"),
        bigquery.SchemaField("rain_sum",            "FLOAT64"),
        bigquery.SchemaField("wind_speed_10m_max",  "FLOAT64"),
        bigquery.SchemaField("sunrise",             "TIMESTAMP"),
        bigquery.SchemaField("sunset",              "TIMESTAMP"),
        bigquery.SchemaField("uv_index_max",        "FLOAT64"),
        bigquery.SchemaField("_extracted_at",       "TIMESTAMP"),
    ],
    "open_meteo_hourly": [
        bigquery.SchemaField("location_id",           "STRING"),
        bigquery.SchemaField("timestamp",             "TIMESTAMP"),
        bigquery.SchemaField("latitude",              "FLOAT64"),
        bigquery.SchemaField("longitude",             "FLOAT64"),
        bigquery.SchemaField("elevation",             "FLOAT64"),
        bigquery.SchemaField("timezone",              "STRING"),
        bigquery.SchemaField("temperature_2m",        "FLOAT64"),
        bigquery.SchemaField("relative_humidity_2m",  "INT64"),
        bigquery.SchemaField("precipitation",         "FLOAT64"),
        bigquery.SchemaField("wind_speed_10m",        "FLOAT64"),
        bigquery.SchemaField("wind_direction_10m",    "INT64"),
        bigquery.SchemaField("surface_pressure",      "FLOAT64"),
        bigquery.SchemaField("cloud_cover",           "INT64"),
        bigquery.SchemaField("visibility",            "FLOAT64"),
        bigquery.SchemaField("weather_code",          "INT64"),
        bigquery.SchemaField("_extracted_at",         "TIMESTAMP"),
    ],
}


# ─── Funções ─────────────────────────────────────────────────────────────────

def get_bq_client():
    credentials = service_account.Credentials.from_service_account_file(GCP_KEYFILE)
    return bigquery.Client(project=GCP_PROJECT, credentials=credentials)


def ensure_dataset(client):
    dataset_ref = bigquery.Dataset(f"{GCP_PROJECT}.{BQ_DATASET}")
    dataset_ref.location = BQ_LOCATION
    client.create_dataset(dataset_ref, exists_ok=True)


def get_last_extracted_at(client, table_name):
    """Retorna o maior _extracted_at já carregado no BigQuery, ou None."""
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.{table_name}"
    try:
        query = f"SELECT MAX(_extracted_at) as max_ts FROM `{table_id}`"
        result = list(client.query(query).result())
        return result[0].max_ts if result else None
    except Exception:
        return None


def ingest_table(table_name: str):
    """Lê dados incrementais do PostgreSQL e carrega no BigQuery."""
    client = get_bq_client()
    ensure_dataset(client)

    last_ts = get_last_extracted_at(client, table_name)

    # Busca registros novos desde o último _extracted_at
    pg_conn = psycopg2.connect(**PG_CONFIG)
    pg_cursor = pg_conn.cursor()

    cols = ", ".join(TABLE_COLUMNS[table_name])
    if last_ts:
        pg_cursor.execute(
            f"SELECT {cols} FROM raw.{table_name} WHERE _extracted_at > %s ORDER BY _extracted_at",
            (last_ts,)
        )
    else:
        pg_cursor.execute(f"SELECT {cols} FROM raw.{table_name} ORDER BY _extracted_at")

    rows = pg_cursor.fetchall()
    col_names = [desc[0] for desc in pg_cursor.description]
    pg_cursor.close()
    pg_conn.close()

    if not rows:
        print(f"[{table_name}] Nenhum registro novo desde {last_ts}. Pulando.")
        return

    print(f"[{table_name}] {len(rows)} registros novos para carregar.")

    # Converte para lista de dicts serializáveis em JSON
    def serialize(val):
        if isinstance(val, dt.datetime):
            return val.isoformat()
        if isinstance(val, dt.date):
            return val.isoformat()
        if isinstance(val, Decimal):
            return float(val)
        return val

    data = [
        {k: serialize(v) for k, v in zip(col_names, row)}
        for row in rows
    ]

    # Carrega no BigQuery
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        schema=BQ_SCHEMA[table_name],
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )

    job = client.load_table_from_json(data, table_id, job_config=job_config)
    job.result()  # aguarda conclusão

    print(f"[{table_name}] Carregados {len(rows)} registros no BigQuery.")


def ingest_daily(**context):
    ingest_table("open_meteo_daily")


def ingest_hourly(**context):
    ingest_table("open_meteo_hourly")


def verify_ingest(**context):
    """Verifica se ambas as tabelas têm dados recentes no BigQuery."""
    client = get_bq_client()
    errors = []

    for table_name in TABLES:
        table_id = f"{GCP_PROJECT}.{BQ_DATASET}.{table_name}"
        try:
            query = f"""
                SELECT COUNT(*) as total, MAX(_extracted_at) as ultima_carga
                FROM `{table_id}`
                WHERE _extracted_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 HOUR)
            """
            result = list(client.query(query).result())[0]
            if result.total == 0:
                errors.append(f"{table_name}: nenhum registro nas últimas 7h")
            else:
                print(f"[{table_name}] OK — {result.total} registros recentes. Última carga: {result.ultima_carga}")
        except Exception as e:
            errors.append(f"{table_name}: erro ao verificar — {e}")

    if errors:
        raise ValueError("Falha na verificação pós-ingestão:\n" + "\n".join(errors))


# ─── DAG ─────────────────────────────────────────────────────────────────────

default_args = {
    "owner": "analytics",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_weather_ingest",
    default_args=default_args,
    description="Ingestão incremental PostgreSQL → BigQuery (substitui Airbyte)",
    schedule="0 4,10,16,22 * * *",   # 01:00, 07:00, 13:00, 19:00 BRT
    start_date=datetime(2026, 1, 1),
    catchup=False,
    is_paused_upon_creation=True,
    tags=["weather", "bigquery", "ingestao", "postgres"],
) as dag:

    task_ingest_daily = PythonOperator(
        task_id="ingest_daily",
        python_callable=ingest_daily,
    )

    task_ingest_hourly = PythonOperator(
        task_id="ingest_hourly",
        python_callable=ingest_hourly,
    )

    task_verify = PythonOperator(
        task_id="verify_ingest",
        python_callable=verify_ingest,
    )

    [task_ingest_daily, task_ingest_hourly] >> task_verify
