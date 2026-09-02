from datetime import timedelta
from urllib.parse import quote, urlencode

import streamlit as st
from utils.bigquery import query, tbl, max_date

st.title("📋 Relatório do clima por cidade")

# ── Dados de referência ────────────────────────────────────────────────────────
_cities_df = query(f"""
SELECT city_name FROM {tbl('locations', seeds=True)} ORDER BY city_name
""")
_city_list = _cities_df["city_name"].tolist() if not _cities_df.empty else []

_max_daily = max_date("mart_climate__daily_facts")

# ── Defaults a partir da URL (primeiro uso de st.query_params no projeto) ──────
_qp_cidades = st.query_params.get("cidades")
_default_cities = (
    [c for c in _qp_cidades.split(",") if c in _city_list] if _qp_cidades else []
)

_qp_dias = st.query_params.get("dias")
try:
    _default_days = int(_qp_dias)
    if not 7 <= _default_days <= 180:
        _default_days = 30
except (TypeError, ValueError):
    _default_days = 30

# ── Filtros ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")
    selected_cities = st.multiselect("Cidades", _city_list, default=_default_cities)
    days = st.slider("Dias", 7, 180, _default_days, step=7)

if not selected_cities:
    st.info("Selecione ao menos uma cidade para gerar o relatório.")
    st.stop()

data_fim = _max_daily
data_inicio = data_fim - timedelta(days=days)

st.caption(
    f"Cidades: {', '.join(selected_cities)} | "
    f"Período: últimos {days} dias "
    f"({data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')})"
)

# ── Query ────────────────────────────────────────────────────────────────────
cities_sql = ", ".join(f"'{c}'" for c in selected_cities)

report_df = query(f"""
SELECT
  city_name,
  ROUND(MAX(temp_max_c), 1)         AS temp_maxima,
  ROUND(AVG(temp_max_c), 1)         AS temp_maxima_media,
  ROUND(MIN(temp_min_c), 1)         AS temp_minima,
  ROUND(AVG(temp_min_c), 1)         AS temp_minima_media,
  ROUND(SUM(precipitation_mm), 1)   AS precip_acumulada,
  ROUND(MAX(wind_speed_max_kmh), 1) AS vento_maximo
FROM {tbl('mart_climate__daily_facts')}
WHERE city_name IN ({cities_sql})
  AND date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
GROUP BY city_name
ORDER BY city_name
""")

if report_df.empty:
    st.warning("Sem dados para o período selecionado.")
else:
    st.dataframe(
        report_df,
        column_config={
            "city_name":         "Cidade",
            "temp_maxima":       st.column_config.NumberColumn("Temp. Máxima (°C)", format="%.1f"),
            "temp_maxima_media": st.column_config.NumberColumn("Temp. Máxima Média (°C)", format="%.1f"),
            "temp_minima":       st.column_config.NumberColumn("Temp. Mínima (°C)", format="%.1f"),
            "temp_minima_media": st.column_config.NumberColumn("Temp. Mínima Média (°C)", format="%.1f"),
            "precip_acumulada":  st.column_config.NumberColumn("Precip. Acumulada (mm)", format="%.1f"),
            "vento_maximo":      st.column_config.NumberColumn("Vento Máximo (km/h)", format="%.1f"),
        },
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Compartilhar ─────────────────────────────────────────────────────────
    share_params = urlencode({"cidades": ",".join(selected_cities), "dias": days})
    share_url = f"https://weather.jeysel.dev/Relatorio_Cidade?{share_params}"
    message = (
        f"Relatório de clima - {', '.join(selected_cities)} - "
        f"Período: últimos {days} dias "
        f"({data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}). "
        f"Veja o relatório completo: {share_url}"
    )
    wa_url = f"https://wa.me/?text={quote(message)}"
    st.link_button("Compartilhar", wa_url)
