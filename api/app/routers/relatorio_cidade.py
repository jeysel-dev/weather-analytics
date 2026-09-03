"""Endpoint JSON da página Relatório por Cidade (spec 013, redesenho).

- GET /api/v1/relatorio-cidade/dados -> linhas diárias (cidade × dia) +
  subtotal agregado por cidade + total geral (uma linha agregando todas as
  cidades/dias juntos, presente mesmo com uma cidade só).

`min_date` / `max_date` para o seletor de intervalo vêm de
`/api/v1/ref/daily-meta` (spec 014) — este endpoint não os expõe (absorveu
o antigo `/limites`). `cidades` validadas contra o seed; `inicio`/`fim`
parseadas como data. O `IN (...)` usa parâmetros nomeados (@c0, @c1, …) —
nunca interpolação de string.
"""

from datetime import date as date_type

from fastapi import APIRouter, HTTPException, Query

from app.routers.ref import require_cidade
from app.schemas.relatorio_cidade import DiaRow, RelatorioResponse, SubtotalRow
from app.utils.bigquery import query, tbl

router = APIRouter(prefix="/relatorio-cidade", tags=["relatorio-cidade"])

_DAILY = "mart_climate__daily_facts"

# Mesma agregação usada pelo subtotal por cidade e pelo total geral — a
# única diferença entre as duas queries é o `GROUP BY city_name`.
_AGG = """
      ROUND(MAX(temp_max_c), 1)         AS temp_maxima,
      ROUND(AVG(temp_max_c), 1)         AS temp_maxima_media,
      ROUND(MIN(temp_min_c), 1)         AS temp_minima,
      ROUND(AVG(temp_min_c), 1)         AS temp_minima_media,
      ROUND(SUM(precipitation_mm), 1)   AS precip_acumulada,
      ROUND(MAX(wind_speed_max_kmh), 1) AS vento_maximo
"""

_SUBTOTAL_KEYS = (
    "temp_maxima",
    "temp_maxima_media",
    "temp_minima",
    "temp_minima_media",
    "precip_acumulada",
    "vento_maximo",
)


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
    params = {**city_params, "inicio": inicio, "fim": fim}

    # a) Linhas diárias — sem agregação, uma linha por cidade × dia.
    dias = query(
        f"""
        SELECT
          city_name,
          date,
          temp_max_c,
          temp_min_c,
          precipitation_mm,
          wind_speed_max_kmh
        FROM {tbl(_DAILY)}
        WHERE city_name IN ({placeholders})
          AND date BETWEEN @inicio AND @fim
        ORDER BY city_name, date
        """,
        params=params,
    )

    # b) Subtotal por cidade.
    subtotais = query(
        f"""
        SELECT
          city_name,
          {_AGG}
        FROM {tbl(_DAILY)}
        WHERE city_name IN ({placeholders})
          AND date BETWEEN @inicio AND @fim
        GROUP BY city_name
        ORDER BY city_name
        """,
        params=params,
    )

    # c) Total geral — mesma agregação, sem GROUP BY (uma linha só,
    #    agregando todas as cidades/dias juntos). Calculado no SQL, não em
    #    Python a partir dos subtotais (média de médias dá resultado errado).
    total_rows = query(
        f"""
        SELECT
          {_AGG}
        FROM {tbl(_DAILY)}
        WHERE city_name IN ({placeholders})
          AND date BETWEEN @inicio AND @fim
        """,
        params=params,
    )

    total_geral = None
    if total_rows and total_rows[0].get("temp_maxima") is not None:
        t = total_rows[0]
        total_geral = SubtotalRow(
            city_name="Total Geral",
            **{k: t[k] for k in _SUBTOTAL_KEYS},
        )

    return RelatorioResponse(
        dias=[DiaRow(**r) for r in dias],
        subtotais=[
            SubtotalRow(city_name=r["city_name"], **{k: r[k] for k in _SUBTOTAL_KEYS})
            for r in subtotais
        ],
        total_geral=total_geral,
    )
