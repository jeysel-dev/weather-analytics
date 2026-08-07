import plotly.express as px
import streamlit as st
from utils.bigquery import query, tbl, max_date
from utils.labels import CLASS_LABELS_PT

_meso_df = query(f"""
SELECT DISTINCT mesoregion
FROM {tbl('locations', seeds=True)}
WHERE mesoregion IS NOT NULL
ORDER BY mesoregion
""")
_meso_list = _meso_df["mesoregion"].tolist() if not _meso_df.empty else []

with st.sidebar:
    st.header("Filtros")
    meso = st.selectbox("Mesorregião", ["Todas"] + _meso_list)
    days = st.slider("Período (dias)", 7, 90, 30, step=7)

meso_clause = f"AND mesoregion = '{meso}'" if meso != "Todas" else ""
_max_daily = max_date("mart_climate__daily_facts")

CLASS_COLORS = {
    "dry":      "#78909C",
    "light":    "#4FC3F7",
    "moderate": "#0288D1",
    "heavy":    "#1565C0",
    "extreme":  "#4A148C",
}
st.title("🌧️ Precipitação")

col1, col2 = st.columns([3, 1])

# ── Top 20 municípios mais chuvosos ───────────────────────────────────────────
with col1:
    limit = 20 if meso == "Todas" else 300
    label = f"Top 20 — últimos {days} dias" if meso == "Todas" else f"{meso} — últimos {days} dias"
    st.subheader(f"Maior precipitação acumulada — {label}")
    top = query(f"""
    SELECT city_name, mesoregion,
           ROUND(SUM(precipitation_mm), 1)                           AS total_mm,
           COUNT(CASE WHEN precipitation_mm > 0 THEN 1 END)          AS dias_chuva
    FROM {tbl('mart_climate__daily_facts')}
    WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
      {meso_clause}
    GROUP BY city_name, mesoregion
    ORDER BY total_mm DESC
    LIMIT {limit}
    """)
    if not top.empty:
        bar_height = max(520, len(top) * 22)
        fig = px.bar(
            top, x="total_mm", y="city_name", orientation="h",
            color="mesoregion",
            labels={"total_mm": "Acumulado (mm)", "city_name": "", "mesoregion": "Mesorregião"},
            hover_data={"dias_chuva": True},
            height=bar_height,
        )
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Distribuição por intensidade ──────────────────────────────────────────────
with col2:
    st.subheader("Intensidade")
    dist = query(f"""
    SELECT precipitation_class, COUNT(*) AS qtd
    FROM {tbl('mart_climate__daily_facts')}
    WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
      {meso_clause}
    GROUP BY precipitation_class
    ORDER BY qtd DESC
    """)
    if not dist.empty:
        dist["classe"] = dist["precipitation_class"].map(CLASS_LABELS_PT)
        fig = px.pie(
            dist, names="classe", values="qtd",
            color="classe",
            color_discrete_map={CLASS_LABELS_PT[k]: v for k, v in CLASS_COLORS.items()},
            labels={"classe": "Classe", "qtd": "Dias"},
            height=300,
        )
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=20), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Heatmap diário por mesorregião ────────────────────────────────────────────
st.subheader(f"Precipitação média diária por mesorregião — últimos {days} dias")
heat = query(f"""
SELECT date, mesoregion,
       ROUND(AVG(precipitation_mm), 1) AS avg_precip
FROM {tbl('mart_climate__daily_facts')}
WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
GROUP BY date, mesoregion
ORDER BY date
""")

if not heat.empty:
    pivot = heat.pivot_table(index="mesoregion", columns="date", values="avg_precip", aggfunc="mean").fillna(0)
    fig = px.imshow(
        pivot,
        color_continuous_scale="Blues",
        labels=dict(color="Precip Média (mm)"),
        aspect="auto",
        height=260,
    )
    fig.update_layout(
        xaxis=dict(title=None, tickformat="%d/%m"),
        yaxis_title=None,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)
