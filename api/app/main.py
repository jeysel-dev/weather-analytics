import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
STATIC_MAIN_JS = f"/static/{_main_entry['file']}"
STATIC_MAIN_CSS = [f"/static/{css}" for css in _main_entry.get("css", [])]


app = FastAPI(
    title="Weather Analytics — API",
    description="Camada de serving do dashboard: páginas Jinja2 + endpoints JSON (spec 006).",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["main_js"] = STATIC_MAIN_JS
templates.env.globals["main_css"] = STATIC_MAIN_CSS


@app.get("/health", include_in_schema=False)
def health() -> JSONResponse:
    """Liveness/readiness. A checagem de BigQuery entra junto com a primeira
    página de dado migrada (spec 010) — por enquanto só confirma que a app
    subiu (o que já implica manifest do Vite válido, via `_load_main_entry`)."""
    return JSONResponse(status_code=200, content={"status": "ok"})


# Nenhuma rota de página aqui ainda. A estrutura central (tupla → rotas +
# menu) e os routers /api/v1/* entram a partir da spec 010.
