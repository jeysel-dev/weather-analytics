// Página Horário (spec 010) — "Padrão Horário".
//
// 3 abas lendo /api/v1/horario/*:
//   - Temperatura & Umidade: 2 linhas, 2 eixos Y   (endpoint /serie)
//   - Vento & Chuva:         barra + linha, 2 eixos Y (mesmo /serie)
//   - Padrão 24h:            2 linhas + 1 barra, 3 eixos Y (endpoint /padrao-24h)
//
// SSR entrega só o esqueleto (horario.html); tudo aqui é client-side.

import * as echarts from "echarts";

import { fmt1, formatarDataISO } from "../format";

interface SerieRow {
  observed_at: string;
  temperature_c: number | null;
  relative_humidity_pct: number | null;
  wind_speed_kmh: number | null;
  precipitation_mm: number | null;
}

interface SerieResponse {
  max_date: string | null;
  rows: SerieRow[];
}

interface Padrao24hRow {
  hour: number;
  avg_temp: number | null;
  avg_humidity: number | null;
  avg_wind: number | null;
  avg_precip_dia: number | null;
}

interface Padrao24hResponse {
  rows: Padrao24hRow[];
}

const CHART_IDS = ["chart-serie", "chart-vento", "chart-padrao"] as const;
const resizeBound = new Set<string>();

function byId<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

function toggle(node: HTMLElement | null, visible: boolean): void {
  if (node !== null) node.hidden = !visible;
}

function setText(id: string, text: string): void {
  const node = byId(id);
  if (node !== null) {
    node.hidden = false;
    node.textContent = text;
  }
}

function chartFor(id: string): echarts.ECharts | null {
  const container = document.getElementById(id);
  if (container === null) return null;
  const chart = echarts.getInstanceByDom(container) ?? echarts.init(container);
  requestAnimationFrame(() => chart.resize());
  if (!resizeBound.has(id)) {
    resizeBound.add(id);
    window.addEventListener("resize", () => chart.resize());
  }
  return chart;
}

function clearChart(id: string): void {
  const container = document.getElementById(id);
  if (container === null) return;
  echarts.getInstanceByDom(container)?.clear();
}

const tooltipValor = (value: unknown): string =>
  fmt1(typeof value === "number" ? value : Number(value));

// ── Abas ────────────────────────────────────────────────────────────────────
function initTabs(): void {
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>(".tab-btn"));
  for (const btn of buttons) {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      if (target === undefined) return;
      for (const other of buttons) {
        other.setAttribute("aria-selected", String(other === btn));
      }
      for (const name of ["serie", "vento", "padrao"]) {
        toggle(byId(`tab-${name}`), name === target);
      }
      const container = document.getElementById(`chart-${target}`);
      if (container !== null) echarts.getInstanceByDom(container)?.resize();
    });
  }
}

// ── Municípios ──────────────────────────────────────────────────────────────
async function popularMunicipios(select: HTMLSelectElement): Promise<void> {
  const resposta = await fetch("/api/v1/horario/cidades");
  if (!resposta.ok) {
    const opt = document.createElement("option");
    opt.disabled = true;
    opt.textContent = `Erro ao carregar municípios (HTTP ${resposta.status})`;
    select.appendChild(opt);
    return;
  }
  const cidades = (await resposta.json()) as string[];
  for (const cidade of cidades) {
    const opt = document.createElement("option");
    opt.value = cidade;
    opt.textContent = cidade;
    select.appendChild(opt);
  }
}

// ── Gráficos ────────────────────────────────────────────────────────────────
function renderSerie(rows: SerieRow[]): void {
  const chart = chartFor("chart-serie");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-serie-vazia"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-serie-vazia"), false);
  chart.setOption(
    {
      tooltip: { trigger: "axis", valueFormatter: tooltipValor },
      legend: { top: 0 },
      grid: { left: 52, right: 60, top: 36, bottom: 32 },
      xAxis: { type: "time" },
      yAxis: [
        { type: "value", name: "°C" },
        { type: "value", name: "%", min: 0, max: 105, position: "right" },
      ],
      series: [
        {
          name: "Temperatura (°C)",
          type: "line",
          showSymbol: false,
          data: rows.map((r) => [r.observed_at, r.temperature_c]),
        },
        {
          name: "Umidade (%)",
          type: "line",
          showSymbol: false,
          yAxisIndex: 1,
          data: rows.map((r) => [r.observed_at, r.relative_humidity_pct]),
        },
      ],
    },
    true,
  );
}

