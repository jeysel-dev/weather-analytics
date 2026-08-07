import os
from decimal import Decimal

import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()


def _project() -> str:
    val = os.environ.get("GCP_PROJECT_ID", "")
    if not val:
        raise EnvironmentError(
            "GCP_PROJECT_ID não definido. Crie um arquivo .env com base em .env.example"
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
    """Returns a backtick-quoted fully-qualified BigQuery table reference."""
    return f"`{_project()}.{_dataset(seeds)}.{name}`"


def _location() -> str | None:
    return os.environ.get("BIGQUERY_LOCATION") or None


@st.cache_resource
def _client() -> bigquery.Client:
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_DASHBOARD")
    if not key_path:
        raise EnvironmentError(
            "GOOGLE_APPLICATION_CREDENTIALS_DASHBOARD não definido. Crie um "
            "arquivo .env com base em .env.example"
        )
    creds = service_account.Credentials.from_service_account_file(key_path)
    return bigquery.Client(project=_project(), credentials=creds, location=_location())


@st.cache_data(ttl=3600, show_spinner="Obtendo os dados...")
def query(sql: str) -> pd.DataFrame:
    df = _client().query(sql).to_dataframe()
    # Colunas BigQuery NUMERIC voltam como decimal.Decimal (escala 9), não
    # float — sem essa conversão, valores já arredondados via ROUND() no SQL
    # aparecem como "16.700000000" quando exibidos sem format spec explícito.
    for col in df.columns:
        if df[col].dtype == object and df[col].apply(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    return df


def format_temp(value, decimals: int = 1) -> str:
    """Formata um valor numérico com casas decimais fixas; retorna '—' se ausente."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def max_date(table: str):
    """Última data disponível na tabela — usada para ancorar filtros de período
    no dado mais recente em vez do relógio de hoje (o pipeline roda por lote,
    não em tempo real, e pode ficar dias/semanas sem rodar)."""
    df = query(f"SELECT MAX(date) AS max_date FROM {tbl(table)}")
    return df["max_date"].iloc[0] if not df.empty else None


MESOREGIONS = [
    "Grande Florianópolis",
    "Norte Catarinense",
    "Vale do Itajaí",
    "Serrana",
    "Oeste Catarinense",
    "Sul Catarinense",
]
