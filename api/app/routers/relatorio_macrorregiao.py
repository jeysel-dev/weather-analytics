"""Endpoint JSON da página Por Macrorregião (spec 022).

- GET /api/v1/relatorio-macrorregiao/dados -> uma linha por macrorregião
  (as 8 do seed) + total geral do estado.

Duas queries: `daily_facts` agregado por `mesoregion` (âncora de
`daily-meta`) e `alerts` contado por `mesoregion` (âncora de `alerts-meta`,
própria — as marts podem divergir de data). Casadas por macrorregião em
Python: macrorregião sem alerta no período fica com `alertas = 0`.
"""

from fastapi import APIRouter, Query

from app.schemas.relatorio_macrorregiao import (
    MacrorregiaoRow,
    RelatorioMacrorregiaoResponse,
)
from app.utils.bigquery import max_date, query, tbl

router = APIRouter(prefix="/relatorio-macrorregiao", tags=["relatorio-macrorregiao"])

_DAILY = "mart_climate__daily_facts"
_ALERTS = "mart_climate__alerts"

_AGG_KEYS = (
    "municipios",
    "temp_max_media",
    "temp_min_media",
    "precip_media",
    "precip_acumulada",
)


@router.get("/dados", response_model=RelatorioMacrorregiaoResponse)
def get_dados(
    dias: int = Query(30, ge=7, le=365, description="Janela em dias (7–365, default 30)"),
) -> RelatorioMacrorregiaoResponse:
    anchor = max_date(_DAILY)
    if anchor is None:
        return RelatorioMacrorregiaoResponse()

    clima = query(
        f"""
        SELECT
          mesoregion,
          COUNT(DISTINCT city_name)      AS municipios,
          ROUND(AVG(temp_max_c), 1)      AS temp_max_media,
          ROUND(AVG(temp_min_c), 1)      AS temp_min_media,
          ROUND(AVG(precipitation_mm), 2) AS precip_media,
          ROUND(SUM(precipitation_mm), 1) AS precip_acumulada
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL @dias DAY)
          AND mesoregion IS NOT NULL
        GROUP BY mesoregion
        ORDER BY mesoregion
        """,
        params={"max_date": anchor, "dias": dias},
    )

    alerts_anchor = max_date(_ALERTS)
    alertas_por_meso: dict[str, int] = {}
    if alerts_anchor is not None:
        for r in query(
            f"""
            SELECT mesoregion, COUNT(*) AS alertas
            FROM {tbl(_ALERTS)}
            WHERE date >= DATE_SUB(@max_date, INTERVAL @dias DAY)
              AND mesoregion IS NOT NULL
            GROUP BY mesoregion
            """,
            params={"max_date": alerts_anchor, "dias": dias},
        ):
            alertas_por_meso[r["mesoregion"]] = r["alertas"]

    rows = [
        MacrorregiaoRow(
            mesoregion=r["mesoregion"],
            alertas=alertas_por_meso.get(r["mesoregion"], 0),
            **{k: r[k] for k in _AGG_KEYS},
        )
        for r in clima
    ]

    total_geral = None
    total_rows = query(
        f"""
        SELECT
          COUNT(DISTINCT city_name)      AS municipios,
          ROUND(AVG(temp_max_c), 1)      AS temp_max_media,
          ROUND(AVG(temp_min_c), 1)      AS temp_min_media,
          ROUND(AVG(precipitation_mm), 2) AS precip_media,
          ROUND(SUM(precipitation_mm), 1) AS precip_acumulada
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL @dias DAY)
        """,
        params={"max_date": anchor, "dias": dias},
    )
    if total_rows and total_rows[0].get("temp_max_media") is not None:
        t = total_rows[0]
        total_geral = MacrorregiaoRow(
            mesoregion="Total Geral",
            alertas=sum(alertas_por_meso.values()),
            **{k: t[k] for k in _AGG_KEYS},
        )

    return RelatorioMacrorregiaoResponse(rows=rows, total_geral=total_geral)