function renderVento(rows: SerieRow[]): void {
  const chart = chartFor("chart-vento");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-vento-vazia"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-vento-vazia"), false);
  chart.setOption(
    {
      tooltip: { trigger: "axis", valueFormatter: tooltipValor },
      legend: { top: 0 },
      grid: { left: 52, right: 60, top: 36, bottom: 32 },
      xAxis: { type: "time" },
      yAxis: [
        { type: "value", name: "mm" },
        { type: "value", name: "km/h", position: "right" },
      ],
      series: [
        {
          name: "Precipitação (mm)",
          type: "bar",
          data: rows.map((r) => [r.observed_at, r.precipitation_mm]),
        },
        {
          name: "Vento (km/h)",
          type: "line",
          showSymbol: false,
          yAxisIndex: 1,
          data: rows.map((r) => [r.observed_at, r.wind_speed_kmh]),
        },
      ],
    },
    true,
  );
}

function renderPadrao(rows: Padrao24hRow[], days: number): void {
  const chart = chartFor("chart-padrao");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-padrao-vazio"), true);
    toggle(byId("padrao-caption"), false);
    chart.clear();
    return;
  }
  toggle(byId("msg-padrao-vazio"), false);
  chart.setOption(
    {
      // avg_wind vem no payload mas não é plotado — paridade com o Streamlit.
      tooltip: { trigger: "axis", valueFormatter: tooltipValor },
      legend: { top: 0 },
      grid: { left: 52, right: 96, top: 36, bottom: 32 },
      xAxis: { type: "category", name: "Hora", data: rows.map((r) => r.hour) },
      yAxis: [
        { type: "value", name: "°C" },
        { type: "value", name: "%", min: 0, max: 105, position: "right" },
        {
          type: "value",
          name: "mm/dia",
          position: "right",
          offset: 52,
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: "Temperatura média (°C)",
          type: "line",
          data: rows.map((r) => r.avg_temp),
        },
        {
          name: "Umidade média (%)",
          type: "line",
          yAxisIndex: 1,
          data: rows.map((r) => r.avg_humidity),
        },
        {
          name: "Precip média (mm/dia)",
          type: "bar",
          yAxisIndex: 2,
          data: rows.map((r) => r.avg_precip_dia),
        },
      ],
    },
    true,
  );
  setText("padrao-caption", `Médias calculadas sobre ${days} dias de dados horários.`);
}

// ── Orquestração ────────────────────────────────────────────────────────────
function clampDias(raw: string): number {
  const n = Number.parseInt(raw, 10);
  if (Number.isNaN(n)) return 7;
  return Math.min(30, Math.max(3, n));
}

function limparTudo(): void {
  for (const id of CHART_IDS) clearChart(id);
  for (const id of ["msg-serie-vazia", "msg-vento-vazia", "msg-padrao-vazio", "padrao-caption"]) {
    toggle(byId(id), false);
  }
}

async function carregar(city: string, days: number): Promise<void> {
  if (city === "") {
    toggle(byId("msg-sem-municipio"), true);
    toggle(byId("msg-sem-cidade"), false);
    toggle(byId("horario-subtitulo"), false);
    toggle(byId("horario-caption"), false);
    limparTudo();
    return;
  }
  toggle(byId("msg-sem-municipio"), false);

  const params = new URLSearchParams({ city, days: String(days) });
  const [serieResp, padraoResp] = await Promise.all([
    fetch(`/api/v1/horario/serie?${params.toString()}`),
    fetch(`/api/v1/horario/padrao-24h?${params.toString()}`),
  ]);

  if (!serieResp.ok || !padraoResp.ok) {
    const status = !serieResp.ok ? serieResp.status : padraoResp.status;
    toggle(byId("msg-sem-cidade"), false);
    setText("horario-subtitulo", `Erro ao carregar dados (HTTP ${status})`);
    toggle(byId("horario-caption"), false);
    limparTudo();
    return;
  }

  const serie = (await serieResp.json()) as SerieResponse;
  const padrao = (await padraoResp.json()) as Padrao24hResponse;

  if (serie.max_date === null) {
    toggle(byId("msg-sem-cidade"), true);
    toggle(byId("horario-subtitulo"), false);
    toggle(byId("horario-caption"), false);
    limparTudo();
    return;
  }
  toggle(byId("msg-sem-cidade"), false);

  setText("horario-subtitulo", `${city} — últimos ${days} dias`);
  setText("horario-caption", `Dados disponíveis até ${formatarDataISO(serie.max_date)}`);

  renderSerie(serie.rows);
  renderVento(serie.rows);
  renderPadrao(padrao.rows, days);
}

export function initHorario(): void {
  const select = byId<HTMLSelectElement>("filtro-municipio");
  const diasInput = byId<HTMLInputElement>("filtro-dias");
  if (select === null || diasInput === null) return;

  initTabs();
  void popularMunicipios(select);

  const rerender = (): void => {
    void carregar(select.value, clampDias(diasInput.value));
  };
  select.addEventListener("change", rerender);
  diasInput.addEventListener("change", rerender);
}
