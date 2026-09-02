import json
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import horario

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


PAGES: tuple[Page, ...] = (
    Page(
        path="/horario",
        template="horario.html",
        page_id="horario",
        menu_label="Horário",
        menu_icon="🕐",
        # Posição 4 = mesma do Streamlit (streamlit/pages/4_Horario.py). As
        # posições 1–3 (Temperatura, Precipitação, Alertas) ainda não existem
        # aqui; o número já fica certo para quando entrarem.
        menu_position=4,
    ),
)

MENU: tuple[Page, ...] = tuple(sorted(PAGES, key=lambda p: p.menu_position))
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

app.include_router(horario.router, prefix="/api/v1")


@app.get("/health", include_in_schema=False)
def health() -> JSONResponse:
    """Liveness. Só confirma que a app subiu (o que já implica manifest do
    Vite válido, via `_load_main_entry`).

    Deliberadamente NÃO testa o BigQuery: a suíte de testes importa a app sem
    credencial (spec 006) e um probe que dependesse do BigQuery daria 503 no
    CI. Uma checagem de readiness contra o BigQuery, se necessária, entra
    como endpoint separado."""
    return JSONResponse(status_code=200, content={"status": "ok"})
