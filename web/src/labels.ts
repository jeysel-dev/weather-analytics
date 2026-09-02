// Rótulos e cores compartilhados do frontend (spec 014).
//
// Fonte única dos dicionários que hoje estão duplicados como constantes
// locais nas páginas Streamlit (2_Precipitacao.py, 3_Alertas.py,
// 5_Cidades.py). Nenhuma página migrada deve redefinir esses dicionários
// localmente — importar daqui.
//
// Divisão (spec 014, Design):
//   - Tradução (*_PT): espelho fiel de `api/app/utils/labels.py` e de
//     `streamlit/utils/labels.py`. Os três arquivos DEVEM ter os mesmos
//     pares chave -> valor (test: api/tests/test_labels_parity.py).
//   - Apresentação (CLASS_COLORS, SEV_COLORS, SEV_ICON): cor/ícone só
//     existem aqui, NUNCA no JSON dos endpoints `/api/v1/*`.
//
// Onde um valor de enum não está no dicionário, a apresentação cai no
// valor cru (paridade com o `.map(...).fillna(<cru>)` do Streamlit).

// ── Tradução ────────────────────────────────────────────────────────────
export const ALERT_TYPE_PT: Record<string, string> = {
  cold_anomaly: "Anomalia de Frio",
  precip_anomaly: "Anomalia de Precipitação",
  heat_anomaly: "Anomalia de Calor",
  heavy_rain: "Chuva Forte",
};

export const SEVERITY_PT: Record<string, string> = {
  critical: "Crítica",
  high: "Alta",
  medium: "Média",
  low: "Baixa",
};

export const CLASS_LABELS_PT: Record<string, string> = {
  dry: "Seco",
  light: "Leve",
  moderate: "Moderado",
  heavy: "Forte",
  extreme: "Extremo",
};

// ── Apresentação (cor / ícone) ──────────────────────────────────────────
export const CLASS_COLORS: Record<string, string> = {
  dry: "#78909C",
  light: "#4FC3F7",
  moderate: "#0288D1",
  heavy: "#1565C0",
  extreme: "#4A148C",
};

export const SEV_COLORS: Record<string, string> = {
  critical: "#D32F2F",
  high: "#F57C00",
  medium: "#FBC02D",
  low: "#388E3C",
};

export const SEV_ICON: Record<string, string> = {
  critical: "🔴",
  high: "🟠",
  medium: "🟡",
  low: "🟢",
};
