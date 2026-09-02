"""Modelos de resposta da página Horário (spec 010).

Três endpoints: `/cidades` (lista de string, sem modelo próprio),
`/serie` (`SerieResponse`) e `/padrao-24h` (`Padrao24hResponse`).
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class SerieRow(BaseModel):
    """Uma observação horária. As abas "Temperatura & Umidade" e
    "Vento & Chuva" leem a mesma série (mesmo `WHERE`, mesmo grão) — só
    mudam as colunas plotadas."""

    observed_at: datetime = Field(..., description="Timestamp da observação (ISO 8601, UTC)")
    temperature_c: float | None = Field(None, description="Temperatura (°C)")
    relative_humidity_pct: float | None = Field(None, description="Umidade relativa (%)")
    wind_speed_kmh: float | None = Field(None, description="Velocidade do vento (km/h)")
    precipitation_mm: float | None = Field(None, description="Precipitação (mm)")


class SerieResponse(BaseModel):
    max_date: date | None = Field(
        None,
        description=(
            "MAX(date) da `mart_climate__hourly_facts` filtrado por este município "
            "(âncora por município, para a caption). Nulo quando o município não tem "
            "dado horário."
        ),
    )
    rows: list[SerieRow] = Field(default_factory=list)


class Padrao24hRow(BaseModel):
    """Perfil médio de uma das 24 horas do dia."""

    hour: int = Field(..., ge=0, le=23, description="Hora do dia (0–23)")
    avg_temp: float | None = Field(None, description="Temperatura média (°C)")
    avg_humidity: float | None = Field(None, description="Umidade média (%)")
    avg_wind: float | None = Field(
        None,
        description="Vento médio (km/h). Disponível no payload mas não plotado (paridade com o Streamlit).",
    )
    avg_precip_dia: float | None = Field(
        None,
        description="Precipitação média por dia (mm) = SUM(precip) / NULLIF(COUNT(DISTINCT date), 0)",
    )


class Padrao24hResponse(BaseModel):
    rows: list[Padrao24hRow] = Field(default_factory=list)
