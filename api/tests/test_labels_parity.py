"""Paridade entre `api/app/utils/labels.py` e `web/src/labels.ts` (spec 014).

A spec 014 aponta a divergência entre os dois espelhos como risco real
(Casos de Borda) e recomenda um teste que compare os pares chave -> valor.
Aqui: sem BigQuery, sem parser de TS — leitura estática do arquivo `.ts`
por regex e comparação dos três dicionários de tradução.

Cor/ícone (`CLASS_COLORS`, `SEV_COLORS`, `SEV_ICON`) são só do frontend
(spec 014, Design) e de propósito NÃO têm contrapartida em Python — não
entram nesta comparação.
"""

import re
from pathlib import Path

import pytest

from app.utils.labels import ALERT_TYPE_PT, CLASS_LABELS_PT, SEVERITY_PT

_LABELS_TS = Path(__file__).resolve().parents[2] / "web" / "src" / "labels.ts"


def _parse_ts_record(source: str, const_name: str) -> dict[str, str]:
    """Extrai `export const <const_name> ... = { ... };` e devolve os pares
    `chave: "valor"` como dict. Aceita chaves com ou sem aspas."""
    block = re.search(
        rf"export const {re.escape(const_name)}\b[^=]*=\s*\{{(.*?)\}};",
        source,
        re.DOTALL,
    )
    if block is None:
        raise AssertionError(f"{const_name} não encontrado em {_LABELS_TS}")
    pairs = re.findall(r'["\']?([A-Za-z_][A-Za-z0-9_]*)["\']?\s*:\s*"([^"]*)"', block.group(1))
    return dict(pairs)


@pytest.fixture(scope="module")
def ts_source() -> str:
    return _LABELS_TS.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("const_name", "py_dict"),
    [
        ("ALERT_TYPE_PT", ALERT_TYPE_PT),
        ("SEVERITY_PT", SEVERITY_PT),
        ("CLASS_LABELS_PT", CLASS_LABELS_PT),
    ],
)
def test_translation_dicts_match(ts_source: str, const_name: str, py_dict: dict[str, str]) -> None:
    assert _parse_ts_record(ts_source, const_name) == py_dict
