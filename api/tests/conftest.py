import json
from pathlib import Path


def _ensure_vite_manifest_stub() -> None:
    """Garante que `api/app/static/.vite/manifest.json` exista antes de
    `app.main` ser importado (spec 006).

    `app/main.py` lê esse manifest em nível de módulo (`_load_main_entry()` —
    fail-fast intencional, não é pra ser enfraquecido) e monta
    `StaticFiles(directory=api/app/static)`. Em produção o arquivo vem do
    build real do Vite (`npm run build` em `web/`, copiado pelo Dockerfile),
    mas `api/app/static/` é gitignored — não existe num checkout limpo
    (ex.: runner de CI), então a importação falharia antes de chegar nos
    testes.

    `_load_main_entry()` só lê o JSON e monta duas strings (`main_js` /
    `main_css`) — nunca abre os arquivos JS/CSS referenciados. Um manifest
    forjado é suficiente.

    Se um manifest real já existir (ambiente local após `npm run build`),
    não sobrescreve — respeita o build real.
    """
    static_dir = Path(__file__).resolve().parent.parent / "app" / "static"
    manifest_path = static_dir / ".vite" / "manifest.json"
    if manifest_path.exists():
        return
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"src/main.ts": {"file": "assets/main-stub.js", "css": []}}),
        encoding="utf-8",
    )


_ensure_vite_manifest_stub()
