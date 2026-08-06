#!/usr/bin/env python3
"""
ingest.py
---------
Coleta dados da API Open-Meteo para os 295 municípios de SC
e grava diretamente no BigQuery (dataset: weather_raw).

Substitui o fluxo Airflow em dois passos (Open-Meteo→PostgreSQL→BigQuery)
por uma etapa direta: Open-Meteo → BigQuery.

Uso:
  python ingest.py                        # últimos 2 dias (padrão)
  python ingest.py --days 7               # últimos 7 dias
  python ingest.py --start 2024-01-01 --end 2024-12-31  # backfill
"""

import os
import csv
import argparse
import logging
import sys
from datetime import datetime, date, timedelta, timezone
from typing import Generator

import requests
from google.cloud import bigquery
from google.oauth2 import service_account

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Configuração ─────────────────────────────────────────────────────────────

API_BASE    = "https://api.open-meteo.com/v1"
API_TIMEOUT = 30

GCP_PROJECT = os.environ.get("GCP_PROJECT_ID", "")
BQ_DATASET  = os.environ.get("BIGQUERY_RAW_DATASET", "weather_raw")
BQ_LOCATION = os.environ.get("BIGQUERY_LOCATION", "southamerica-east1")

HOURLY_VARS = (
    "temperature_2m,relative_humidity_2m,precipitation,"
    "wind_speed_10m,wind_direction_10m,surface_pressure,"
    "cloud_cover,visibility,weather_code"
)

DAILY_VARS = (
    "temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "rain_sum,wind_speed_10m_max,sunrise,sunset,uv_index_max"
)

# ── Schema BigQuery ──────────────────────────────────────────────────────────

