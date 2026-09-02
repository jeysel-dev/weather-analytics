"""Modelos de resposta da página Cidades / "Perfil por Município" (spec 011).

`/api/v1/cidades/lista` é endpoint PRÓPRIO (não `/api/v1/ref/cidades`):
traz os metadados (lat/lon/altitude/mesorregião) que só esta página usa.
`altitude_m` nulo é tratado no cliente com placeholder `—` (correção
deliberada de robustez, spec 011 — não é bug a replicar).
"""

from datetime import date

from pydantic import BaseModel, Field


class CidadeMeta(BaseModel):
    city_name: str
    mesoregion: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None


class ClimaRow(BaseModel):
    date: date
    temp_max_c: float | None = None
    temp_min_c: float | None = None
    temp_avg_c: float | None = None
    temp_anomaly_c: float | None = None
    precipitation_mm: float | None = None
    precipitation_class: str | None = None
    wind_speed_max_kmh: float | None = None
    uv_index_max: float | None = None


class ClimaResumo(BaseModel):
    """Agregados calculados no servidor — batem com o `pandas.agg(...).round(1)`
    do Streamlit (média sobre dias presentes, soma de precipitação)."""

    temp_max_mean: float | None = None
    temp_min_mean: float | None = None
    temp_anomaly_mean: float | None = None
    precip_total: float | None = None
    dias_chuva: int = 0
    dias_total: int = 0


class ClimaResponse(BaseModel):
    resumo: ClimaResumo | None = Field(
        None, description="Nulo quando não há linha no período (frontend mostra 'Sem dados…')"
    )
    rows: list[ClimaRow] = Field(default_factory=list)


class AlertaRow(BaseModel):
    date: date
    alert_type: str
    alert_type_pt: str
    severity: str
    severity_pt: str
    temp_max: float | None = None
    anomalia: float | None = None
    precip: float | None = None
    vento: float | None = None
    uv_index_max: float | None = None


class AlertasResponse(BaseModel):
    rows: list[AlertaRow] = Field(default_factory=list)
