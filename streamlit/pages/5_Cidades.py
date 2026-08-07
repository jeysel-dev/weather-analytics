import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils.bigquery import query, tbl, max_date, format_temp
from utils.labels import ALERT_TYPE_PT, SEVERITY_PT, CLASS_LABELS_PT

st.title("🏙️ Perfil por Município")

CLASS_COLORS = {
    "dry":      "#78909C",
    "light":    "#4FC3F7",
    "moderate": "#0288D1",
    "heavy":    "#1565C0",
    "extreme":  "#4A148C",
}

# Lista de municípios com metadados — usa seeds.locations para garantir todos os 295 municípios
cities = query(f"""
SELECT city_name, mesoregion,
       ROUND(latitude, 4)  AS latitude,
       ROUND(longitude, 4) AS longitude,
       altitude_m
FROM {tbl('locations', seeds=True)}
WHERE city_name IS NOT NULL
ORDER BY city_name
""")

if cities.empty:
    st.error("Não foi possível carregar a lista de municípios. Verifique a conexão com o BigQuery.")
    st.stop()

with st.sidebar:
    st.header("Município")
    city = st.selectbox("Selecione", cities["city_name"].tolist())
    days = st.slider("Período (dias)", 30, 365, 90, step=30)

_max_daily = max_date("mart_climate__daily_facts")
_max_alerts = max_date("mart_climate__alerts")

info = cities[cities["city_name"] == city].iloc[0]
st.subheader(f"📍 {city}")
st.caption(
    f"Mesorregião: **{info['mesoregion']}** · "
    f"Altitude: {info['altitude_m']:.0f} m · "
    f"{abs(info['latitude']):.2f}°{'S' if info['latitude'] < 0 else 'N'}, "
    f"{abs(info['longitude']):.2f}°{'W' if info['longitude'] < 0 else 'E'}"
)

# ── Dados climáticos do município ─────────────────────────────────────────────
climate = query(f"""
SELECT
  date, temp_max_c, temp_min_c, temp_avg_c,
  temp_anomaly_c, precipitation_mm, precipitation_class,
  wind_speed_max_kmh, uv_index_max, uv_risk_level
FROM {tbl('mart_climate__daily_facts')}
WHERE city_name = '{city}'
  AND date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
ORDER BY date
""")

if climate.empty:
    st.warning(f"Sem dados para {city} no período de {days} dias.")
    st.stop()

# ── KPIs resumo ───────────────────────────────────────────────────────────────
agg = climate.agg({
    "temp_max_c":    "mean",
    "temp_min_c":    "mean",
    "precipitation_mm": "sum",
    "temp_anomaly_c": "mean",
}).round(1)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Temp Máx Média",  f"{format_temp(agg['temp_max_c'])} °C")
c2.metric("Temp Mín Média",  f"{format_temp(agg['temp_min_c'])} °C")
c3.metric("Precip. Acumulada", f"{format_temp(agg['precipitation_mm'])} mm")
delta = float(agg["temp_anomaly_c"] or 0)
c4.metric("Anomalia Média",  f"{delta:+.1f} °C", delta_color="inverse")

st.divider()

tab_temp, tab_precip, tab_vento, tab_alertas = st.tabs(
    ["🌡️ Temperatura", "🌧️ Precipitação", "💨 Vento & UV", "🚨 Alertas"]
)

