import pytest
from starlette.testclient import TestClient

from app.main import LEGACY_STREAMLIT_REDIRECTS, app

# Espelha a tabela da spec 015; se o mapa mudar, o teste deve mudar junto.
EXPECTED = {
    "/Temperatura": "/temperatura",
    "/Precipitacao": "/precipitacao",
    "/Alertas": "/alertas",
    "/Cidades": "/cidades",
    "/Comparativo": "/comparativo",
    "/Relatorio_por_Cidade": "/relatorio-cidade",
    "/Horario": "/horario",
}


def test_redirect_map_matches_spec() -> None:
    assert LEGACY_STREAMLIT_REDIRECTS == EXPECTED


@pytest.mark.parametrize(("old", "new"), EXPECTED.items())
def test_legacy_url_redirects_308(old: str, new: str) -> None:
    with TestClient(app) as client:
        response = client.get(old, follow_redirects=False)
    assert response.status_code == 308
    assert response.headers["location"] == new


def test_redirect_preserves_query_string() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/Relatorio_por_Cidade?cidades=Florianopolis&inicio=2026-01-01",
            follow_redirects=False,
        )
    assert response.status_code == 308
    assert (
        response.headers["location"]
        == "/relatorio-cidade?cidades=Florianopolis&inicio=2026-01-01"
    )