BQ_SCHEMA = {
    "open_meteo_daily": [
        bigquery.SchemaField("location_id",         "STRING",  mode="REQUIRED"),
        bigquery.SchemaField("date",                "DATE",    mode="REQUIRED"),
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
        bigquery.SchemaField("location_id",           "STRING",    mode="REQUIRED"),
        bigquery.SchemaField("timestamp",             "TIMESTAMP", mode="REQUIRED"),
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

# ── Localidades ──────────────────────────────────────────────────────────────

def load_locations() -> list:
    candidates = [
        os.environ.get("LOCATIONS_CSV", ""),
        "/app/dbt/seeds/locations.csv",
        os.path.join(os.path.dirname(__file__), "../dbt/seeds/locations.csv"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            locations = []
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    locations.append({
                        "id":  row["location_id"],
                        "lat": float(row["latitude"]),
                        "lon": float(row["longitude"]),
                    })
            log.info(f"Carregados {len(locations)} municípios de {path}")
            return locations
    raise FileNotFoundError(
        "locations.csv não encontrado. Defina LOCATIONS_CSV ou rode dentro do container."
    )

# ── Open-Meteo API ────────────────────────────────────────────────────────────

def fetch_forecast(location: dict, start_date: str, end_date: str) -> dict:
    resp = requests.get(
        f"{API_BASE}/forecast",
        params={
            "latitude":   location["lat"],
            "longitude":  location["lon"],
            "hourly":     HOURLY_VARS,
            "daily":      DAILY_VARS,
            "timezone":   "America/Sao_Paulo",
            "start_date": start_date,
            "end_date":   end_date,
        },
        timeout=API_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()

# ── Flatten ───────────────────────────────────────────────────────────────────

def _norm_ts(s) -> str | None:
    """Normaliza string de datetime para formato TIMESTAMP aceito pelo BigQuery."""
    if s is None:
        return None
    s = str(s)
    if len(s) == 16:  # "YYYY-MM-DDTHH:MM" → adiciona segundos
        s = s + ":00"
    # Substitui T por espaço para formato BigQuery TIMESTAMP
    return s.replace("T", " ")


def iter_hourly(raw: dict, location_id: str, extracted_at: str) -> Generator[dict, None, None]:
    hourly = raw.get("hourly", {})
    times  = hourly.get("time", [])
    for i, ts in enumerate(times):
        yield {
            "location_id":          location_id,
            "timestamp":            _norm_ts(ts),
            "latitude":             raw.get("latitude"),
            "longitude":            raw.get("longitude"),
            "elevation":            raw.get("elevation"),
            "timezone":             raw.get("timezone"),
            "temperature_2m":       hourly.get("temperature_2m",       [None] * len(times))[i],
            "relative_humidity_2m": hourly.get("relative_humidity_2m", [None] * len(times))[i],
            "precipitation":        hourly.get("precipitation",         [None] * len(times))[i],
            "wind_speed_10m":       hourly.get("wind_speed_10m",        [None] * len(times))[i],
            "wind_direction_10m":   hourly.get("wind_direction_10m",    [None] * len(times))[i],
            "surface_pressure":     hourly.get("surface_pressure",      [None] * len(times))[i],
            "cloud_cover":          hourly.get("cloud_cover",           [None] * len(times))[i],
            "visibility":           hourly.get("visibility",            [None] * len(times))[i],
            "weather_code":         hourly.get("weather_code",          [None] * len(times))[i],
            "_extracted_at":        extracted_at,
        }


def iter_daily(raw: dict, location_id: str, extracted_at: str) -> Generator[dict, None, None]:
    daily = raw.get("daily", {})
    dates = daily.get("time", [])
    for i, d in enumerate(dates):
        yield {
            "location_id":        location_id,
            "date":               d,
            "latitude":           raw.get("latitude"),
            "longitude":          raw.get("longitude"),
            "temperature_2m_max": daily.get("temperature_2m_max", [None] * len(dates))[i],
            "temperature_2m_min": daily.get("temperature_2m_min", [None] * len(dates))[i],
            "precipitation_sum":  daily.get("precipitation_sum",  [None] * len(dates))[i],
            "rain_sum":           daily.get("rain_sum",            [None] * len(dates))[i],
            "wind_speed_10m_max": daily.get("wind_speed_10m_max",  [None] * len(dates))[i],
            "sunrise":            _norm_ts(daily.get("sunrise",  [None] * len(dates))[i]),
            "sunset":             _norm_ts(daily.get("sunset",   [None] * len(dates))[i]),
            "uv_index_max":       daily.get("uv_index_max",        [None] * len(dates))[i],
            "_extracted_at":      extracted_at,
        }

# ── BigQuery ──────────────────────────────────────────────────────────────────

def get_bq_client() -> bigquery.Client:
    # Credencial explícita (não ADC): pipeline e dashboard agora usam service
    # accounts distintas no mesmo ambiente, então não dá para depender da
    # credencial "default" implícita.
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_PIPELINE")
    if not key_path:
        raise EnvironmentError(
            "GOOGLE_APPLICATION_CREDENTIALS_PIPELINE não definido. Aponte "
            "para o JSON da service account do pipeline/dbt."
        )
    credentials = service_account.Credentials.from_service_account_file(key_path)
    return bigquery.Client(project=GCP_PROJECT, credentials=credentials)


def ensure_dataset(client: bigquery.Client):
    dataset_ref = bigquery.Dataset(f"{GCP_PROJECT}.{BQ_DATASET}")
    dataset_ref.location = BQ_LOCATION
    client.create_dataset(dataset_ref, exists_ok=True)


def ensure_table(client: bigquery.Client, table_name: str):
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.{table_name}"
    table = bigquery.Table(table_id, schema=BQ_SCHEMA[table_name])
    table.clustering_fields = ["location_id"]
    if table_name == "open_meteo_daily":
        # Sem expiração: mart_climate__daily_facts é reconstruída via full
        # rebuild (materialized='table') e depende do histórico completo.
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY, field="date",
        )
    else:
        # open_meteo_hourly pode expirar — mart_climate__hourly_facts é
        # incremental e não depende mais do raw para preservar histórico já
        # mesclado. ~450 dias de folga para backfill/debug antes de expirar.
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY, field="timestamp",
            expiration_ms=450 * 24 * 60 * 60 * 1000,
        )
    client.create_table(table, exists_ok=True)


def delete_window(client: bigquery.Client, table_name: str, start_date: str):
    """Remove registros do período que será re-carregado (idempotência)."""
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.{table_name}"
    if table_name == "open_meteo_daily":
        dml = f"DELETE FROM `{table_id}` WHERE `date` >= '{start_date}'"
    else:
        dml = f"DELETE FROM `{table_id}` WHERE `timestamp` >= '{start_date}T00:00:00'"
    client.query(dml).result()
    log.info(f"Deletados registros de {table_name} a partir de {start_date}")


def insert_rows(client: bigquery.Client, table_name: str, records: list):
    if not records:
        log.warning(f"Nenhum registro para inserir em {table_name}")
        return
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        schema=BQ_SCHEMA[table_name],
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    job = client.load_table_from_json(records, table_id, job_config=job_config)
    job.result()
    log.info(f"Inseridos {len(records)} registros em {table_name}")

# ── Coleta principal ──────────────────────────────────────────────────────────

def run(start_date: str, end_date: str):
    if not GCP_PROJECT:
        log.error("GCP_PROJECT_ID não definido")
        sys.exit(1)

    locations = load_locations()
    client = get_bq_client()

    log.info(f"Preparando dataset {GCP_PROJECT}.{BQ_DATASET}...")
    ensure_dataset(client)
    ensure_table(client, "open_meteo_daily")
    ensure_table(client, "open_meteo_hourly")

    delete_window(client, "open_meteo_daily",  start_date)
    delete_window(client, "open_meteo_hourly", start_date)

    log.info(f"Coletando {start_date} → {end_date} para {len(locations)} municípios...")

    extracted_at = datetime.now(timezone.utc).isoformat()
    all_hourly: list = []
    all_daily:  list = []
    errors = 0

    for loc in locations:
        try:
            raw = fetch_forecast(loc, start_date, end_date)
            all_hourly.extend(iter_hourly(raw, loc["id"], extracted_at))
            all_daily.extend(iter_daily(raw,  loc["id"], extracted_at))
            log.debug(f"  ✓ {loc['id']}")
        except requests.HTTPError as e:
            log.error(f"  ✗ {loc['id']} — HTTP {e.response.status_code}")
            errors += 1
        except Exception as e:
            log.error(f"  ✗ {loc['id']} — {e}")
            errors += 1

    insert_rows(client, "open_meteo_daily",  all_daily)
    insert_rows(client, "open_meteo_hourly", all_hourly)

    log.info(
        f"Ingestão concluída — daily: {len(all_daily)}, "
        f"hourly: {len(all_hourly)}, erros: {errors}/{len(locations)}"
    )

    if errors:
        log.warning(f"{errors} municípios falharam. Verifique os logs acima.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Ingestão Open-Meteo → BigQuery")
    parser.add_argument("--days",  type=int, default=2,
                        help="Janela de coleta em dias (padrão: 2)")
    parser.add_argument("--start", default=None, help="Data inicial backfill: YYYY-MM-DD")
    parser.add_argument("--end",   default=None, help="Data final backfill:   YYYY-MM-DD")
    args = parser.parse_args()

    if args.start and args.end:
        run(args.start, args.end)
    else:
        end   = date.today().isoformat()
        start = (date.today() - timedelta(days=args.days)).isoformat()
        run(start, end)


if __name__ == "__main__":
    main()
