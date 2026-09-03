import json
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import (
    alertas,
    cidades,
    comparativo,
    horario,
    precipitacao,
    ref,
    relatorio_cidade,
    temperatura,
)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"


def _load_main_entry() -> dict:
    """Lê o manifest do Vite (spec 006) e resolve o nome real, com hash de
    conteúdo, do entrypoint `src/main.ts`.

    Falha explícita (`RuntimeError`) se o build do frontend não rodou — nunca
    cai para um nome de asset fixo sem hash. É chamada em nível de módulo,
    antes da app existir: se o manifest não está lá, a API não sobe.
    """
    manifest_path = STATIC_DIR / ".vite" / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(
            f"manifest do Vite não encontrado em {manifest_path} — rode "
            "`npm run build` em web/ antes de iniciar a API (spec 006)"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest.get("src/main.ts")
    if entry is None or "file" not in entry:
        raise RuntimeError(
            f"manifest do Vite ({manifest_path}) não tem entrada válida para "
            "src/main.ts (spec 006)"
        )
    return entry


_main_entry = _load_main_entry()
STATIC_MAIN_JS = f"/static/api/{_main_entry['file']}"
STATIC_MAIN_CSS = [f"/static/api/{css}" for css in _main_entry.get("css", [])]


app = FastAPI(
    title="Weather Analytics — API",
    description="Camada de serving do dashboard: páginas Jinja2 + endpoints JSON (spec 006).",
    version="0.1.0",
)

app.mount("/static/api", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["main_js"] = STATIC_MAIN_JS
templates.env.globals["main_css"] = STATIC_MAIN_CSS


# ── Estrutura central de páginas (spec 006) ──────────────────────────────────
# Fonte única: as rotas de página E o menu de navegação saem daqui. Ao
# contrário de compras-publicas-sc (onde o menu é hardcoded no layout.html,
# separado das rotas — o que já produziu páginas órfãs de menu), aqui não é
# possível registrar uma rota e esquecer o item de menu: os dois campos são
# obrigatórios na dataclass.
@dataclass(frozen=True)
class Page:
    path: str
    template: str
    page_id: str  # vira document.body.dataset.page -> dispatch em web/src/main.ts
    menu_label: str
    menu_icon: str
    menu_position: int
    # Rótulo do submenu ao qual este item pertence ("Relatórios"). None = item
    # de topo. Ver `_build_menu` — a rota continua saindo de `path`, o submenu
    # é só agrupamento visual (spec 017).
    menu_group: str | None = None


@dataclass(frozen=True)
class MenuGroup:
    """Item de navegação que não é uma página: agrupa `children` num submenu.
    `menu_position` = a do primeiro filho, pra o grupo ordenar junto com os
    itens de topo (spec 017)."""

    label: str
    children: tuple[Page, ...]

    @property
    def menu_position(self) -> int:
        return min(child.menu_position for child in self.children)


PAGES: tuple[Page, ...] = (
    Page(
        path="/",
        template="home.html",
        page_id="home",
        menu_label="Início",
        menu_icon="🏠",
        menu_position=0,
    ),
    Page(
        path="/temperatura",
        template="temperatura.html",
        page_id="temperatura",
        menu_label="Temperatura",
        menu_icon="🌡️",
        menu_position=1,
    ),
    Page(
        path="/precipitacao",
        template="precipitacao.html",
        page_id="precipitacao",
        menu_label="Precipitação",
        menu_icon="🌧️",
        menu_position=2,
    ),
    Page(
        path="/alertas",
        template="alertas.html",
        page_id="alertas",
        menu_label="Alertas",
        menu_icon="🚨",
        menu_position=3,
    ),
    Page(
        path="/horario",
        template="horario.html",
        page_id="horario",
        menu_label="Horário",
        menu_icon="🕐",
        # Posição 4 = mesma do Streamlit (streamlit/pages/4_Horario.py).
        menu_position=4,
    ),
    Page(
        path="/cidades",
        template="cidades.html",
        page_id="cidades",
        menu_label="Cidades",
        menu_icon="🏙️",
        menu_position=5,
    ),
    Page(
        path="/comparativo",
        template="comparativo.html",
        page_id="comparativo",
        menu_label="Comparativo",
        menu_icon="🔍",
        menu_position=6,
    ),
    Page(
        path="/relatorio-cidade",
        template="relatorio-cidade.html",
        page_id="relatorio-cidade",
        menu_label="Relatório por Cidade",
        menu_icon="📋",
        menu_position=7,
        menu_group="Relatórios",
    ),
)


def _build_menu(pages: tuple[Page, ...]) -> tuple[Page | MenuGroup, ...]:
    """Achata `PAGES` na árvore de navegação: itens sem `menu_group` ficam no
    topo; os que têm um `menu_group` são recolhidos num `MenuGroup` com aquele
    rótulo. Tudo ordenado por `menu_position` (o grupo herda a do 1º filho).
    Estende a "estrutura central" da spec 006 — segue sendo impossível ter
    rota sem item de menu (spec 017)."""
    top: list[Page | MenuGroup] = []
    groups: dict[str, list[Page]] = {}
    for page in sorted(pages, key=lambda p: p.menu_position):
        if page.menu_group is None:
            top.append(page)
        else:
            groups.setdefault(page.menu_group, []).append(page)
    top.extend(MenuGroup(label=label, children=tuple(children)) for label, children in groups.items())
    return tuple(sorted(top, key=lambda item: item.menu_position))


MENU: tuple[Page | MenuGroup, ...] = _build_menu(PAGES)
templates.env.globals["menu"] = MENU


def _make_page_view(template: str, page_id: str):
    def _view(request: Request):
        return templates.TemplateResponse(request, template, {"page": page_id})

    return _view


for _page in PAGES:
    app.add_api_route(
        _page.path,
        _make_page_view(_page.template, _page.page_id),
        methods=["GET"],
        include_in_schema=False,
    )


# ── Redirects das URLs antigas do Streamlit (spec 015) ───────────────────────
# O Streamlit derivava estes paths dos nomes de arquivo em `streamlit/pages/`
# (capitalizados, `_` como separador). Nenhum link do site atual aponta para
# eles — só chegam por bookmark ou histórico de quem usava o dashboard antigo.
# Mesma disciplina de "estrutura central" do PAGES acima: o mapa é a fonte
# única e as rotas saem de um loop, não de 7 blocos repetidos.
LEGACY_STREAMLIT_REDIRECTS: dict[str, str] = {
    "/Temperatura": "/temperatura",
    "/Precipitacao": "/precipitacao",
    "/Alertas": "/alertas",
    "/Cidades": "/cidades",
    "/Comparativo": "/comparativo",
    "/Relatorio_por_Cidade": "/relatorio-cidade",
    "/Horario": "/horario",
}


def _make_legacy_redirect(target: str):
    # 308 (Permanent Redirect): preserva o método HTTP e sinaliza permanência,
    # o comportamento correto para links e bookmarks antigos. A query string do
    # request original é reanexada ao path novo, para não perder parâmetros
    # como ?cidades=X&inicio=Y.
    def _redirect(request: Request) -> RedirectResponse:
        location = f"{target}?{request.url.query}" if request.url.query else target
        return RedirectResponse(location, status_code=308)

    return _redirect


for _old_path, _new_path in LEGACY_STREAMLIT_REDIRECTS.items():
    app.add_api_route(
        _old_path,
        _make_legacy_redirect(_new_path),
        methods=["GET"],
        include_in_schema=False,
    )


app.include_router(temperatura.router, prefix="/api/v1")
app.include_router(precipitacao.router, prefix="/api/v1")
app.include_router(alertas.router, prefix="/api/v1")
app.include_router(horario.router, prefix="/api/v1")
app.include_router(cidades.router, prefix="/api/v1")
app.include_router(comparativo.router, prefix="/api/v1")
app.include_router(relatorio_cidade.router, prefix="/api/v1")
app.include_router(ref.router, prefix="/api/v1")


@app.get("/health", include_in_schema=False)
def health() -> JSONResponse:
    """Liveness. Só confirma que a app subiu (o que já implica manifest do
    Vite válido, via `_load_main_entry`).

    Deliberadamente NÃO testa o BigQuery: a suíte de testes importa a app sem
    credencial (spec 006) e um probe que dependesse do BigQuery daria 503 no
    CI. Uma checagem de readiness contra o BigQuery, se necessária, entra
    como endpoint separado."""
    return JSONResponse(status_code=200, content={"status": "ok"})
