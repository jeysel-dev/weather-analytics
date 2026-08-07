import plotly.graph_objects as go
import streamlit as st
from utils.bigquery import query, tbl

st.title("🕐 Padrão Horário")

# Carrega lista de cidades com dados horários disponíveis
cities_df = query(f"""
SELECT DISTINCT city_name
FROM {tbl('mart_climate__hourly_facts')}
ORDER BY city_name
""")

with st.sidebar:
    st.header("Filtros")
    city_list = cities_df["city_name"].tolist() if not cities_df.empty else []
    city = st.selectbox("Município", city_list)
    days = st.slider("Período (dias)", 3, 30, 7, step=1)

if not city:
    st.info("Selecione um município na barra lateral.")
    st.stop()

max_date_df = query(f"""
SELECT MAX(date) AS max_date
FROM {tbl('mart_climate__hourly_facts')}
WHERE city_name = '{city}'
""")
max_date = max_date_df["max_date"].iloc[0] if not max_date_df.empty else None

if max_date is None:
    st.warning("Sem dados horários para este município.")
    st.stop()

st.subheader(f"{city} — últimos {days} dias")
st.caption(f"Dados disponíveis até {max_date}")

tab_serie, tab_vento, tab_padrao = st.tabs(["🌡️ Temperatura & Umidade", "💨 Vento & Chuva", "📊 Padrão 24h"])

# ── Série horária: temperatura + umidade ──────────────────────────────────────
with tab_serie:
    serie = query(f"""
    SELECT observed_at, temperature_c, relative_humidity_pct
    FROM {tbl('mart_climate__hourly_facts')}
    WHERE city_name = '{city}'
      AND date >= DATE_SUB(DATE '{max_date}', INTERVAL {days} DAY)
    ORDER BY observed_at
    """)

    if serie.empty:
        st.warning("Sem dados horários para este município no período.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=serie["observed_at"], y=serie["temperature_c"],
            name="Temperatura (°C)",
            line=dict(color="#EF5350", width=1.5),
        ))
        fig.add_trace(go.Scatter(
            x=serie["observed_at"], y=serie["relative_humidity_pct"],
            name="Umidade (%)",
            line=dict(color="#42A5F5", width=1.5, dash="dot"),
            yaxis="y2",
        ))
        fig.update_layout(
            xaxis=dict(tickformat="%d/%m"),
            yaxis=dict(title="Temperatura (°C)", titlefont=dict(color="#EF5350")),
            yaxis2=dict(
                title="Umidade (%)", titlefont=dict(color="#42A5F5"),
                overlaying="y", side="right", range=[0, 105],
            ),
            legend=dict(orientation="h", y=1.02),
            margin=dict(l=0, r=60, t=30, b=0),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Série horária: vento + precipitação ───────────────────────────────────────
with tab_vento:
    vento = query(f"""
    SELECT observed_at, wind_speed_kmh, precipitation_mm
    FROM {tbl('mart_climate__hourly_facts')}
    WHERE city_name = '{city}'
      AND date >= DATE_SUB(DATE '{max_date}', INTERVAL {days} DAY)
    ORDER BY observed_at
    """)

    if vento.empty:
        st.warning("Sem dados horários para este município no período.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=vento["observed_at"], y=vento["precipitation_mm"],
            name="Precip (mm)", marker_color="#0288D1",
        ))
        fig.add_trace(go.Scatter(
            x=vento["observed_at"], y=vento["wind_speed_kmh"],
            name="Vento (km/h)",
            line=dict(color="#66BB6A", width=1.5),
            yaxis="y2",
        ))
        fig.update_layout(
            xaxis=dict(tickformat="%d/%m"),
            yaxis=dict(title="Precipitação (mm)", titlefont=dict(color="#0288D1")),
            yaxis2=dict(
                title="Vento (km/h)", titlefont=dict(color="#66BB6A"),
                overlaying="y", side="right",
            ),
            legend=dict(orientation="h", y=1.02),
            margin=dict(l=0, r=60, t=30, b=0),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Padrão médio das 24 horas ─────────────────────────────────────────────────
with tab_padrao:
    avg_h = query(f"""
    SELECT
      hour,
      ROUND(AVG(temperature_c), 1)         AS avg_temp,
      ROUND(AVG(relative_humidity_pct), 1) AS avg_humidity,
      ROUND(AVG(wind_speed_kmh), 1)         AS avg_wind,
      ROUND(
        SUM(precipitation_mm) / NULLIF(COUNT(DISTINCT date), 0), 2
      )                                     AS avg_precip_dia
    FROM {tbl('mart_climate__hourly_facts')}
    WHERE city_name = '{city}'
      AND date >= DATE_SUB(DATE '{max_date}', INTERVAL {days} DAY)
    GROUP BY hour
    ORDER BY hour
    """)

    if avg_h.empty:
        st.warning("Sem dados suficientes para calcular o padrão horário.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=avg_h["hour"], y=avg_h["avg_temp"],
            name="Temperatura média (°C)",
            line=dict(color="#EF5350", width=2.5),
            mode="lines+markers",
        ))
        fig.add_trace(go.Scatter(
            x=avg_h["hour"], y=avg_h["avg_humidity"],
            name="Umidade média (%)",
            line=dict(color="#42A5F5", width=1.5, dash="dot"),
            yaxis="y2",
        ))
        fig.add_trace(go.Bar(
            x=avg_h["hour"], y=avg_h["avg_precip_dia"],
            name="Precip média (mm)",
            marker_color="#0288D1", opacity=0.55,
            yaxis="y3",
        ))
        fig.update_layout(
            title=f"Perfil médio das 24 horas — {city}",
            xaxis=dict(title="Hora do dia", tickmode="linear", tick0=0, dtick=2, domain=[0, 0.86]),
            yaxis=dict(title="Temperatura (°C)", titlefont=dict(color="#EF5350")),
            yaxis2=dict(
                title="Umidade (%)", titlefont=dict(color="#42A5F5"),
                overlaying="y", side="right", range=[0, 105],
            ),
            yaxis3=dict(
                title="Precip (mm)", titlefont=dict(color="#0288D1"),
                overlaying="y", side="right", anchor="free", position=1.0,
                showgrid=False,
            ),
            legend=dict(orientation="h", y=1.02),
            margin=dict(l=0, r=90, t=40, b=0),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Médias calculadas sobre {days} dias de dados horários.")
