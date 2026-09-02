"""Endpoint JSON da página Relatório por Cidade (spec 013).

- GET /api/v1/relatorio-cidade/dados -> 1 linha consolidada por cidade

`min_date` / `max_date` para o seletor de intervalo vêm de
`/api/v1/ref/daily-meta` (spec 014) — este endpoint não os expõe (absorveu
o antigo `/limites`). `cidades` validadas contra o seed; `inicio`/`fim`
parseadas como data. O `IN (...)` usa parâmetros nomeados (@c0, @c1, …).
"""

from datetime import date as date_type

from fastapi import APIRouter, HTTPException, Query

from app.routers.ref import require_cidade
from app.schemas.relatorio_cidade import RelatorioResponse
from app.utils.bigquery import query, tbl

router = APIRouter(prefix="/relatorio-cidade", tags=["relatorio-cidade"])

_DAILY = "mart_climate__daily_facts"


@router.get("/dados", response_model=RelatorioResponse)
def get_dados(
    cidades: list[str] = Query(..., description="1+ municípios (parâmetro repetido)"),
    inicio: date_type = Query(..., description="Data inicial (ISO 8601)"),
    fim: date_type = Query(..., description="Data final (ISO 8601)"),
) -> RelatorioResponse:
    if not cidades:
        raise HTTPException(status_code=422, detail="Informe ao menos uma cidade.")
    if inicio > fim:
        raise HTTPException(status_code=422, detail="`inicio` posterior a `fim`.")
    for city in cidades:
        require_cidade(city)

    placeholders = ", ".join(f"@c{i}" for i in range(len(cidades)))
    city_params = {f"c{i}": c for i, c in enumerate(cidades)}
    rows = query(
        f"""
        SELECT
          city_name,
          ROUND(MAX(temp_max_c), 1)         AS temp_maxima,
          ROUND(AVG(temp_max_c), 1)         AS temp_maxima_media,
          ROUND(MIN(temp_min_c), 1)         AS temp_minima,
          ROUND(AVG(temp_min_c), 1)         AS temp_minima_media,
          ROUND(SUM(precipitation_mm), 1)   AS precip_acumulada,
          ROUND(MAX(wind_speed_max_kmh), 1) AS vento_maximo
        FROM {tbl(_DAILY)}
        WHERE city_name IN ({placeholders})
          AND date BETWEEN @inicio AND @fim
        GROUP BY city_name
        ORDER BY city_name
        """,
        params={**city_params, "inicio": inicio, "fim": fim},
    )
    return RelatorioResponse(rows=rows)
