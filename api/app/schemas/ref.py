"""Modelos de resposta da camada de referência compartilhada (spec 014).

`/ref/mesorregioes` e `/ref/cidades` respondem `list[str]` puro (sem modelo
próprio). Só os dois endpoints `*-meta` têm corpo estruturado — `min_date`
e `max_date` de uma mart, ambos nulos quando a tabela está vazia (spec 014,
Casos de Borda).
"""

from datetime import date

from pydantic import BaseModel, Field


class DailyMetaResponse(BaseModel):
    """`MIN(date)` / `MAX(date)` de `mart_climate__daily_facts` — âncora dos
    filtros de período das páginas que leem daily facts (007, 008, 011, 012,
    013). Absorve o antigo `/api/v1/relatorio-cidade/limites` (spec 013)."""

    min_date: date | None = Field(None, description="Primeira data com dado (nula se a mart está vazia)")
    max_date: date | None = Field(None, description="Última data com dado (nula se a mart está vazia)")


class AlertsMetaResponse(BaseModel):
    """`MIN(date)` / `MAX(date)` de `mart_climate__alerts` (spec 009, 011).
    Pode divergir de `DailyMetaResponse` — tabelas atualizadas por passos
    diferentes do pipeline; por isso são dois endpoints (spec 014)."""

    min_date: date | None = Field(None, description="Primeira data com alerta (nula se a mart está vazia)")
    max_date: date | None = Field(None, description="Última data com alerta (nula se a mart está vazia)")
