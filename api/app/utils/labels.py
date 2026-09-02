"""Traduções canônicas de enum para PT-BR no backend (spec 014).

Espelho fiel de `streamlit/utils/labels.py` (fonte canônica histórica) e de
`web/src/labels.ts` (passo 6 da spec 014): os três arquivos DEVEM ter os
mesmos pares chave -> valor. Só rótulo (tradução) mora aqui — cor e ícone
são apresentação e ficam apenas em `web/src/labels.ts`, nunca no JSON dos
endpoints (spec 014, Design).

Usado onde a tradução precisa acontecer no servidor (ex.: a tabela de
alertas recentes da futura página Alertas, spec 009, que devolve o rótulo
já pronto). Onde um valor de enum não está no dicionário, o consumidor
cai no valor cru (paridade com o `.map(...).fillna(<cru>)` do Streamlit).

`api/tests/test_labels_parity.py` compara estas chaves com `web/src/labels.ts`.
"""

ALERT_TYPE_PT = {
    "cold_anomaly":   "Anomalia de Frio",
    "precip_anomaly": "Anomalia de Precipitação",
    "heat_anomaly":   "Anomalia de Calor",
    "heavy_rain":     "Chuva Forte",
}

SEVERITY_PT = {
    "critical": "Crítica",
    "high":     "Alta",
    "medium":   "Média",
    "low":      "Baixa",
}

CLASS_LABELS_PT = {
    "dry":      "Seco",
    "light":    "Leve",
    "moderate": "Moderado",
    "heavy":    "Forte",
    "extreme":  "Extremo",
}
