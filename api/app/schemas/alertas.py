"""Modelos de resposta da página Alertas (spec 009).

A tradução de `alert_type` / `severity` acontece no **backend** (spec 009 /
014: `api/app/utils/labels.py`), então cada linha traz o valor cru **e** o
rótulo PT. A cor/ícone por severidade continuam só no frontend
(`web/src/labels.ts`) — por isso o valor cru de `severity` vai junto.
"""

from datetime import date

from pydantic import BaseModel, Field


class ResumoResponse(BaseModel):
    """Os 5 KPIs (Total + contagem por severidade)."""

    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class PorTipoRow(BaseModel):
    alert_type: str = Field(..., description="Valor cru do enum")
    alert_type_pt: str = Field(..., description="Rótulo PT (fallback = valor cru)")
    severity: str = Field(..., description="Valor cru (para cor/ícone no cliente)")
    severity_pt: str = Field(..., description="Rótulo PT (fallback = valor cru)")
    qtd: int = 0


class PorTipoResponse(BaseModel):
    rows: list[PorTipoRow] = Field(default_factory=list)


class MunicipioRow(BaseModel):
    city_name: str
    mesoregion: str | None = None
    alertas: int = 0


class MunicipiosResponse(BaseModel):
    """15 linhas quando sem mesorregião; todas (LIMIT 300) quando filtrado."""

    rows: list[MunicipioRow] = Field(default_factory=list)


class RecenteRow(BaseModel):
    date: date
    city_name: str
    mesoregion: str | None = None
    alert_type: str
    alert_type_pt: str
    severity: str
    severity_pt: str
    temp_max: float | None = None
    anomalia: float | None = None
    precip: float | None = None
    vento_max: float | None = None
    uv_index_max: float | None = None


class RecentesResponse(BaseModel):
    """Até 200 linhas, `date DESC, severity ASC` (ordenação alfabética de
    severity — paridade com o Streamlit, não "corrigida" na migração)."""

    rows: list[RecenteRow] = Field(default_factory=list)
