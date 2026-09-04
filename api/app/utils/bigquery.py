"""Acesso ao BigQuery para os endpoints /api/v1/* (spec 006/010).

Adaptado de `streamlit/utils/bigquery.py` — mesma semântica de `tbl()`,
`query()`, `max_date()`, `min_date()` e a mesma conversão `Decimal -> float`
já validada em produção no dashboard Streamlit. Diferenças em relação ao
original:

- Sem `@st.cache_data` / `@st.cache_resource` (não há Streamlit aqui). O
  cliente é reaproveitado via `functools.lru_cache`; resultados de query
  não são cacheados na aplicação — o BigQuery já tem cache de resultados
  server-side (24h, sem custo) para queries idênticas.
- `query()` retorna `list[dict]` (linhas), não um `pandas.DataFrame` — as
  respostas desta API são pequenas (agregados diários/horários por
  município) e viram JSON direto via Pydantic.
- `query()` aceita `params` (parâmetros nomeados do BigQuery). O Streamlit
  interpola strings direto no SQL; aqui os valores dinâmicos (nome de
  município, nº de dias, data-âncora) vão como parâmetros — evita o bug de
  aspas em nomes como "Herval d'Oeste" e mantém a defesa contra injeção
  mesmo com a allowlist de município aplicada na camada do router.
"""

import datetime
import os
from decimal import Decimal
from functools import lru_cache

from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account

load_dotenv()


def _project() -> str:
    val = os.environ.get("GCP_PROJECT_ID", "")
    if not val:
        raise EnvironmentError(
            "GCP_PROJECT_ID não definido. Configure o ambiente da API "
            "(.env local a partir de api/.env.example, ou variáveis do container)."
        )
    return val


def _dataset(seeds: bool = False) -> str:
    if seeds:
        return os.environ.get(
            "BIGQUERY_SEEDS_DATASET",
            os.environ.get("BIGQUERY_DATASET", "marts"),
        )
    return os.environ.get("BIGQUERY_DATASET", "marts")


def tbl(name: str, seeds: bool = False) -> str:
    """Referência de tabela BigQuery totalmente qualificada, entre crases."""
    return f"`{_project()}.{_dataset(seeds)}.{name}`"


def _location() -> str | None:
    return os.environ.get("BIGQUERY_LOCATION") or None


def _credentials_path() -> str:
    """Caminho da chave da service account dedicada da API (`weather-analytics-api-sa`)."""
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_API")
    if not path:
        raise EnvironmentError(
            "GOOGLE_APPLICATION_CREDENTIALS_API não definido. Ver api/.env.example."
        )
    return path


@lru_cache(maxsize=1)
def _client() -> bigquery.Client:
    creds = service_account.Credentials.from_service_account_file(_credentials_path())
    return bigquery.Client(project=_project(), credentials=creds, location=_location())


def _scalar_param(name: str, value: object) -> bigquery.ScalarQueryParameter:
    if isinstance(value, bool):
        bq_type = "BOOL"
    elif isinstance(value, int):
        bq_type = "INT64"
    elif isinstance(value, float):
        bq_type = "FLOAT64"
    elif isinstance(value, datetime.datetime):
        bq_type = "TIMESTAMP"
    elif isinstance(value, datetime.date):
        bq_type = "DATE"
    else:
        bq_type = "STRING"
    return bigquery.ScalarQueryParameter(name, bq_type, value)


def query(sql: str, params: dict | None = None) -> list[dict]:
    """Executa `sql` e devolve as linhas como `list[dict]`.

    `params`: dict de parâmetros nomeados (`@nome` no SQL). O tipo BigQuery
    é inferido do tipo Python do valor.

    Colunas NUMERIC do BigQuery voltam como `decimal.Decimal` (escala 9),
    não `float` — sem a conversão abaixo, um valor já arredondado via
    `ROUND()` no SQL apareceria como "16.700000000" ao serializar. Mesma
    lógica de `streamlit/utils/bigquery.py`.
    """
    job_config = None
    if params:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[_scalar_param(name, value) for name, value in params.items()]
        )
    rows = _client().query(sql, job_config=job_config).result()
    out: list[dict] = []
    for row in rows:
        record = dict(row)
        for key, value in record.items():
            if isinstance(value, Decimal):
                record[key] = float(value)
        out.append(record)
    return out


def max_date(table: str):
    """Última `date` disponível na tabela — âncora de filtros de período no
    dado real, não em `CURRENT_DATE()` (o pipeline roda por lote e pode
    ficar dias/semanas parado; ver CLAUDE.md)."""
    rows = query(f"SELECT MAX(date) AS max_date FROM {tbl(table)}")
    return rows[0]["max_date"] if rows else None


def min_date(table: str):
    """Primeira `date` disponível na tabela."""
    rows = query(f"SELECT MIN(date) AS min_date FROM {tbl(table)}")
    return rows[0]["min_date"] if rows else None