# ── Temperatura ───────────────────────────────────────────────────────────────
with tab_temp:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=climate["date"], y=climate["temp_max_c"],
        name="Máxima", line=dict(color="#EF5350", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=climate["date"], y=climate["temp_avg_c"],
        name="Média", line=dict(color="#FFA726", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=climate["date"], y=climate["temp_min_c"],
        name="Mínima", line=dict(color="#42A5F5", width=2),
        fill="tonexty", fillcolor="rgba(66,165,245,0.08)",
    ))
    anomaly_vals = climate["temp_anomaly_c"].fillna(0)
    fig.add_trace(go.Bar(
        x=climate["date"],
        y=anomaly_vals,
        name="Anomalia",
        marker_color=["#D32F2F" if v > 0 else "#1565C0" for v in anomaly_vals],
        opacity=0.45,
        yaxis="y2",
    ))
    fig.update_layout(
        xaxis=dict(tickformat="%d/%m"),
        yaxis=dict(title="Temperatura (°C)"),
        yaxis2=dict(title="Anomalia (°C)", overlaying="y", side="right", zeroline=True),
        legend=dict(orientation="h", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Precipitação ──────────────────────────────────────────────────────────────
with tab_precip:
    climate["intensidade"] = climate["precipitation_class"].map(CLASS_LABELS_PT).fillna(climate["precipitation_class"])
    fig = px.bar(
        climate, x="date", y="precipitation_mm",
        color="intensidade",
        color_discrete_map={CLASS_LABELS_PT[k]: v for k, v in CLASS_COLORS.items()},
        labels={
            "precipitation_mm": "Precipitação (mm)",
            "date": "",
            "intensidade": "Intensidade",
        },
        height=360,
    )
    fig.update_layout(
        xaxis=dict(tickformat="%d/%m"),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    total_rain = climate["precipitation_mm"].sum()
    rain_days  = (climate["precipitation_mm"] > 0).sum()
    cc1, cc2 = st.columns(2)
    cc1.metric("Total acumulado", f"{total_rain:.1f} mm")
    cc2.metric("Dias com chuva",  f"{rain_days} de {len(climate)}")

# ── Vento & UV ────────────────────────────────────────────────────────────────
with tab_vento:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=climate["date"], y=climate["wind_speed_max_kmh"],
        name="Vento Máx (km/h)", marker_color="#66BB6A",
    ))
    fig.add_trace(go.Scatter(
        x=climate["date"], y=climate["uv_index_max"],
        name="Índice UV Máx",
        line=dict(color="#FF8F00", width=2),
        yaxis="y2",
    ))
    fig.update_layout(
        xaxis=dict(tickformat="%d/%m"),
        yaxis=dict(title="Vento Máx (km/h)"),
        yaxis2=dict(title="Índice UV", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.02),
        margin=dict(l=0, r=0, t=10, b=0),
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Alertas do município ───────────────────────────────────────────────────────
with tab_alertas:
    alerts = query(f"""
    SELECT
      date, alert_type, severity,
      ROUND(temp_max_c, 1)         AS temp_max,
      ROUND(temp_anomaly_c, 1)     AS anomalia,
      ROUND(precipitation_mm, 1)   AS precip,
      ROUND(wind_speed_max_kmh, 1) AS vento,
      uv_index_max
    FROM {tbl('mart_climate__alerts')}
    WHERE city_name = '{city}'
      AND date >= DATE_SUB(DATE '{_max_alerts}', INTERVAL {days} DAY)
    ORDER BY date DESC
    LIMIT 100
    """)

    if alerts.empty:
        st.success(f"Nenhum alerta registrado para {city} nos últimos {days} dias.")
    else:
        alerts["alert_type"] = alerts["alert_type"].map(ALERT_TYPE_PT).fillna(alerts["alert_type"])
        alerts["severity"] = alerts["severity"].map(SEVERITY_PT).fillna(alerts["severity"])
        st.dataframe(
            alerts,
            column_config={
                "date":      "Data",
                "alert_type":"Tipo de Alerta",
                "severity":  "Severidade",
                "temp_max":  st.column_config.NumberColumn("Temp Máx (°C)", format="%.1f"),
                "anomalia":  st.column_config.NumberColumn("Anomalia (°C)", format="%.1f"),
                "precip":    st.column_config.NumberColumn("Precip (mm)",   format="%.1f"),
                "vento":     st.column_config.NumberColumn("Vento (km/h)",  format="%.1f"),
                "uv_index_max": st.column_config.NumberColumn("UV Máx",     format="%.0f"),
            },
            use_container_width=True,
            hide_index=True,
        )
