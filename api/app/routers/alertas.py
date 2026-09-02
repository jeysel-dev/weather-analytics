"""Endpoints JSON da página Alertas (spec 009).

- GET /api/v1/alertas/resumo     -> 5 KPIs (total + por severidade)
- GET /api/v1/alertas/por-tipo   -> COUNT(*) por alert_type × severity (com rótulo PT)
- GET /api/v1/alertas/municipios -> COUNT(*) por município (15 / todos)
- GET /api/v1/alertas/recentes   -> até 200 linhas, date DESC / severity ASC

Todos compartilham o mesmo `WHERE` base (`days` 7–60, `meso` opcional,
`severity` opcional). Janela ancorada em `max_date('mart_climate__alerts')`
— âncora própria, pode divergir da de `daily_facts`.
"""

from typing import Literal

from fastapi import APIRouter, Query

from app.routers.ref import meso_filter
from app.schemas.alertas import (
    MunicipiosResponse,
    PorTipoResponse,
    PorTipoRow,
    RecenteRow,
    RecentesResponse,
    ResumoResponse,
)
from app.utils.bigquery import max_date, query, tbl
from app.utils.labels import ALERT_TYPE_PT, SEVERITY_PT

router = APIRouter(prefix="/alertas", tags=["alertas"])

_ALERTS = "mart_climate__alerts"

Severity = Literal["critical", "high", "medium", "low"]


def _base_where(days: int, meso: str | None, severity: str | None) -> tuple[str, dict]:
    """`WHERE` comum às 4 queries (paridade com o `base_where` do Streamlit)."""
    clause = "date >= DATE_SUB(@max_date, INTERVAL @days DAY)"
    params: dict = {"days": days}
    meso_clause, meso_params = meso_filter(meso)
    if meso_clause:
        clause += f"\n          {meso_clause}"
        params.update(meso_params)
    if severity is not None:
        clause += "\n          AND severity = @severity"
        params["severity"] = severity
    return clause, params


@router.get("/resumo", response_model=ResumoResponse)
def get_resumo(
    days: int = Query(30, ge=7, le=60),
    meso: str | None = Query(None),
    severity: Severity | None = Query(None),
) -> ResumoResponse:
    anchor = max_date(_ALERTS)
    if anchor is None:
        return ResumoResponse()
    where, params = _base_where(days, meso, severity)
    rows = query(
        f"""
        SELECT
          COUNT(*)                       AS total,
          COUNTIF(severity = 'critical') AS critical,
          COUNTIF(severity = 'high')     AS high,
          COUNTIF(severity = 'medium')   AS medium,
          COUNTIF(severity = 'low')      AS low
        FROM {tbl(_ALERTS)}
        WHERE {where}
        """,
        params={"max_date": anchor, **params},
    )
    return ResumoResponse(**rows[0]) if rows else ResumoResponse()


@router.get("/por-tipo", response_model=PorTipoResponse)
def get_por_tipo(
    days: int = Query(30, ge=7, le=60),
    meso: str | None = Query(None),
    severity: Severity | None = Query(None),
) -> PorTipoResponse:
    anchor = max_date(_ALERTS)
    if anchor is None:
        return PorTipoResponse()
    where, params = _base_where(days, meso, severity)
    rows = query(
        f"""
        SELECT alert_type, severity, COUNT(*) AS qtd
        FROM {tbl(_ALERTS)}
        WHERE {where}
        GROUP BY alert_type, severity
        ORDER BY qtd DESC
        """,
        params={"max_date": anchor, **params},
    )
    return PorTipoResponse(
        rows=[
            PorTipoRow(
                alert_type=r["alert_type"],
                alert_type_pt=ALERT_TYPE_PT.get(r["alert_type"], r["alert_type"]),
                severity=r["severity"],
                severity_pt=SEVERITY_PT.get(r["severity"], r["severity"]),
                qtd=r["qtd"],
            )
            for r in rows
        ]
    )


@router.get("/municipios", response_model=MunicipiosResponse)
def get_municipios(
    days: int = Query(30, ge=7, le=60),
    meso: str | None = Query(None),
    severity: Severity | None = Query(None),
) -> MunicipiosResponse:
    anchor = max_date(_ALERTS)
    if anchor is None:
        return MunicipiosResponse()
    where, params = _base_where(days, meso, severity)
    limit = 15 if not (meso and meso != "Todas") else 300
    rows = query(
        f"""
        SELECT city_name, mesoregion, COUNT(*) AS alertas
        FROM {tbl(_ALERTS)}
        WHERE {where}
        GROUP BY city_name, mesoregion
        ORDER BY alertas DESC
        LIMIT @limit
        """,
        params={"max_date": anchor, "limit": limit, **params},
    )
    return MunicipiosResponse(rows=rows)


@router.get("/recentes", response_model=RecentesResponse)
def get_recentes(
    days: int = Query(30, ge=7, le=60),
    meso: str | None = Query(None),
    severity: Severity | None = Query(None),
) -> RecentesResponse:
    anchor = max_date(_ALERTS)
    if anchor is None:
        return RecentesResponse()
    where, params = _base_where(days, meso, severity)
    rows = query(
        f"""
        SELECT
          date, city_name, mesoregion, alert_type, severity,
          ROUND(temp_max_c, 1)         AS temp_max,
          ROUND(temp_anomaly_c, 1)     AS anomalia,
          ROUND(precipitation_mm, 1)   AS precip,
          ROUND(wind_speed_max_kmh, 1) AS vento_max,
          uv_index_max
        FROM {tbl(_ALERTS)}
        WHERE {where}
        ORDER BY date DESC, severity ASC
        LIMIT 200
        """,
        params={"max_date": anchor, **params},
    )
    return RecentesResponse(
        rows=[
            RecenteRow(
                date=r["date"],
                city_name=r["city_name"],
                mesoregion=r["mesoregion"],
                alert_type=r["alert_type"],
                alert_type_pt=ALERT_TYPE_PT.get(r["alert_type"], r["alert_type"]),
                severity=r["severity"],
                severity_pt=SEVERITY_PT.get(r["severity"], r["severity"]),
                temp_max=r["temp_max"],
                anomalia=r["anomalia"],
                precip=r["precip"],
                vento_max=r["vento_max"],
                uv_index_max=r["uv_index_max"],
            )
            for r in rows
        ]
    )
