"""Modelos de resposta da página Comparativo (spec 012).

4 endpoints, 1 por bloco de dado das 3 abas (a aba 3 usa 2). Resumos
(`min`/`max`/`mean` por cidade; desvio médio/máx/mín) são calculados no
servidor para garantir paridade numérica com o `groupby`/`merge` do pandas.
"""

from datetime import date

from pydantic import BaseModel, Field


class SerieRow(BaseModel):
    date: date
    city_name: str
    valor: float | None = None


class ResumoCidade(BaseModel):
    city_name: str
    min: float | None = None
    max: float | None = None
    mean: float | None = None


class CidadesSerieResponse(BaseModel):
    rows: list[SerieRow] = Field(default_factory=list)
    resumo: list[ResumoCidade] = Field(default_factory=list)


class ChuvaHeatmapRow(BaseModel):
    date: date
    city_name: str
    precipitation_mm: float | None = None


class ChuvaHeatmapResponse(BaseModel):
    rows: list[ChuvaHeatmapRow] = Field(default_factory=list)


class DatasDisponiveisResponse(BaseModel):
    """Últimas 60 datas distintas com dado horário para o município."""

    dates: list[date] = Field(default_factory=list)


class PerfilHoraRow(BaseModel):
    hour: int
    temp: float | None = None
    humidity: float | None = None


class HistHoraRow(BaseModel):
    hour: int
    avg_temp: float | None = None
    avg_humidity: float | None = None


class DesvioResumo(BaseModel):
    medio: float | None = None
    maximo: float | None = None
    minimo: float | None = None


class DiaVsHistoricoResponse(BaseModel):
    atual: list[PerfilHoraRow] = Field(default_factory=list)
    historico: list[HistHoraRow] = Field(
        default_factory=list,
        description="Média horária de [date-30d, date) — EXCLUI o próprio dia (paridade)",
    )
    desvio: DesvioResumo | None = Field(
        None, description="Nulo quando não há histórico (data de referência é a mais antiga)"
    )
