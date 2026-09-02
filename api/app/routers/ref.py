"""Camada de referência compartilhada — `GET /api/v1/ref/*` (spec 014).

Infraestrutura transversal da migração FastAPI: os dados de referência que
quase toda página migrada precisa (lista de municípios, lista de
mesorregiões, data mínima/máxima por mart) definidos UMA vez aqui, em vez
de repetidos em cada spec de página (007-009, 011-013). Esta spec não tem
página consumidora — as rotas de página passam a chamar estes endpoints
quando forem implementadas.

Rotas síncronas (`def`) — threadpool do Starlette, cliente BigQuery
síncrono reaproveitado (spec 006/010).

Cache:
- `/mesorregioes` e `/cidades` -> `@lru_cache(maxsize=1)`, mesmo padrão e
  justificativa de `_cidades()` em `horario.py`: as listas só mudam quando
  o seed `locations` muda (raríssimo); sem TTL, sem invalidação automática
  (spec 014, Não-funcionais e "Fora do escopo").
- `/daily-meta` e `/alerts-meta` -> SEM cache: `max_date` muda a cada run
  do pipeline (1x/dia). A spec permite cache curtíssimo; optamos por
  nenhum — a query é `MIN`/`MAX` sobre coluna de partição, barata, e o
  BigQuery ainda tem cache de resultado server-side (24h, sem custo) para
  SQL idêntico.
"""

from functools import lru_cache

from fastapi import APIRouter, HTTPException

from app.schemas.ref import AlertsMetaResponse, DailyMetaResponse
from app.utils.bigquery import max_date, min_date, query, tbl

router = APIRouter(prefix="/ref", tags=["ref"])

_DAILY = "mart_climate__daily_facts"
_ALERTS = "mart_climate__alerts"


@lru_cache(maxsize=1)
def _mesorregioes() -> list[str]:
    rows = query(
        f"""
        SELECT DISTINCT mesoregion
        FROM {tbl('locations', seeds=True)}
        WHERE mesoregion IS NOT NULL
        ORDER BY mesoregion
        """
    )
    return [row["mesoregion"] for row in rows]


@lru_cache(maxsize=1)
def _cidades() -> list[str]:
    rows = query(
        f"""
        SELECT city_name
        FROM {tbl('locations', seeds=True)}
        ORDER BY city_name
        """
    )
    return [row["city_name"] for row in rows]


# ── Reuso pelas páginas (007/008/009/011/012/013) ───────────────────────────
# As páginas migradas NÃO reimplementam a query nem o cache das listas de
# referência (spec 014): validam o filtro/parâmetro contra a mesma allowlist
# cacheada aqui, via as funções abaixo — `_mesorregioes()` / `_cidades()`
# continuam privados.
def require_meso(meso: str) -> None:
    """Allowlist: `meso` tem que estar na lista do seed antes de entrar numa
    query (defesa em profundidade — o valor já vai como parâmetro do
    BigQuery, mas isto dá um 404 claro para uma mesorregião inexistente)."""
    if meso not in _mesorregioes():
        raise HTTPException(status_code=404, detail=f"Mesorregião desconhecida: {meso!r}")


def require_cidade(city: str) -> None:
    """Allowlist de município contra o seed `locations` (usada por 012/013)."""
    if city not in _cidades():
        raise HTTPException(status_code=404, detail=f"Município desconhecido: {city!r}")


def meso_filter(meso: str | None) -> tuple[str, dict]:
    """Cláusula SQL opcional `AND mesoregion = @meso` + o parâmetro nomeado.

    `("", {})` quando não há filtro (`None` ou `"Todas"` — paridade com o
    `meso_clause` vazio do Streamlit); valida `meso` contra a allowlist do
    seed quando há filtro. Usada pelas páginas 007/008/009."""
    if meso is None or meso == "Todas":
        return "", {}
    require_meso(meso)
    return "AND mesoregion = @meso", {"meso": meso}


@router.get("/mesorregioes", response_model=list[str])
def get_mesorregioes() -> list[str]:
    """Mesorregiões distintas do seed `locations` (`mesoregion IS NOT NULL`,
    ordenadas). Único lugar onde essa query é definida (spec 014) — filtro
    de mesorregião das páginas 007, 008, 009, 012 consome este endpoint.
    Seed vazio/inacessível -> lista vazia (spec 014, Casos de Borda)."""
    return _mesorregioes()


@router.get("/cidades", response_model=list[str])
def get_cidades() -> list[str]:
    """`city_name` do seed `locations` ordenado — só os nomes, sem
    metadados (spec 014, Design: lat/lon/altitude/mesorregião ficam no
    `/api/v1/cidades/lista` da futura página Cidades, spec 011).
    Consumido por 012, 013."""
    return _cidades()


@router.get("/daily-meta", response_model=DailyMetaResponse)
def get_daily_meta() -> DailyMetaResponse:
    """`MIN(date)` / `MAX(date)` de `mart_climate__daily_facts`. Mart vazia
    -> ambos nulos, não erro (spec 014, Casos de Borda)."""
    return DailyMetaResponse(min_date=min_date(_DAILY), max_date=max_date(_DAILY))


@router.get("/alerts-meta", response_model=AlertsMetaResponse)
def get_alerts_meta() -> AlertsMetaResponse:
    """`MIN(date)` / `MAX(date)` de `mart_climate__alerts`. Mart vazia ->
    ambos nulos, não erro (spec 014, Casos de Borda)."""
    return AlertsMetaResponse(min_date=min_date(_ALERTS), max_date=max_date(_ALERTS))
