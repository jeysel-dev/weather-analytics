import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from utils.bigquery import query, tbl, max_date, format_temp

load_dotenv()

st.set_page_config(
    page_title="Weather Analytics SC",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def home():
    if not os.environ.get("GCP_PROJECT_ID"):
        st.error(
            "**Configuração incompleta:** `GCP_PROJECT_ID` não definido.  \n"
            "Crie o arquivo `.env` a partir de `.env.example` e reinicie o serviço."
        )
        st.stop()

    # ── Mesorregiões disponíveis (lidas do seed — fonte canônica dos nomes) ────
    _meso_df = query(f"""
    SELECT DISTINCT mesoregion
    FROM {tbl('locations', seeds=True)}
    WHERE mesoregion IS NOT NULL
    ORDER BY mesoregion
    """)
    _meso_list = _meso_df["mesoregion"].tolist() if not _meso_df.empty else []

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Filtros")
        meso = st.selectbox("Mesorregião", ["Todas"] + _meso_list)
        days = st.slider("Período (dias)", 7, 90, 30, step=7)

    meso_clause = f"AND mesoregion = '{meso}'" if meso != "Todas" else ""

    _max_daily = max_date("mart_climate__daily_facts")
    _max_alerts = max_date("mart_climate__alerts")

    # ── KPIs (últimos 7 dias com dado disponível) ───────────────────────────
    kpi_df = query(f"""
    SELECT
      ROUND(AVG(temp_max_c), 1)  AS avg_max,
      ROUND(AVG(temp_min_c), 1)  AS avg_min,
      ROUND(AVG(temp_avg_c), 1)  AS avg_temp,
      ROUND(
        SUM(precipitation_mm) / NULLIF(COUNT(DISTINCT location_id), 0), 1
      )                           AS avg_precip,
      ROUND(AVG(temp_anomaly_c), 2) AS avg_anomaly
    FROM {tbl('mart_climate__daily_facts')}
    WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL 7 DAY)
      {meso_clause}
    """)

    alerts_df = query(f"""
    SELECT COUNT(*) AS total
    FROM {tbl('mart_climate__alerts')}
    WHERE date >= DATE_SUB(DATE '{_max_alerts}', INTERVAL 7 DAY)
      {meso_clause}
    """)

    st.title("🌤️ Weather Analytics — Santa Catarina")
    st.caption(f"Últimos 7 dias (dados até {_max_daily}) · {meso if meso != 'Todas' else '295 municípios'}")

    if not kpi_df.empty:
        r = kpi_df.iloc[0]

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Temp Máx Média",   f"{format_temp(r['avg_max'])} °C")
        c2.metric("Temp Mín Média",   f"{format_temp(r['avg_min'])} °C")
        c3.metric("Temp Média",       f"{format_temp(r['avg_temp'])} °C")
        c4.metric("Precip. Média",    f"{format_temp(r['avg_precip'])} mm")
        delta = float(r["avg_anomaly"] or 0)
        c5.metric(
            "Anomalia Térmica",
            f"{delta:+.1f} °C",
            delta=f"{delta:+.1f} vs média 30d",
            delta_color="inverse",
        )

    st.divider()

    # ── Tendência de temperatura ─────────────────────────────────────────────
    trend = query(f"""
    SELECT
      date,
      ROUND(AVG(temp_max_c), 1) AS temp_max,
      ROUND(AVG(temp_min_c), 1) AS temp_min,
      ROUND(AVG(temp_avg_c), 1) AS temp_avg
    FROM {tbl('mart_climate__daily_facts')}
    WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
      {meso_clause}
    GROUP BY date
    ORDER BY date
    """)

    if not trend.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend["date"], y=trend["temp_max"],
            name="Máxima", line=dict(color="#EF5350", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=trend["date"], y=trend["temp_avg"],
            name="Média", line=dict(color="#FFA726", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=trend["date"], y=trend["temp_min"],
            name="Mínima", line=dict(color="#42A5F5", width=2),
            fill="tonexty", fillcolor="rgba(66,165,245,0.08)",
        ))
        fig.update_layout(
            title=f"Tendência de temperatura — últimos {days} dias",
            xaxis=dict(tickformat="%d/%m"),
            yaxis_title="°C",
            legend=dict(orientation="h", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=40, b=0),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Mapa de municípios ────────────────────────────────────────────────────
    mapa = query(f"""
    SELECT city_name, mesoregion, latitude, longitude,
           temp_max_c, precipitation_mm
    FROM {tbl('mart_climate__daily_facts')}
    WHERE mesoregion IS NOT NULL
      {meso_clause}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY location_id ORDER BY date DESC) = 1
    """)

    if mapa.empty:
        st.warning(f"Sem dados disponíveis para **{meso}**. Verifique se o pipeline já rodou para esta mesorregião.")
    else:
        mapa["_size"] = pd.to_numeric(mapa["precipitation_mm"], errors="coerce").fillna(0).clip(lower=1)

        if meso != "Todas":
            center_lat = mapa["latitude"].mean()
            center_lon = mapa["longitude"].mean()
            spread = max(
                mapa["latitude"].max() - mapa["latitude"].min(),
                mapa["longitude"].max() - mapa["longitude"].min(),
            )
            zoom = 8 if spread < 1 else 7.5 if spread < 1.5 else 7
        else:
            center_lat, center_lon, zoom = -27.2, -50.5, 5.5

        fig_m = px.scatter_mapbox(
            mapa,
            lat="latitude", lon="longitude",
            color="temp_max_c", size="_size", size_max=18,
            hover_name="city_name",
            hover_data={
                "mesoregion": True,
                "temp_max_c": ":.1f",
                "precipitation_mm": ":.1f",
                "latitude": False, "longitude": False, "_size": False,
            },
            color_continuous_scale="RdYlBu_r",
            range_color=[-5, 40],
            zoom=zoom,
            center={"lat": center_lat, "lon": center_lon},
            mapbox_style="carto-positron",
            labels={"temp_max_c": "Temp Máx (°C)", "precipitation_mm": "Precip (mm)"},
            height=540,
        )
        fig_m.update_layout(
            title="Temperatura Máxima por Município",
            margin=dict(l=0, r=0, t=40, b=0),
            coloraxis_colorbar=dict(title="°C", thickness=14),
        )
        st.plotly_chart(fig_m, use_container_width=True)


pg = st.navigation([
    st.Page(home, title="Weather Analytics", icon="🌤️", default=True),
    st.Page("pages/1_Temperatura.py", title="Temperatura", icon="🌡️"),
    st.Page("pages/2_Precipitacao.py", title="Precipitação", icon="🌧️"),
    st.Page("pages/3_Alertas.py", title="Alertas", icon="🚨"),
    st.Page("pages/4_Horario.py", title="Horário", icon="🕐"),
    st.Page("pages/5_Cidades.py", title="Cidades", icon="🏙️"),
    st.Page("pages/6_Comparativo.py", title="Comparativo", icon="🔍"),
])
pg.run()
