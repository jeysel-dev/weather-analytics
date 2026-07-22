import pandas as pd
import plotly.express as px
import streamlit as st
from utils.bigquery import query, tbl, max_date

st.set_page_config(page_title="Alertas | Weather SC", page_icon="🚨", layout="wide")

SEV_COLORS = {
    "critical": "#D32F2F",
    "high":     "#F57C00",
    "medium":   "#FBC02D",
    "low":      "#388E3C",
}
SEV_ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}

_meso_df = query(f"""
SELECT DISTINCT mesoregion
FROM {tbl('locations', seeds=True)}
WHERE mesoregion IS NOT NULL
ORDER BY mesoregion
""")
_meso_list = _meso_df["mesoregion"].tolist() if not _meso_df.empty else []

with st.sidebar:
    st.header("Filtros")
    days = st.slider("Período (dias)", 7, 60, 30, step=7)
    meso = st.selectbox("Mesorregião", ["Todas"] + _meso_list)
    severity = st.selectbox("Severidade", ["Todas", "critical", "high", "medium", "low"])

meso_clause = f"AND mesoregion = '{meso}'" if meso != "Todas" else ""
sev_clause  = f"AND severity = '{severity}'" if severity != "Todas" else ""
_max_alerts = max_date("mart_climate__alerts")
base_where  = f"""
  date >= DATE_SUB(DATE '{_max_alerts}', INTERVAL {days} DAY)
  {meso_clause}
  {sev_clause}
"""

st.title("🚨 Alertas Climáticos")
st.caption(f"Dados disponíveis até {_max_alerts}")

# ── KPIs ──────────────────────────────────────────────────────────────────────
kpi = query(f"""
SELECT
  COUNT(*)                           AS total,
  COUNTIF(severity = 'critical')     AS critical,
  COUNTIF(severity = 'high')         AS high,
  COUNTIF(severity = 'medium')       AS medium,
  COUNTIF(severity = 'low')          AS low
FROM {tbl('mart_climate__alerts')}
WHERE {base_where}
""")

if not kpi.empty:
    r = kpi.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", int(r["total"] or 0))
    c2.metric("🔴 Críticos", int(r["critical"] or 0))
    c3.metric("🟠 Altos",    int(r["high"]     or 0))
    c4.metric("🟡 Médios",   int(r["medium"]   or 0))
    c5.metric("🟢 Baixos",   int(r["low"]      or 0))

st.divider()

col1, col2 = st.columns(2)

# ── Alertas por tipo ──────────────────────────────────────────────────────────
with col1:
    st.subheader("Por tipo de alerta")
    by_type = query(f"""
    SELECT alert_type, severity, COUNT(*) AS qtd
    FROM {tbl('mart_climate__alerts')}
    WHERE {base_where}
    GROUP BY alert_type, severity
    ORDER BY qtd DESC
    """)
    if not by_type.empty:
        fig = px.bar(
            by_type, x="qtd", y="alert_type", color="severity", orientation="h",
            color_discrete_map=SEV_COLORS,
            barmode="stack",
            labels={"qtd": "Ocorrências", "alert_type": "", "severity": "Severidade"},
            height=320,
        )
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Municípios mais afetados ──────────────────────────────────────────────────
with col2:
    st.subheader("Municípios mais afetados")
    city_limit = 15 if meso == "Todas" else 300
    top_cities = query(f"""
    SELECT city_name, mesoregion, COUNT(*) AS alertas
    FROM {tbl('mart_climate__alerts')}
    WHERE {base_where}
    GROUP BY city_name, mesoregion
    ORDER BY alertas DESC
    LIMIT {city_limit}
    """)
    if not top_cities.empty:
        bar_height = max(320, len(top_cities) * 22)
        fig = px.bar(
            top_cities, x="alertas", y="city_name", orientation="h",
            color="mesoregion",
            labels={"alertas": "Nº de Alertas", "city_name": "", "mesoregion": "Mesorregião"},
            height=bar_height,
        )
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Tabela de alertas recentes ────────────────────────────────────────────────
st.subheader(f"Alertas recentes — últimos {days} dias")
recent = query(f"""
SELECT
  date, city_name, mesoregion, alert_type, severity,
  ROUND(temp_max_c, 1)         AS temp_max,
  ROUND(temp_anomaly_c, 1)     AS anomalia,
  ROUND(precipitation_mm, 1)   AS precip,
  ROUND(wind_speed_max_kmh, 1) AS vento_max,
  uv_index_max
FROM {tbl('mart_climate__alerts')}
WHERE {base_where}
ORDER BY date DESC, severity ASC
LIMIT 200
""")

if recent.empty:
    st.info("Nenhum alerta encontrado no período e filtros selecionados.")
else:
    recent["sev_label"] = recent["severity"].map(lambda s: f"{SEV_ICON.get(s,'')} {s}")
    st.dataframe(
        recent[["date","city_name","mesoregion","alert_type","sev_label",
                "temp_max","anomalia","precip","vento_max","uv_index_max"]],
        column_config={
            "date":        "Data",
            "city_name":   "Município",
            "mesoregion":  "Mesorregião",
            "alert_type":  "Tipo",
            "sev_label":   "Severidade",
            "temp_max":    st.column_config.NumberColumn("Temp Máx (°C)", format="%.1f"),
            "anomalia":    st.column_config.NumberColumn("Anomalia (°C)", format="%.1f"),
            "precip":      st.column_config.NumberColumn("Precip (mm)",   format="%.1f"),
            "vento_max":   st.column_config.NumberColumn("Vento (km/h)",  format="%.1f"),
            "uv_index_max":st.column_config.NumberColumn("UV Máx",        format="%.0f"),
        },
        use_container_width=True,
        hide_index=True,
    )
