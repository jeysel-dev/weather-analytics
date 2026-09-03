"""Cada rota de página renderiza (200 + HTML). Não bate no BigQuery — as
páginas são esqueleto Jinja e os dados chegam via fetch no cliente
(spec 006). Pega erro de template e item de menu quebrado no CI."""

import pytest
from starlette.testclient import TestClient

from app.main import MENU, PAGES, app


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.page_id)
def test_page_route_renders(page) -> None:
    with TestClient(app) as client:
        response = client.get(page.path)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # layout.html sempre renderiza a navbar
    assert 'class="site-nav"' in response.text


def test_relatorios_submenu_lists_all_report_pages() -> None:
    grupo = next((m for m in MENU if getattr(m, "label", None) == "Relatórios"), None)
    assert grupo is not None
    filhos = {child.page_id for child in grupo.children}
    esperado = {p.page_id for p in PAGES if p.menu_group == "Relatórios"}
    assert filhos == esperado
