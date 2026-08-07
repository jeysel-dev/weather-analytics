import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from utils.bigquery import query, tbl, max_date

st.title("🔍 Análise Comparativa")

# ── Dados de referência ────────────────────────────────────────────────────────
_cities_df = query(f"""
SELECT city_name FROM {tbl('locations', seeds=True)} ORDER BY city_name
""")
_city_list = _cities_df["city_name"].tolist() if not _cities_df.empty else []

_meso_df = query(f"""
SELECT DISTINCT mesoregion
FROM {tbl('locations', seeds=True)}
WHERE mesoregion IS NOT NULL
ORDER BY mesoregion
""")
_meso_list = _meso_df["mesoregion"].tolist() if not _meso_df.empty else []

_max_daily = max_date("mart_climate__daily_facts")


def _idx(name: str) -> int:
    try:
        return _city_list.index(name)
    except ValueError:
        return 0


tab1, tab2, tab3 = st.tabs([
    "🌡️ Comparativo de Cidades",
    "🌧️ Quando Choveu",
    "📈 Dia vs Histórico",
])

# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Comparativo de Cidades
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Série temporal comparativa entre municípios")

    cf1, cf2, cf3, cf4, cf5 = st.columns([2, 2, 2, 2, 1])
    with cf1:
        city_a = st.selectbox("Cidade A", _city_list, index=_idx("Florianópolis"), key="ca")
    with cf2:
        city_b = st.selectbox("Cidade B", _city_list, index=_idx("Lages"), key="cb")
    with cf3:
        city_c = st.selectbox("Cidade C (opcional)", ["—"] + _city_list,
                              index=_idx("Chapecó") + 1, key="cc")
    with cf4:
        metric_label = st.selectbox(
            "Métrica",
            ["Temp Máxima", "Temp Mínima", "Temp Média", "Precipitação Diária"],
            key="cm",
        )
    with cf5:
        comp_days = st.slider("Dias", 7, 180, 30, step=7, key="cd")

    METRIC = {
        "Temp Máxima":        ("temp_max_c",       "Temperatura Máxima (°C)"),
        "Temp Mínima":        ("temp_min_c",        "Temperatura Mínima (°C)"),
        "Temp Média":         ("temp_avg_c",        "Temperatura Média (°C)"),
        "Precipitação Diária":("precipitation_mm",  "Precipitação (mm)"),
    }
    col, ylabel = METRIC[metric_label]

    cities_filter = [city_a, city_b]
    if city_c != "—":
        cities_filter.append(city_c)
    cities_sql = ", ".join(f"'{c}'" for c in cities_filter)

    comp_df = query(f"""
    SELECT date, city_name, ROUND({col}, 1) AS valor
    FROM {tbl('mart_climate__daily_facts')}
    WHERE city_name IN ({cities_sql})
      AND date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {comp_days} DAY)
    ORDER BY date, city_name
    """)

    if comp_df.empty:
        st.warning("Sem dados para o período selecionado.")
    else:
        fig = px.line(
            comp_df, x="date", y="valor", color="city_name",
            labels={"date": "", "valor": ylabel, "city_name": "Município"},
            height=420,
        )
        fig.update_layout(
            xaxis=dict(tickformat="%d/%m"),
            legend=dict(orientation="h", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        summary = (
            comp_df.groupby("city_name")["valor"]
            .agg(Mínimo="min", Máximo="max", Média="mean")
            .round(1)
        )
        summary.index.name = "Cidade"
        st.dataframe(summary, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Quando Choveu
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Intensidade de chuva diária por município")

    wf1, wf2 = st.columns([3, 1])
    with wf1:
        meso_w = st.selectbox("Mesorregião", _meso_list, key="wm")
    with wf2:
        wet_days = st.slider("Dias", 14, 60, 30, step=7, key="wd")

    rain_df = query(f"""
    SELECT date, city_name,
           ROUND(SUM(precipitation_mm), 1) AS precipitation_mm
    FROM {tbl('mart_climate__daily_facts')}
    WHERE mesoregion = '{meso_w}'
      AND date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {wet_days} DAY)
    GROUP BY date, city_name
    ORDER BY city_name, date
    """)

    if rain_df.empty:
        st.warning(f"Sem dados para **{meso_w}** no período selecionado.")
    else:
        pivot = rain_df.pivot_table(
            index="city_name", columns="date",
            values="precipitation_mm", aggfunc="sum",
        ).fillna(0)

        fig = px.imshow(
            pivot,
            color_continuous_scale=[
                [0.00, "#F5F5F5"],
                [0.01, "#B3E5FC"],
                [0.15, "#0288D1"],
                [0.40, "#1565C0"],
                [1.00, "#4A148C"],
            ],
            zmin=0,
            zmax=80,
            labels=dict(color="Precip (mm)", x="", y=""),
            aspect="auto",
            height=max(320, len(pivot) * 22),
        )
        fig.update_layout(
            xaxis=dict(tickformat="%d/%m"),
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_colorbar=dict(
                title="mm",
                thickness=14,
                tickvals=[0, 5, 20, 50, 80],
                ticktext=["Seco", "Leve", "Moderado", "Forte", "Extremo"],
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Branco = seco (0 mm) · Azul claro = leve (< 5 mm) · "
            "Azul = moderado (5–20 mm) · Azul escuro = forte (20–50 mm) · "
            "Roxo = extremo (> 50 mm)"
        )

# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 — Dia vs Histórico
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Perfil horário: dia selecionado vs média dos 30 dias anteriores")

    hf1, hf2 = st.columns([2, 2])
    with hf1:
        city_h = st.selectbox("Município", _city_list, index=_idx("Florianópolis"), key="hc")

    avail_dates = query(f"""
    SELECT DISTINCT date
    FROM {tbl('mart_climate__hourly_facts')}
    WHERE city_name = '{city_h}'
    ORDER BY date DESC
    LIMIT 60
    """)

    if avail_dates.empty:
        st.warning(f"Sem dados horários disponíveis para **{city_h}**.")
    else:
        date_list = avail_dates["date"].tolist()
        with hf2:
            selected_date = st.selectbox("Data de referência", date_list, key="hd")

        actual = query(f"""
        SELECT hour,
               ROUND(AVG(temperature_c), 1)         AS temp,
               ROUND(AVG(relative_humidity_pct), 1) AS humidity
        FROM {tbl('mart_climate__hourly_facts')}
        WHERE city_name = '{city_h}'
          AND date = DATE '{selected_date}'
        GROUP BY hour
        ORDER BY hour
        """)

        hist = query(f"""
        SELECT hour,
               ROUND(AVG(temperature_c), 1)         AS avg_temp,
               ROUND(AVG(relative_humidity_pct), 1) AS avg_humidity
        FROM {tbl('mart_climate__hourly_facts')}
        WHERE city_name = '{city_h}'
          AND date >= DATE_SUB(DATE '{selected_date}', INTERVAL 30 DAY)
          AND date <  DATE '{selected_date}'
        GROUP BY hour
        ORDER BY hour
        """)

        if actual.empty:
            st.warning(f"Sem dados horários para {city_h} em {selected_date}.")
        else:
            # ── Temperatura ────────────────────────────────────────────────
            fig_t = go.Figure()
            if not hist.empty:
                fig_t.add_trace(go.Scatter(
                    x=hist["hour"], y=hist["avg_temp"],
                    name="Média 30 dias anteriores",
                    line=dict(color="#90A4AE", width=2, dash="dot"),
                ))
            fig_t.add_trace(go.Scatter(
                x=actual["hour"], y=actual["temp"],
                name=str(selected_date),
                line=dict(color="#EF5350", width=3),
                mode="lines+markers",
                marker=dict(size=5),
            ))
            fig_t.update_layout(
                title=f"Temperatura — {city_h} · {selected_date} vs média 30d anteriores",
                xaxis=dict(title="Hora do dia", tickmode="linear", tick0=0, dtick=2),
                yaxis=dict(title="Temperatura (°C)"),
                legend=dict(orientation="h", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=40, b=0),
                height=380,
            )
            st.plotly_chart(fig_t, use_container_width=True)

            # ── Umidade ────────────────────────────────────────────────────
            fig_u = go.Figure()
            if not hist.empty:
                fig_u.add_trace(go.Scatter(
                    x=hist["hour"], y=hist["avg_humidity"],
                    name="Umidade média 30d",
                    line=dict(color="#90A4AE", width=2, dash="dot"),
                ))
            fig_u.add_trace(go.Scatter(
                x=actual["hour"], y=actual["humidity"],
                name=f"Umidade {selected_date}",
                line=dict(color="#42A5F5", width=3),
                mode="lines+markers",
                marker=dict(size=5),
            ))
            fig_u.update_layout(
                title=f"Umidade relativa — {city_h} · {selected_date} vs média 30d anteriores",
                xaxis=dict(title="Hora do dia", tickmode="linear", tick0=0, dtick=2),
                yaxis=dict(title="Umidade (%)", range=[0, 105]),
                legend=dict(orientation="h", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=40, b=0),
                height=340,
            )
            st.plotly_chart(fig_u, use_container_width=True)

            # ── Resumo das diferenças ──────────────────────────────────────
            if not hist.empty:
                merged = actual.merge(hist, on="hour", how="left")
                merged["diff_temp"] = (merged["temp"] - merged["avg_temp"]).round(1)
                avg_diff = merged["diff_temp"].mean()
                max_diff = merged["diff_temp"].max()
                min_diff = merged["diff_temp"].min()

                d1, d2, d3 = st.columns(3)
                d1.metric(
                    "Desvio médio do dia",
                    f"{avg_diff:+.1f} °C",
                    delta_color="inverse" if avg_diff < 0 else "normal",
                )
                d2.metric("Hora mais quente vs histórico", f"{max_diff:+.1f} °C")
                d3.metric("Hora mais fria vs histórico",   f"{min_diff:+.1f} °C")
