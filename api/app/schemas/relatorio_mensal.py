"""Modelo de resposta da página Consolidado Mensal (spec 022).

Mesmo formato de 3 partes do `/relatorio-cidade`: linhas (cidade × mês),
subtotal agregado por cidade e total geral (agregando tudo). As médias
mensais são recalculadas a partir das linhas diárias em cada nível — nunca
"média de médias".
"""

from pydantic import BaseModel, Field


class MesRow(BaseModel):
    year_month: str  # "YYYY-MM"
    city_name: str
    temp_max_media: float | None = None
    temp_min_media: float | None = None
    amplitude_media: float | None = None
    precip_acumulada: float | None = None
    dias_chuva: int = 0
    vento_maximo: float | None = None


class MensalAgg(BaseModel):
    """Linha agregada — subtotal por cidade ou total geral."""

    city_name: str  # nome da cidade, ou "Total Geral"
    temp_max_media: float | None = None
    temp_min_media: float | None = None
    amplitude_media: float | None = None
    precip_acumulada: float | None = None
    dias_chuva: int = 0
    vento_maximo: float | None = None


class RelatorioMensalResponse(BaseModel):
    meses: list[MesRow] = Field(default_factory=list)
    subtotais: list[MensalAgg] = Field(default_factory=list)
    total_geral: MensalAgg | None = None
