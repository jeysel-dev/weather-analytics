"""Endpoint JSON da página Extremos e Recordes (spec 022).

- GET /api/v1/relatorio-extremos/dados -> 6 linhas (uma por indicador) com
  o recorde da janela: valor, cidade e data.

Uma query só: `MAX_BY` / `MIN_BY` de um `STRUCT(city_name, date, valor)` por
indicador — um scan da janela em vez de seis. `MAX_BY`/`MIN_BY` ignoram
linhas onde a métrica é `NULL` e devolvem `NULL` quando não sobra nenhuma.
"""

from fastapi import APIRouter, Query

from app.routers.ref import meso_filter
from app.schemas.relatorio_extremos import ExtremoRow, RelatorioExtremosResponse
from app.utils.bigquery import max_date, query, tbl

router = APIRouter(prefix="/relatorio-extremos", tags=["relatorio-extremos"])

_DAILY = "mart_climate__daily_facts"

# (chave no SELECT, rótulo exibido, coluna-métrica, agregação BigQuery)
_INDICADORES: tuple[tuple[str, str, str, str], ...] = (
    ("maior_temp_max", "Maior temperatura máxima (°C)", "temp_max_c", "MAX_BY"),
    ("menor_temp_min", "Menor temperatura mínima (°C)", "temp_min_c", "MIN_BY"),
    ("maior_amplitude", "Maior amplitude térmica (°C)", "temp_amplitude_c", "MAX_BY"),
    ("maior_precip", "Maior precipitação em 24 h (mm)", "precipitation_mm", "MAX_BY"),
    ("maior_vento", "Maior rajada de vento (km/h)", "wind_speed_max_kmh", "MAX_BY"),
    ("maior_uv", "Maior índice UV", "uv_index_max", "MAX_BY"),
)


@router.get("/dados", response_model=RelatorioExtremosResponse)
def get_dados(
    dias: int = Query(30, ge=7, le=365, description="Janela em dias (7–365, default 30)"),
    meso: str | None = Query(None, description="Macrorregião (omitir ou 'Todas' = sem filtro)"),
) -> RelatorioExtremosResponse:
    anchor = max_date(_DAILY)
    if anchor is None:
        return RelatorioExtremosResponse()
    clause, meso_params = meso_filter(meso)

    selects = ",\n          ".join(
        f"{agg}(STRUCT(city_name, date, ROUND({col}, 1) AS valor), {col}) AS {key}"
        for key, _, col, agg in _INDICADORES
    )
    rows = query(
        f"""
        SELECT
          {selects}
        FROM {tbl(_DAILY)}
        WHERE date >= DATE_SUB(@max_date, INTERVAL @dias DAY)
          {clause}
        """,
        params={"max_date": anchor, "dias": dias, **meso_params},
    )

    row = rows[0] if rows else {}
    out: list[ExtremoRow] = []
    for key, label, _col, _agg in _INDICADORES:
        rec = row.get(key)
        out.append(
            ExtremoRow(
                indicador=label,
                valor=rec["valor"] if rec else None,
                city_name=rec["city_name"] if rec else None,
                date=rec["date"] if rec else None,
            )
        )
    return RelatorioExtremosResponse(rows=out)
