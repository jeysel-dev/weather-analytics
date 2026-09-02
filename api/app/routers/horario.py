"""Endpoints JSON da página Horário (spec 010).

- GET /api/v1/horario/cidades      -> lista de municípios com dado horário
- GET /api/v1/horario/serie        -> série horária (temp/umidade/vento/chuva)
- GET /api/v1/horario/padrao-24h   -> perfil médio das 24 horas

Rotas síncronas (`def`) — rodam no threadpool do Starlette, cliente
BigQuery síncrono reaproveitado (spec 006). A tabela
`mart_climate__hourly_facts` é a mais volumosa do projeto: toda query
mantém filtro por `city_name` e por `date` (partição), nunca varre a
tabela inteira.
"""

from datetime import date
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query

from app.schemas.horario import Padrao24hResponse, SerieResponse
from app.utils.bigquery import query, tbl

router = APIRouter(prefix="/horario", tags=["horario"])

_HOURLY = "mart_climate__hourly_facts"


@lru_cache(maxsize=1)
def _cidades() -> list[str]:
    # Sem TTL de propósito: a lista de municípios com dado horário muda
    # muito raramente (só quando uma nova localidade entra no seed e passa
    # a ter coleta horária). Mesmo raciocínio da spec 014 para os endpoints
    # de referência — embora esta lista não faça parte formal daquela
    # camada. `get_cidades()` (endpoint público) e `_require_city()`
    # compartilham este cache: a query só roda na primeira chamada,
    # depois `_require_city()` vira validação em memória (0 queries).
    rows = query(
        f"""
        SELECT DISTINCT city_name
        FROM {tbl(_HOURLY)}
        WHERE city_name IS NOT NULL
        ORDER BY city_name
        """
    )
    return [row["city_name"] for row in rows]


def _require_city(city: str) -> None:
    """Allowlist: `city` tem que estar na lista de /cidades antes de entrar
    numa query. Defesa em profundidade — os valores dinâmicos já vão como
    parâmetro do BigQuery, mas isto também dá um 404 claro para um
    município inexistente."""
    if city not in _cidades():
        raise HTTPException(status_code=404, detail=f"Sem dado horário para o município: {city!r}")


def _max_date_for(city: str) -> date | None:
    rows = query(
        f"SELECT MAX(date) AS max_date FROM {tbl(_HOURLY)} WHERE city_name = @city",
        params={"city": city},
    )
    return rows[0]["max_date"] if rows else None


@router.get("/cidades", response_model=list[str])
def get_cidades() -> list[str]:
    """Municípios distintos presentes em `mart_climate__hourly_facts`
    (ordenados) — não a lista do seed: nem todo município tem dado horário."""
    return _cidades()


@router.get("/serie", response_model=SerieResponse)
def get_serie(
    city: str = Query(..., min_length=1, description="Nome do município (da lista de /cidades)"),
    days: int = Query(7, ge=3, le=30, description="Janela em dias (3–30, default 7)"),
) -> SerieResponse:
    _require_city(city)
    max_dt = _max_date_for(city)
    if max_dt is None:
        return SerieResponse(max_date=None, rows=[])

    rows = query(
        f"""
        SELECT observed_at, temperature_c, relative_humidity_pct,
               wind_speed_kmh, precipitation_mm
        FROM {tbl(_HOURLY)}
        WHERE city_name = @city
          AND date >= DATE_SUB(@max_date, INTERVAL @days DAY)
        ORDER BY observed_at
        """,
        params={"city": city, "max_date": max_dt, "days": days},
    )
    return SerieResponse(max_date=max_dt, rows=rows)


@router.get("/padrao-24h", response_model=Padrao24hResponse)
def get_padrao_24h(
    city: str = Query(..., min_length=1, description="Nome do município (da lista de /cidades)"),
    days: int = Query(7, ge=3, le=30, description="Janela em dias (3–30, default 7)"),
) -> Padrao24hResponse:
    _require_city(city)
    max_dt = _max_date_for(city)
    if max_dt is None:
        return Padrao24hResponse(rows=[])

    rows = query(
        f"""
        SELECT
          hour,
          ROUND(AVG(temperature_c), 1)         AS avg_temp,
          ROUND(AVG(relative_humidity_pct), 1) AS avg_humidity,
          ROUND(AVG(wind_speed_kmh), 1)        AS avg_wind,
          ROUND(SUM(precipitation_mm) / NULLIF(COUNT(DISTINCT date), 0), 2) AS avg_precip_dia
        FROM {tbl(_HOURLY)}
        WHERE city_name = @city
          AND date >= DATE_SUB(@max_date, INTERVAL @days DAY)
        GROUP BY hour
        ORDER BY hour
        """,
        params={"city": city, "max_date": max_dt, "days": days},
    )
    return Padrao24hResponse(rows=rows)
