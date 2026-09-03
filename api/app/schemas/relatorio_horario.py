"""Modelo de resposta da página Detalhamento Horário (spec 023).

Dado horário (`mart_climate__hourly_facts`) de um município + janela,
apresentado em duas tabelas: extremos do período (com o instante) e
resumo diário (com linha de total).
"""

import datetime

from pydantic import BaseModel, Field


class ExtremoHorario(BaseModel):
    indicador: str
    valor: float | None = None
    quando: str | None = Field(
        None, description="Instante do extremo, já formatado em America/Sao_Paulo"
    )


class DiaHorario(BaseModel):
    date: datetime.date | None = None  # nulo na linha de total
    temp_min: float | None = None
    temp_avg: float | None = None
    temp_max: float | None = None
    humidity_min: float | None = None
    humidity_avg: float | None = None
    humidity_max: float | None = None
    precip_total: float | None = None
    wind_max: float | None = None


class RelatorioHorarioResponse(BaseModel):
    max_date: datetime.date | None = None
    extremos: list[ExtremoHorario] = Field(default_factory=list)
    dias: list[DiaHorario] = Field(default_factory=list)
    total: DiaHorario | None = None
