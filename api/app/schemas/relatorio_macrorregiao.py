"""Modelo de resposta da página Por Macrorregião (spec 022).

Uma linha por macrorregião (as 8 do seed `locations`) + uma linha de total
geral (agregado do estado). `alertas` vem de `mart_climate__alerts` (âncora
própria) casada por macrorregião com a agregação de `daily_facts`.
"""

from pydantic import BaseModel, Field


class MacrorregiaoRow(BaseModel):
    mesoregion: str  # nome da macrorregião, ou "Total Geral"
    municipios: int = 0
    temp_max_media: float | None = None
    temp_min_media: float | None = None
    precip_media: float | None = None
    precip_acumulada: float | None = None
    alertas: int = 0


class RelatorioMacrorregiaoResponse(BaseModel):
    rows: list[MacrorregiaoRow] = Field(default_factory=list)
    total_geral: MacrorregiaoRow | None = None
