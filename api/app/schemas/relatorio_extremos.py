"""Modelo de resposta da página Extremos e Recordes (spec 022).

Seis linhas em ordem fixa — um recorde por indicador na janela. `valor` /
`city_name` / `date` vêm nulos quando a janela não tem dado para aquele
indicador (`SAFE_OFFSET(0)` sobre um `ARRAY_AGG` vazio).
"""

import datetime

from pydantic import BaseModel, Field


class ExtremoRow(BaseModel):
    indicador: str
    valor: float | None = None
    city_name: str | None = None
    date: datetime.date | None = None


class RelatorioExtremosResponse(BaseModel):
    rows: list[ExtremoRow] = Field(default_factory=list)
