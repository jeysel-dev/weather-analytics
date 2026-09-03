"""Modelos de resposta da página Temperatura (spec 007).

Três endpoints, um por bloco visual (rankings / tendência / heatmap de
anomalia) — cada um com janela e filtro próprios (ver spec 007, Design).
"""

from datetime import date

from pydantic import BaseModel, Field


class RankingItem(BaseModel):
    """Um município num dos rankings da janela `days`."""

    city_name: str
    mesoregion: str | None = None
    media: float | None = Field(
        None,
        description="AVG(temp_max_c) no ranking de quentes, AVG(temp_min_c) no de frios (°C, 1 casa)",
    )


class RankingsResponse(BaseModel):
    """Os dois rankings (quentes / frios) na janela `days` da página."""

    quentes: list[RankingItem] = Field(default_factory=list)
    frios: list[RankingItem] = Field(default_factory=list)


class TendenciaRow(BaseModel):
    date: date
    mesoregion: str | None = None
    temp_avg: float | None = Field(None, description="AVG(temp_avg_c) do dia × mesorregião (°C, 1 casa)")


class TendenciaResponse(BaseModel):
    rows: list[TendenciaRow] = Field(default_factory=list)


class AnomaliaRow(BaseModel):
    date: date
    mesoregion: str | None = None
    anomaly: float | None = Field(None, description="AVG(temp_anomaly_c) do dia × mesorregião (°C, 2 casas)")


class AnomaliaResponse(BaseModel):
    """Heatmap de anomalia térmica — sempre todas as mesorregiões (o filtro
    `meso` não se aplica a este endpoint, paridade com o Streamlit)."""

    rows: list[AnomaliaRow] = Field(default_factory=list)
