"""Modelo de resposta da página Relatório por Cidade (spec 013, redesenho).

Um único endpoint (`/dados`). A resposta tem três partes:

- `dias`: uma linha por cidade × dia do período (sem agregação).
- `subtotais`: uma linha agregada por cidade (MAX/AVG/MIN/AVG/SUM/MAX).
- `total_geral`: uma linha agregando todas as cidades/dias juntos —
  presente mesmo quando só uma cidade foi selecionada.

Sem gráfico — esta página é puramente tabular (spec 013, Design).
"""

from datetime import date

from pydantic import BaseModel, Field


class DiaRow(BaseModel):
    date: date
    city_name: str
    temp_max_c: float | None = None
    temp_min_c: float | None = None
    precipitation_mm: float | None = None
    wind_speed_max_kmh: float | None = None


class SubtotalRow(BaseModel):
    city_name: str  # nome real da cidade, ou "Total Geral" pro agregado final
    temp_maxima: float | None = None
    temp_maxima_media: float | None = None
    temp_minima: float | None = None
    temp_minima_media: float | None = None
    precip_acumulada: float | None = None
    vento_maximo: float | None = None


class RelatorioResponse(BaseModel):
    dias: list[DiaRow] = Field(default_factory=list)
    subtotais: list[SubtotalRow] = Field(default_factory=list)
    total_geral: SubtotalRow | None = None
