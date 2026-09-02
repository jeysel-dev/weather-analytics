"""Endpoints JSON da página Cidades / "Perfil por Município" (spec 011).

- GET /api/v1/cidades/lista   -> 295 municípios do seed COM metadados (endpoint próprio)
- GET /api/v1/cidades/clima   -> linhas diárias + resumo agregado (KPIs) do município
- GET /api/v1/cidades/alertas -> até 100 alertas do município (traduzidos)

Rotas síncronas. `clima` ancora em `max_date('mart_climate__daily_facts')`,
`alertas` em `max_date('mart_climate__alerts')`. `city` validada contra a
lista de `/api/v1/cidades/lista`.
"""

from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query

from app.schemas.cidades import (
    AlertaRow,
    AlertasResponse,
    CidadeMeta,
    ClimaResponse,
    ClimaResumo,
)
from app.utils.bigquery import max_date, query, tbl
from app.utils.labels import ALERT_TYPE_PT, SEVERITY_PT

router = APIRouter(prefix="/cidades", tags=["cidades"])

_DAILY = "mart_climate__daily_facts"
_ALERTS = "mart_climate__alerts"


@lru_cache(maxsize=1)
def _lista() -> list[dict]:
    # Sem TTL: a lista (e os metadados) só muda quando o seed `locations`
    # muda — mesma justificativa dos caches de `ref.py` (spec 014).
    return query(
        f"""
        SELECT city_name, mesoregion,
               ROUND(latitude, 4)  AS latitude,
               ROUND(longitude, 4) AS longitude,
               altitude_m
        FROM {tbl('locations', seeds=True)}
        WHERE city_name IS NOT NULL
        ORDER BY city_name
        """
    )


def _require_city(city: str) -> None:
    if city not in {r["city_name"] for r in _lista()}:
        raise HTTPException(status_code=404, detail=f"Município desconhecido: {city!r}")


def _mean(values: list) -> float | None:
    """Média sobre os valores não-nulos, `round(1)` (= `Series.mean()` do
    pandas, que ignora NaN). Devolve `None` quando NÃO há nenhum valor no
    período — inclusive para `temp_anomaly_c`.

    Divergência deliberada e ÚNICA do Streamlit, decidida aqui no servidor
    (não espalhada no TS): a página Streamlit faz
    `float(agg["temp_anomaly_c"] or 0)` e exibe `+0.0 °C` quando a média é
    nula/ausente — o que mostra um "zero" que não é dado real. Aqui o resumo
    agregado retorna `temp_anomaly_mean=None` e o cliente formata via
    `fmtSigned(null)` -> `"—"` (mesma convenção de "sem dado" do resto do
    dashboard). O cliente NÃO tem lógica condicional para isso: só formata o
    que veio. Vale para os 3 KPIs de temperatura, não só a anomalia."""
    nums = [v for v in values if v is not None]
    return round(sum(nums) / len(nums), 1) if nums else None


def _resumo(rows: list[dict]) -> ClimaResumo:
    """Espelha `climate.agg({...}).round(1)` + as 2 métricas da aba
    Precipitação do Streamlit (média sobre dias presentes; soma de chuva;
    contagem de dias com chuva)."""
    precip = [r["precipitation_mm"] for r in rows if r["precipitation_mm"] is not None]
    return ClimaResumo(
        temp_max_mean=_mean([r["temp_max_c"] for r in rows]),
        temp_min_mean=_mean([r["temp_min_c"] for r in rows]),
        temp_anomaly_mean=_mean([r["temp_anomaly_c"] for r in rows]),
        precip_total=round(sum(precip), 1) if precip else 0.0,
        dias_chuva=sum(1 for v in precip if v > 0),
        dias_total=len(rows),
    )


@router.get("/lista", response_model=list[CidadeMeta])
def get_lista() -> list[dict]:
    """Os 295 municípios do seed com `mesoregion`, `latitude`, `longitude`,
    `altitude_m` (para o selectbox e o cabeçalho). Endpoint dedicado — o
    `/api/v1/ref/cidades` compartilhado devolve só os nomes (spec 014)."""
    return _lista()


@router.get("/clima", response_model=ClimaResponse)
def get_clima(
    city: str = Query(..., min_length=1, description="Município (da lista de /api/v1/cidades/lista)"),
    days: int = Query(90, ge=30, le=365, description="Janela em dias (30–365, default 90)"),
) -> ClimaResponse:
    _require_city(city)
    anchor = max_date(_DAILY)
    if anchor is None:
        return ClimaResponse()
    rows = query(
        f"""
        SELECT date, temp_max_c, temp_min_c, temp_avg_c, temp_anomaly_c,
               precipitation_mm, precipitation_class, wind_speed_max_kmh, uv_index_max
        FROM {tbl(_DAILY)}
        WHERE city_name = @city
          AND date >= DATE_SUB(@max_date, INTERVAL @days DAY)
        ORDER BY date
        """,
        params={"city": city, "max_date": anchor, "days": days},
    )
    if not rows:
        return ClimaResponse()
    return ClimaResponse(resumo=_resumo(rows), rows=rows)


@router.get("/alertas", response_model=AlertasResponse)
def get_alertas(
    city: str = Query(..., min_length=1),
    days: int = Query(90, ge=30, le=365),
) -> AlertasResponse:
    _require_city(city)
    anchor = max_date(_ALERTS)
    if anchor is None:
        return AlertasResponse()
    rows = query(
        f"""
        SELECT date, alert_type, severity,
               ROUND(temp_max_c, 1)         AS temp_max,
               ROUND(temp_anomaly_c, 1)     AS anomalia,
               ROUND(precipitation_mm, 1)   AS precip,
               ROUND(wind_speed_max_kmh, 1) AS vento,
               uv_index_max
        FROM {tbl(_ALERTS)}
        WHERE city_name = @city
          AND date >= DATE_SUB(@max_date, INTERVAL @days DAY)
        ORDER BY date DESC
        LIMIT 100
        """,
        params={"city": city, "max_date": anchor, "days": days},
    )
    return AlertasResponse(
        rows=[
            AlertaRow(
                date=r["date"],
                alert_type=r["alert_type"],
                alert_type_pt=ALERT_TYPE_PT.get(r["alert_type"], r["alert_type"]),
                severity=r["severity"],
                severity_pt=SEVERITY_PT.get(r["severity"], r["severity"]),
                temp_max=r["temp_max"],
                anomalia=r["anomalia"],
                precip=r["precip"],
                vento=r["vento"],
                uv_index_max=r["uv_index_max"],
            )
            for r in rows
        ]
    )
