"""Endpoints JSON da página Comparativo (spec 012).

- GET /api/v1/comparativo/cidades-serie      -> série multi-cidade + resumo min/max/mean (aba 1)
- GET /api/v1/comparativo/chuva-heatmap      -> SUM(precipitation_mm) por dia × município (aba 2)
- GET /api/v1/comparativo/datas-disponiveis  -> últimas 60 datas horárias do município (aba 3)
- GET /api/v1/comparativo/dia-vs-historico   -> perfil horário do dia vs média 30d anteriores (aba 3)

Abas 1/2 ancoram em `max_date('mart_climate__daily_facts')`; a aba 3 usa as
datas reais da `hourly_facts`. Listas de referência vêm da camada de
referência (spec 014): `/api/v1/ref/cidades`, `/api/v1/ref/mesorregioes`.
"""

from datetime import date as date_type
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.routers.ref import require_cidade, require_meso
from app.schemas.comparativo import (
    CidadesSerieResponse,
    ChuvaHeatmapResponse,
    DatasDisponiveisResponse,
    DesvioResumo,
    DiaVsHistoricoResponse,
    ResumoCidade,
)
from app.utils.bigquery import max_date, query, tbl

router = APIRouter(prefix="/comparativo", tags=["comparativo"])

_DAILY = "mart_climate__daily_facts"
_HOURLY = "mart_climate__hourly_facts"

Metric = Literal["temp_max", "temp_min", "temp_avg", "precip"]
_METRIC_COL = {
    "temp_max": "temp_max_c",
    "temp_min": "temp_min_c",
    "temp_avg": "temp_avg_c",
    "precip": "precipitation_mm",
}


@router.get("/cidades-serie", response_model=CidadesSerieResponse)
def get_cidades_serie(
    cities: list[str] = Query(..., description="2 a 3 municípios (parâmetro repetido)"),
    metric: Metric = Query("temp_max"),
    days: int = Query(30, ge=7, le=180),
) -> CidadesSerieResponse:
    """Série temporal de `metric` por município + resumo `min`/`max`/`mean`
    por cidade (sobre os dias presentes, `round(1)` — paridade com o
    `groupby(...).agg(...)` do pandas)."""
    if not 2 <= len(cities) <= 3:
        raise HTTPException(status_code=422, detail="Informe 2 ou 3 municípios.")
    for city in cities:
        require_cidade(city)
    anchor = max_date(_DAILY)
    if anchor is None:
        return CidadesSerieResponse()

    col = _METRIC_COL[metric]  # dict fechado — não é string livre do cliente
    placeholders = ", ".join(f"@c{i}" for i in range(len(cities)))
    city_params = {f"c{i}": c for i, c in enumerate(cities)}
    rows = query(
        f"""
        SELECT date, city_name, ROUND({col}, 1) AS valor
        FROM {tbl(_DAILY)}
        WHERE city_name IN ({placeholders})
          AND date >= DATE_SUB(@max_date, INTERVAL @days DAY)
        ORDER BY date, city_name
        """,
        params={**city_params, "max_date": anchor, "days": days},
    )

    resumo: list[ResumoCidade] = []
    for city in dict.fromkeys(cities):  # ordem estável, sem duplicatas
        vals = [r["valor"] for r in rows if r["city_name"] == city and r["valor"] is not None]
        if vals:
            resumo.append(
                ResumoCidade(
                    city_name=city,
                    min=round(min(vals), 1),
                    max=round(max(vals), 1),
                    mean=round(sum(vals) / len(vals), 1),
                )
            )
    return CidadesSerieResponse(rows=rows, resumo=resumo)


@router.get("/chuva-heatmap", response_model=ChuvaHeatmapResponse)
def get_chuva_heatmap(
    meso: str = Query(..., description="Mesorregião (obrigatória, sem 'Todas')"),
    days: int = Query(30, ge=14, le=60),
) -> ChuvaHeatmapResponse:
    require_meso(meso)
    anchor = max_date(_DAILY)
    if anchor is None:
        return ChuvaHeatmapResponse()
    rows = query(
        f"""
        SELECT date, city_name, ROUND(SUM(precipitation_mm), 1) AS precipitation_mm
        FROM {tbl(_DAILY)}
        WHERE mesoregion = @meso
          AND date >= DATE_SUB(@max_date, INTERVAL @days DAY)
        GROUP BY date, city_name
        ORDER BY city_name, date
        """,
        params={"meso": meso, "max_date": anchor, "days": days},
    )
    return ChuvaHeatmapResponse(rows=rows)


@router.get("/datas-disponiveis", response_model=DatasDisponiveisResponse)
def get_datas_disponiveis(
    city: str = Query(..., min_length=1),
) -> DatasDisponiveisResponse:
    require_cidade(city)
    rows = query(
        f"""
        SELECT DISTINCT date
        FROM {tbl(_HOURLY)}
        WHERE city_name = @city
        ORDER BY date DESC
        LIMIT 60
        """,
        params={"city": city},
    )
    return DatasDisponiveisResponse(dates=[r["date"] for r in rows])


@router.get("/dia-vs-historico", response_model=DiaVsHistoricoResponse)
def get_dia_vs_historico(
    city: str = Query(..., min_length=1),
    date: date_type = Query(..., description="Data de referência (ISO 8601)"),
) -> DiaVsHistoricoResponse:
    require_cidade(city)
    atual = query(
        f"""
        SELECT hour,
               ROUND(AVG(temperature_c), 1)         AS temp,
               ROUND(AVG(relative_humidity_pct), 1) AS humidity
        FROM {tbl(_HOURLY)}
        WHERE city_name = @city AND date = @date
        GROUP BY hour
        ORDER BY hour
        """,
        params={"city": city, "date": date},
    )
    historico = query(
        f"""
        SELECT hour,
               ROUND(AVG(temperature_c), 1)         AS avg_temp,
               ROUND(AVG(relative_humidity_pct), 1) AS avg_humidity
        FROM {tbl(_HOURLY)}
        WHERE city_name = @city
          AND date >= DATE_SUB(@date, INTERVAL 30 DAY)
          AND date <  @date
        GROUP BY hour
        ORDER BY hour
        """,
        params={"city": city, "date": date},
    )

    desvio: DesvioResumo | None = None
    if atual and historico:
        hist_temp = {h["hour"]: h["avg_temp"] for h in historico}
        diffs = [
            round(a["temp"] - hist_temp[a["hour"]], 1)
            for a in atual
            if a["temp"] is not None and hist_temp.get(a["hour"]) is not None
        ]
        if diffs:
            desvio = DesvioResumo(
                medio=round(sum(diffs) / len(diffs), 1),
                maximo=max(diffs),
                minimo=min(diffs),
            )
    return DiaVsHistoricoResponse(atual=atual, historico=historico, desvio=desvio)
