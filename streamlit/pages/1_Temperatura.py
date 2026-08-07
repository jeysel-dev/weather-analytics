import pandas as pd
import plotly.express as px
import streamlit as st
from utils.bigquery import query, tbl, max_date

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

st.title("🌡️ Temperatura")
st.caption(f"Dados disponíveis até {_max_daily}")

# ── Rankings ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔥 Municípios mais quentes — 7 dias")
    hot = query(f"""
    SELECT city_name, mesoregion,
           ROUND(AVG(temp_max_c), 1) AS media_max
    FROM {tbl('mart_climate__daily_facts')}
    WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL 7 DAY)
      {meso_clause}
    GROUP BY city_name, mesoregion
    ORDER BY media_max DESC
    LIMIT 10
    """)
    if not hot.empty:
        fig = px.bar(
            hot, x="media_max", y="city_name", orientation="h",
            color="media_max", color_continuous_scale="Reds",
            text="media_max",
            labels={"media_max": "Temp Máx Média (°C)", "city_name": ""},
            height=340,
        )
        fig.update_traces(texttemplate="%{text:.1f}°C", textposition="outside", cliponaxis=False)
        fig.update_layout(
            showlegend=False,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=60, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("❄️ Municípios mais frios — 7 dias")
    cold = query(f"""
    SELECT city_name, mesoregion,
           ROUND(AVG(temp_min_c), 1) AS media_min
    FROM {tbl('mart_climate__daily_facts')}
    WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL 7 DAY)
      {meso_clause}
    GROUP BY city_name, mesoregion
    ORDER BY media_min ASC
    LIMIT 10
    """)
    if not cold.empty:
        fig = px.bar(
            cold, x="media_min", y="city_name", orientation="h",
            color="media_min", color_continuous_scale="Blues_r",
            text="media_min",
            labels={"media_min": "Temp Mín Média (°C)", "city_name": ""},
            height=340,
        )
        fig.update_traces(texttemplate="%{text:.1f}°C", textposition="outside", cliponaxis=False)
        fig.update_layout(
            showlegend=False,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=60, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Tendência por mesorregião ─────────────────────────────────────────────────
st.subheader(f"Temperatura média por mesorregião — últimos {days} dias")
meso_trend = query(f"""
SELECT date, mesoregion,
       ROUND(AVG(temp_avg_c), 1) AS temp_avg
FROM {tbl('mart_climate__daily_facts')}
WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
  {meso_clause}
GROUP BY date, mesoregion
ORDER BY date
""")

if not meso_trend.empty:
    fig = px.line(
        meso_trend, x="date", y="temp_avg", color="mesoregion",
        labels={"date": "", "temp_avg": "Temperatura Média (°C)", "mesoregion": "Mesorregião"},
        height=360,
    )
    fig.update_layout(
        xaxis=dict(tickformat="%d/%m"),
        legend=dict(orientation="h", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Heatmap de anomalia ───────────────────────────────────────────────────────
st.subheader(f"Anomalia térmica por mesorregião — últimos {days} dias")
anomaly = query(f"""
SELECT date, mesoregion,
       ROUND(AVG(temp_anomaly_c), 2) AS anomaly
FROM {tbl('mart_climate__daily_facts')}
WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
GROUP BY date, mesoregion
ORDER BY date
""")

if not anomaly.empty:
    pivot = anomaly.pivot_table(index="mesoregion", columns="date", values="anomaly", aggfunc="mean")
    fig = px.imshow(
        pivot,
        color_continuous_scale="RdBu_r",
        color_continuous_midpoint=0,
        labels=dict(color="Anomalia (°C)"),
        aspect="auto",
        height=260,
    )
    fig.update_layout(
        xaxis=dict(title=None, tickformat="%d/%m"),
        yaxis_title=None,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Positivo (vermelho) = mais quente que a média 30d · Negativo (azul) = mais frio")
