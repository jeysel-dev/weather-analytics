"""Endpoints JSON da página Precipitação (spec 008).

- GET /api/v1/precipitacao/ranking              -> acumulado + dias de chuva por município
- GET /api/v1/precipitacao/intensidade          -> COUNT(*) por precipitation_class (valor cru)
- GET /api/v1/precipitacao/heatmap-mesorregiao  -> AVG(precipitation_mm) por dia × mesorregião (todas)

Rotas síncronas. Janela ancorada em `max_date('mart_climate__daily_facts')`.
O `limit` do ranking (20 vs 300/todos) é regra de domínio e fica no servidor.
"""

from fastapi import APIRouter, Query

from app.routers.ref import meso_filter
from app.schemas.precipitacao import (
    HeatmapResponse,
    IntensidadeResponse,
    RankingResponse,
)
from app.utils.bigquery import max_date, query, tbl

router = APIRouter(prefix="/precipitacao", tags=["precipitacao"])

_DAILY = "mart_climate__daily_facts"


@router.get("/ranking", response_model=RankingResponse)
def get_ranking(
    meso: str | None = Query(None, description="Mesorregião (omitir ou 'Todas' = sem filtro)"),
    days: int = Query(30, ge=7, le=90, description="Janela em dias (7–90, default 30)"),
) -> RankingResponse:
    """`SUM(precipitation_mm)` + contagem de dias com chuva por município.
    WHEN sem mesorregião: 20 resultados; WHEN mesorregião específica: todos
    (paridade com o `LIMIT 300` do Streamlit)."""
    anchor = max_date(_DAILY)
    if anchor is None:
        return RankingResponse()
    clause, meso_params = meso_filter(meso)
    limit = 20 if not meso_params else 300
    rows = query(
        f"""
        SELECT city_name, mesoregion,
               ROUND(SUM(precipitation_mm), 1)                  AS total_mm,
               COUNT(CASE WHEN precipitation_mm > 0 THEN 1 END) AS dias_chuva
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL @days DAY)
          {clause}
        GROUP BY city_name, mesoregion
        ORDER BY total_mm DESC
        LIMIT @limit
        """,
        params={"max_date": anchor, "days": days, "limit": limit, **meso_params},
    )
    return RankingResponse(rows=rows)


@router.get("/intensidade", response_model=IntensidadeResponse)
def get_intensidade(
    meso: str | None = Query(None, description="Mesorregião (omitir ou 'Todas' = sem filtro)"),
    days: int = Query(30, ge=7, le=90, description="Janela em dias (7–90, default 30)"),
) -> IntensidadeResponse:
    """`COUNT(*)` por `precipitation_class` (valor cru — o rótulo PT e a cor
    vêm de `web/src/labels.ts` no cliente, spec 014)."""
    anchor = max_date(_DAILY)
    if anchor is None:
        return IntensidadeResponse()
    clause, meso_params = meso_filter(meso)
    rows = query(
        f"""
        SELECT precipitation_class, COUNT(*) AS qtd
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL @days DAY)
          {clause}
        GROUP BY precipitation_class
        ORDER BY qtd DESC
        """,
        params={"max_date": anchor, "days": days, **meso_params},
    )
    return IntensidadeResponse(rows=rows)


@router.get("/heatmap-mesorregiao", response_model=HeatmapResponse)
def get_heatmap(
    days: int = Query(30, ge=7, le=90, description="Janela em dias (7–90, default 30)"),
) -> HeatmapResponse:
    """`AVG(precipitation_mm)` por `date` × `mesoregion` para **todas** as
    mesorregiões — ignora `meso` de propósito (paridade com o Streamlit)."""
    anchor = max_date(_DAILY)
    if anchor is None:
        return HeatmapResponse()
    rows = query(
        f"""
        SELECT date, mesoregion, ROUND(AVG(precipitation_mm), 1) AS avg_precip
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL @days DAY)
        GROUP BY date, mesoregion
        ORDER BY date
        """,
        params={"max_date": anchor, "days": days},
    )
    return HeatmapResponse(rows=rows)
