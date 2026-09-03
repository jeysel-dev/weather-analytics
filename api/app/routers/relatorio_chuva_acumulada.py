"""Endpoint JSON da página Chuva Acumulada (spec 022).

- GET /api/v1/relatorio-chuva-acumulada/dados -> ranking de precipitação
  acumulada por município na janela (todas as cidades da macrorregião, ou
  todas do estado), ordenado do maior para o menor.

Sem linha de total — soma de chuva entre municípios não é grandeza física
útil.
"""

from fastapi import APIRouter, Query

from app.routers.ref import meso_filter
from app.schemas.relatorio_chuva_acumulada import (
    ChuvaAcumuladaRow,
    RelatorioChuvaAcumuladaResponse,
)
from app.utils.bigquery import max_date, query, tbl

router = APIRouter(
    prefix="/relatorio-chuva-acumulada", tags=["relatorio-chuva-acumulada"]
)

_DAILY = "mart_climate__daily_facts"


@router.get("/dados", response_model=RelatorioChuvaAcumuladaResponse)
def get_dados(
    dias: int = Query(30, ge=7, le=365, description="Janela em dias (7–365, default 30)"),
    meso: str | None = Query(None, description="Macrorregião (omitir ou 'Todas' = sem filtro)"),
) -> RelatorioChuvaAcumuladaResponse:
    anchor = max_date(_DAILY)
    if anchor is None:
        return RelatorioChuvaAcumuladaResponse()
    clause, meso_params = meso_filter(meso)

    rows = query(
        f"""
        SELECT
          city_name,
          mesoregion,
          ROUND(SUM(precipitation_mm), 1) AS precip_acumulada,
          COUNTIF(precipitation_mm > 0)   AS dias_chuva,
          ROUND(MAX(precipitation_mm), 1)  AS maior_dia_mm,
          MAX_BY(date, precipitation_mm)   AS maior_dia_data
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL @dias DAY)
          {clause}
        GROUP BY city_name, mesoregion
        ORDER BY precip_acumulada DESC, city_name
        """,
        params={"max_date": anchor, "dias": dias, **meso_params},
    )
    return RelatorioChuvaAcumuladaResponse(
        rows=[ChuvaAcumuladaRow(**r) for r in rows]
    )
