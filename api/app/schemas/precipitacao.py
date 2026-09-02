"""Modelos de resposta da página Precipitação (spec 008).

Três endpoints (ranking / intensidade / heatmap). O rótulo PT e a cor por
`precipitation_class` NÃO entram na resposta — são apresentação e vivem em
`web/src/labels.ts` (spec 014). A resposta devolve o valor cru do enum.
"""

from datetime import date

from pydantic import BaseModel, Field


class RankingItem(BaseModel):
    city_name: str
    mesoregion: str | None = None
    total_mm: float | None = Field(None, description="SUM(precipitation_mm) na janela (mm, 1 casa)")
    dias_chuva: int = Field(0, description="Nº de dias com precipitation_mm > 0")


class RankingResponse(BaseModel):
    """`limit` já resolvido no servidor: 20 quando sem mesorregião, 300
    (todos) quando filtrado (paridade com o Streamlit)."""

    rows: list[RankingItem] = Field(default_factory=list)


class IntensidadeRow(BaseModel):
    precipitation_class: str | None = Field(None, description="Valor cru do enum (traduzido no cliente)")
    qtd: int = 0


class IntensidadeResponse(BaseModel):
    rows: list[IntensidadeRow] = Field(default_factory=list)


class HeatmapRow(BaseModel):
    date: date
    mesoregion: str | None = None
    avg_precip: float | None = Field(None, description="AVG(precipitation_mm) do dia × mesorregião (mm, 1 casa)")


class HeatmapResponse(BaseModel):
    """Sempre todas as mesorregiões — este endpoint ignora `meso` (paridade
    com o Streamlit)."""

    rows: list[HeatmapRow] = Field(default_factory=list)
