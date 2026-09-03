"""Modelo de resposta da página Chuva Acumulada (spec 022).

Ranking de precipitação acumulada por município na janela. Sem linha de
total — a soma de chuva entre municípios não é grandeza física útil.
"""

import datetime

from pydantic import BaseModel, Field


class ChuvaAcumuladaRow(BaseModel):
    city_name: str
    mesoregion: str | None = None
    precip_acumulada: float | None = None
    dias_chuva: int = 0
    maior_dia_mm: float | None = None
    maior_dia_data: datetime.date | None = None


class RelatorioChuvaAcumuladaResponse(BaseModel):
    rows: list[ChuvaAcumuladaRow] = Field(default_factory=list)
