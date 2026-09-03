"""Endpoint JSON da página Consolidado Mensal (spec 022).

- GET /api/v1/relatorio-mensal/dados -> linhas cidade × mês + subtotal por
  cidade + total geral (mesmo formato de 3 partes do /relatorio-cidade).

`inicio` / `fim` são meses (`YYYY-MM`), casados direto contra a coluna
`year_month` (ordenável lexicograficamente). `cidades` validadas contra o
seed; `IN (...)` com parâmetros nomeados.
"""

import re

from fastapi import APIRouter, HTTPException, Query

from app.routers.ref import require_cidade
from app.schemas.relatorio_mensal import MensalAgg, MesRow, RelatorioMensalResponse
from app.utils.bigquery import query, tbl

router = APIRouter(prefix="/relatorio-mensal", tags=["relatorio-mensal"])

_DAILY = "mart_climate__daily_facts"
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

# Mesma agregação nos 3 níveis (mês, subtotal por cidade, total geral) — as
# médias saem sempre das linhas diárias, nunca de média de médias.
_AGG = """
      ROUND(AVG(temp_max_c), 1)                        AS temp_max_media,
      ROUND(AVG(temp_min_c), 1)                        AS temp_min_media,
      ROUND(AVG(temp_amplitude_c), 1)                  AS amplitude_media,
      ROUND(SUM(precipitation_mm), 1)                  AS precip_acumulada,
      COUNTIF(precipitation_mm > 0)                    AS dias_chuva,
      ROUND(MAX(wind_speed_max_kmh), 1)                AS vento_maximo
"""

_AGG_KEYS = (
    "temp_max_media",
    "temp_min_media",
    "amplitude_media",
    "precip_acumulada",
    "dias_chuva",
    "vento_maximo",
)


@router.get("/dados", response_model=RelatorioMensalResponse)
def get_dados(
    cidades: list[str] = Query(..., description="1+ municípios (parâmetro repetido)"),
    inicio: str = Query(..., description="Mês inicial (YYYY-MM)"),
    fim: str = Query(..., description="Mês final (YYYY-MM)"),
) -> RelatorioMensalResponse:
    if not cidades:
        raise HTTPException(status_code=422, detail="Informe ao menos uma cidade.")
    if not _MONTH_RE.match(inicio) or not _MONTH_RE.match(fim):
        raise HTTPException(status_code=422, detail="`inicio`/`fim` devem ser YYYY-MM.")
    if inicio > fim:
        raise HTTPException(status_code=422, detail="`inicio` posterior a `fim`.")
    for city in cidades:
        require_cidade(city)

    placeholders = ", ".join(f"@c{i}" for i in range(len(cidades)))
    params = {
        **{f"c{i}": c for i, c in enumerate(cidades)},
        "inicio": inicio,
        "fim": fim,
    }
    where = f"""
        WHERE city_name IN ({placeholders})
          AND year_month BETWEEN @inicio AND @fim
    """

    meses = query(
        f"""
        SELECT year_month, city_name, {_AGG}
        FROM {tbl(_DAILY)}
        {where}
        GROUP BY year_month, city_name
        ORDER BY city_name, year_month
        """,
        params=params,
    )
    subtotais = query(
        f"""
        SELECT city_name, {_AGG}
        FROM {tbl(_DAILY)}
        {where}
        GROUP BY city_name
        ORDER BY city_name
        """,
        params=params,
    )
    total_rows = query(
        f"""
        SELECT {_AGG}
        FROM {tbl(_DAILY)}
        {where}
        """,
        params=params,
    )

    total_geral = None
    if total_rows and total_rows[0].get("temp_max_media") is not None:
        t = total_rows[0]
        total_geral = MensalAgg(city_name="Total Geral", **{k: t[k] for k in _AGG_KEYS})

    return RelatorioMensalResponse(
        meses=[MesRow(**r) for r in meses],
        subtotais=[
            MensalAgg(city_name=r["city_name"], **{k: r[k] for k in _AGG_KEYS})
            for r in subtotais
        ],
        total_geral=total_geral,
    )
