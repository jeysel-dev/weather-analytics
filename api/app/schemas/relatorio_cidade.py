"""Modelo de resposta da página Relatório por Cidade (spec 013).

Um único endpoint (`/dados`): uma linha consolidada por cidade. Sem gráfico
— esta página é puramente tabular (spec 013, Design).
"""

from pydantic import BaseModel, Field


class RelatorioRow(BaseModel):
    city_name: str
    temp_maxima: float | None = Field(None, description="MAX(temp_max_c) (°C, 1 casa)")
    temp_maxima_media: float | None = Field(None, description="AVG(temp_max_c) (°C, 1 casa)")
    temp_minima: float | None = Field(None, description="MIN(temp_min_c) (°C, 1 casa)")
    temp_minima_media: float | None = Field(None, description="AVG(temp_min_c) (°C, 1 casa)")
    precip_acumulada: float | None = Field(None, description="SUM(precipitation_mm) (mm, 1 casa)")
    vento_maximo: float | None = Field(None, description="MAX(wind_speed_max_kmh) (km/h, 1 casa)")


class RelatorioResponse(BaseModel):
    rows: list[RelatorioRow] = Field(default_factory=list)
