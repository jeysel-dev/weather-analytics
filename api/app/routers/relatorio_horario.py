"""Endpoint JSON da página Detalhamento Horário (spec 023).

- GET /api/v1/relatorio-horario/dados -> extremos do período (com o
  instante) + resumo diário (com linha de total), a partir do dado horário
  de `mart_climate__hourly_facts` para um município + janela.

Reusa `_require_city` / `_max_date_for` / `_HOURLY` de `horario.py` (mesmo
cache de "municípios com dado horário"). Toda query filtra `city_name` +
`date` — a mart horária é a mais volumosa do projeto.
"""

from fastapi import APIRouter, Query

from app.routers.horario import _HOURLY, _max_date_for, _require_city
from app.schemas.relatorio_horario import (
    DiaHorario,
    ExtremoHorario,
    RelatorioHorarioResponse,
)
from app.utils.bigquery import query, tbl

router = APIRouter(prefix="/relatorio-horario", tags=["relatorio-horario"])

# Instante do extremo formatado no BigQuery em horário local de SC (UTC−3
# fixo) — o front não converte fuso.
_TS = "FORMAT_TIMESTAMP('%d/%m/%Y %Hh', {expr}, 'America/Sao_Paulo')"

# (rótulo, chave do valor, chave do instante)
_INDICADORES: tuple[tuple[str, str, str], ...] = (
    ("Maior temperatura (°C)", "temp_max_v", "temp_max_at"),
    ("Menor temperatura (°C)", "temp_min_v", "temp_min_at"),
    ("Maior umidade (%)", "hum_max_v", "hum_max_at"),
    ("Menor umidade (%)", "hum_min_v", "hum_min_at"),
    ("Maior precipitação em 1 h (mm)", "precip_max_v", "precip_max_at"),
    ("Maior velocidade do vento (km/h)", "wind_max_v", "wind_max_at"),
)


@router.get("/dados", response_model=RelatorioHorarioResponse)
def get_dados(
    city: str = Query(..., min_length=1, description="Município (da lista de /horario/cidades)"),
    days: int = Query(7, ge=3, le=30, description="Janela em dias (3–30, default 7)"),
) -> RelatorioHorarioResponse:
    _require_city(city)
    max_dt = _max_date_for(city)
    if max_dt is None:
        return RelatorioHorarioResponse()

    params = {"city": city, "max_date": max_dt, "days": days}
    where = """
        WHERE city_name = @city
          AND date >= DATE_SUB(@max_date, INTERVAL @days DAY)
    """

    agg = query(
        f"""
        SELECT
          ROUND(MAX(temperature_c), 1)         AS temp_max_v,
          {_TS.format(expr="MAX_BY(observed_at, temperature_c)")}         AS temp_max_at,
          ROUND(MIN(temperature_c), 1)         AS temp_min_v,
          {_TS.format(expr="MIN_BY(observed_at, temperature_c)")}         AS temp_min_at,
          ROUND(MAX(relative_humidity_pct), 1) AS hum_max_v,
          {_TS.format(expr="MAX_BY(observed_at, relative_humidity_pct)")} AS hum_max_at,
          ROUND(MIN(relative_humidity_pct), 1) AS hum_min_v,
          {_TS.format(expr="MIN_BY(observed_at, relative_humidity_pct)")} AS hum_min_at,
          ROUND(MAX(precipitation_mm), 1)      AS precip_max_v,
          {_TS.format(expr="MAX_BY(observed_at, precipitation_mm)")}      AS precip_max_at,
          ROUND(MAX(wind_speed_kmh), 1)        AS wind_max_v,
          {_TS.format(expr="MAX_BY(observed_at, wind_speed_kmh)")}        AS wind_max_at,
          ROUND(AVG(temperature_c), 1)         AS temp_avg,
          ROUND(AVG(relative_humidity_pct), 1) AS hum_avg,
          ROUND(SUM(precipitation_mm), 1)      AS precip_total
        FROM {tbl(_HOURLY)}
        {where}
        """,
        params=params,
    )
    a = agg[0] if agg else {}

    dias = query(
        f"""
        SELECT
          date,
          ROUND(MIN(temperature_c), 1)         AS temp_min,
          ROUND(AVG(temperature_c), 1)         AS temp_avg,
          ROUND(MAX(temperature_c), 1)         AS temp_max,
          ROUND(MIN(relative_humidity_pct), 1) AS humidity_min,
          ROUND(AVG(relative_humidity_pct), 1) AS humidity_avg,
          ROUND(MAX(relative_humidity_pct), 1) AS humidity_max,
          ROUND(SUM(precipitation_mm), 1)      AS precip_total,
          ROUND(MAX(wind_speed_kmh), 1)        AS wind_max
        FROM {tbl(_HOURLY)}
        {where}
        GROUP BY date
        ORDER BY date
        """,
        params=params,
    )

    extremos = [
        ExtremoHorario(indicador=label, valor=a.get(v_key), quando=a.get(at_key))
        for label, v_key, at_key in _INDICADORES
    ]

    total = None
    if dias:
        total = DiaHorario(
            temp_min=a.get("temp_min_v"),
            temp_avg=a.get("temp_avg"),
            temp_max=a.get("temp_max_v"),
            humidity_min=a.get("hum_min_v"),
            humidity_avg=a.get("hum_avg"),
            humidity_max=a.get("hum_max_v"),
            precip_total=a.get("precip_total"),
            wind_max=a.get("wind_max_v"),
        )

    return RelatorioHorarioResponse(
        max_date=max_dt,
        extremos=extremos,
        dias=[DiaHorario(**r) for r in dias],
        total=total,
    )
