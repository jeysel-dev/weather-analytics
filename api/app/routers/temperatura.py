"""Endpoints JSON da página Temperatura (spec 007).

- GET /api/v1/temperatura/rankings              -> top 10 quentes / frios (janela fixa 7d)
- GET /api/v1/temperatura/tendencia-mesorregiao -> AVG(temp_avg_c) por dia × mesorregião
- GET /api/v1/temperatura/anomalia              -> AVG(temp_anomaly_c) por dia × mesorregião (todas)

Rotas síncronas (`def`). Janela ancorada em `max_date('mart_climate__daily_facts')`,
nunca `CURRENT_DATE()` (CLAUDE.md / spec 006). Valores dinâmicos (`meso`,
`days`, data-âncora) vão como parâmetros nomeados do BigQuery.
"""

from fastapi import APIRouter, Query

from app.routers.ref import meso_filter
from app.schemas.temperatura import (
    AnomaliaResponse,
    RankingsResponse,
    TendenciaResponse,
)
from app.utils.bigquery import max_date, query, tbl

router = APIRouter(prefix="/temperatura", tags=["temperatura"])

_DAILY = "mart_climate__daily_facts"


@router.get("/rankings", response_model=RankingsResponse)
def get_rankings(
    meso: str | None = Query(None, description="Mesorregião (omitir ou 'Todas' = sem filtro)"),
) -> RankingsResponse:
    """Top 10 municípios mais quentes (`AVG(temp_max_c)`) e mais frios
    (`AVG(temp_min_c)`) na janela **fixa de 7 dias** — o filtro `days` das
    outras seções não afeta este endpoint (paridade com o Streamlit)."""
    anchor = max_date(_DAILY)
    if anchor is None:
        return RankingsResponse()
    clause, meso_params = meso_filter(meso)
    params = {"max_date": anchor, **meso_params}

    quentes = query(
        f"""
        SELECT city_name, mesoregion, ROUND(AVG(temp_max_c), 1) AS media
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL 7 DAY)
          {clause}
        GROUP BY city_name, mesoregion
        ORDER BY media DESC
        LIMIT 10
        """,
        params=params,
    )
    frios = query(
        f"""
        SELECT city_name, mesoregion, ROUND(AVG(temp_min_c), 1) AS media
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL 7 DAY)
          {clause}
        GROUP BY city_name, mesoregion
        ORDER BY media ASC
        LIMIT 10
        """,
        params=params,
    )
    return RankingsResponse(quentes=quentes, frios=frios)


@router.get("/tendencia-mesorregiao", response_model=TendenciaResponse)
def get_tendencia(
    meso: str | None = Query(None, description="Mesorregião (omitir ou 'Todas' = sem filtro)"),
    days: int = Query(30, ge=7, le=90, description="Janela em dias (7–90, default 30)"),
) -> TendenciaResponse:
    """`AVG(temp_avg_c)` por `date` × `mesoregion` na janela de `days` dias.
    Respeita o filtro de mesorregião."""
    anchor = max_date(_DAILY)
    if anchor is None:
        return TendenciaResponse()
    clause, meso_params = meso_filter(meso)
    rows = query(
        f"""
        SELECT date, mesoregion, ROUND(AVG(temp_avg_c), 1) AS temp_avg
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL @days DAY)
          {clause}
        GROUP BY date, mesoregion
        ORDER BY date
        """,
        params={"max_date": anchor, "days": days, **meso_params},
    )
    return TendenciaResponse(rows=rows)


@router.get("/anomalia", response_model=AnomaliaResponse)
def get_anomalia(
    days: int = Query(30, ge=7, le=90, description="Janela em dias (7–90, default 30)"),
) -> AnomaliaResponse:
    """`AVG(temp_anomaly_c)` por `date` × `mesoregion` para **todas** as
    mesorregiões — este endpoint ignora `meso` de propósito (paridade com o
    Streamlit, onde o heatmap não recebe `meso_clause`)."""
    anchor = max_date(_DAILY)
    if anchor is None:
        return AnomaliaResponse()
    rows = query(
        f"""
        SELECT date, mesoregion, ROUND(AVG(temp_anomaly_c), 2) AS anomaly
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL @days DAY)
        GROUP BY date, mesoregion
        ORDER BY date
        """,
        params={"max_date": anchor, "days": days},
    )
    return AnomaliaResponse(rows=rows)
