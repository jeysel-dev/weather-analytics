// Página Precipitação (spec 008) — migração de streamlit/pages/2_Precipitacao.py.
//
// 3 blocos lendo /api/v1/precipitacao/*:
//   - Ranking de chuvosos (bar horizontal, cor por macrorregião)  -> /ranking
//   - Distribuição por intensidade (pizza)                       -> /intensidade
//   - Heatmap de chuva média por macrorregião (ignora `meso`)     -> /heatmap-mesorregiao
//
// Rótulo/cor por precipitation_class vêm de web/src/labels.ts (spec 014);
// lista de macrorregiões e caption de data, da camada de referência.

import { fmt1, formatarDataISO } from "../format";
import { CLASS_COLORS, CLASS_LABELS_PT } from "../labels";
import { byId, chartFor, setText, toggle } from "../ui";

interface RankItem {
  city_name: string;
  mesoregion: string | null;
  total_mm: number | null;
  dias_chuva: number;
}
interface IntRow {
  precipitation_class: string | null;
  qtd: number;
}
interface HeatRow {
  date: string;
  mesoregion: string | null;
  avg_precip: number | null;
}

// Paleta categórica para as macrorregiões no ranking (o Streamlit deixa o
// Plotly escolher; aqui fixamos para o resultado ser estável entre runs).
const MESO_PALETTE = [
  "#5470c6",
  "#91cc75",
  "#fac858",
  "#ee6666",
  "#73c0de",
  "#3ba272",
  "#fc8452",
  "#9a60b4",
];

async function popularMesorregioes(select: HTMLSelectElement): Promise<void> {
  const resposta = await fetch("/api/v1/ref/mesorregioes");
  if (!resposta.ok) return;
  for (const meso of (await resposta.json()) as string[]) {
    const opt = document.createElement("option");
    opt.value = meso;
    opt.textContent = meso;
    select.appendChild(opt);
  }
}

async function carregarCaption(): Promise<void> {
  const resposta = await fetch("/api/v1/ref/daily-meta");
  if (!resposta.ok) return;
  const meta = (await resposta.json()) as { max_date: string | null };
  if (meta.max_date !== null) {
    setText("precip-caption", `Dados disponíveis até ${formatarDataISO(meta.max_date)}`);
  }
}

// ── Ranking de chuvosos ─────────────────────────────────────────────────────
function renderRanking(rows: RankItem[], meso: string, days: number): void {
  const legenda =
    meso === "Todas" ? `Top 20 — últimos ${days} dias` : `${meso} — últimos ${days} dias`;
  setText("ranking-titulo", `Maior precipitação acumulada — ${legenda}`);

  const chart = chartFor("chart-ranking");
  if (chart === null) return;
  const validos = rows.filter((r) => typeof r.total_mm === "number");
  if (validos.length === 0) {
    toggle(byId("msg-ranking-vazio"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-ranking-vazio"), false);

  const linhas = [...validos].reverse(); // maior no topo
  const cidades = linhas.map((r) => r.city_name);
  const mesos = [...new Set(linhas.map((r) => r.mesoregion ?? "—"))];
  const diasChuva = new Map(linhas.map((r) => [r.city_name, r.dias_chuva]));

  const container = byId<HTMLElement>("chart-ranking");
  if (container !== null) container.style.height = `${Math.max(520, linhas.length * 22)}px`;
  chart.resize();

  chart.setOption(
    {
      tooltip: {
        trigger: "item",
        formatter: (p: { name: string; seriesName: string; value: number | null }) =>
          `${p.name} — ${p.seriesName}<br/>Acumulado: ${fmt1(p.value)} mm<br/>Dias com chuva: ${
            diasChuva.get(p.name) ?? 0
          }`,
      },
      legend: { top: 0, type: "scroll" },
      grid: { left: 8, right: 24, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: "value", name: "Acumulado (mm)" },
      yAxis: { type: "category", data: cidades },
      series: mesos.map((m, i) => ({
        name: m,
        type: "bar",
        stack: "total",
        itemStyle: { color: MESO_PALETTE[i % MESO_PALETTE.length] },
        data: linhas.map((r) => ((r.mesoregion ?? "—") === m ? r.total_mm : null)),
      })),
    },
    true,
  );
}

// ── Distribuição por intensidade ────────────────────────────────────────────
function renderIntensidade(rows: IntRow[], days: number): void {
  setText("intensidade-titulo", `Distribuição por intensidade — últimos ${days} dias`);
  const chart = chartFor("chart-intensidade");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-intensidade-vazio"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-intensidade-vazio"), false);
  chart.setOption(
    {
      tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      legend: { orient: "vertical", right: "6%", top: "middle" },
      series: [
        {
          type: "pie",
          radius: ["38%", "72%"],
          center: ["38%", "50%"],
          avoidLabelOverlap: true,
          label: { formatter: "{b}\n{d}%" },
          data: rows.map((r) => {
            const cru = r.precipitation_class ?? "—";
            return {
              name: CLASS_LABELS_PT[cru] ?? cru,
              value: r.qtd,
              itemStyle: { color: CLASS_COLORS[cru] },
            };
          }),
        },
      ],
    },
    true,
  );
}

// ── Heatmap por macrorregião ─────────────────────────────────────────────────
function renderHeatmap(rows: HeatRow[], days: number): void {
  setText("heatmap-titulo", `Precipitação média diária por macrorregião — últimos ${days} dias`);
  const chart = chartFor("chart-heatmap");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-heatmap-vazio"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-heatmap-vazio"), false);
  const datas = [...new Set(rows.map((r) => r.date))].sort();
  const mesos = [...new Set(rows.map((r) => r.mesoregion ?? "—"))].sort();
  const data = rows.map((r) => [
    datas.indexOf(r.date),
    mesos.indexOf(r.mesoregion ?? "—"),
    r.avg_precip,
  ]);
  const max = Math.max(...rows.map((r) => r.avg_precip ?? 0), 1);
  chart.setOption(
    {
      tooltip: {
        position: "top",
        formatter: (p: { value: [number, number, number | null] }) =>
          `${mesos[p.value[1]]} · ${formatarDataISO(datas[p.value[0]])}: ${fmt1(p.value[2] ?? null)} mm`,
      },
      grid: { left: 140, right: 16, top: 8, bottom: 60, containLabel: true },
      xAxis: { type: "category", data: datas.map(formatarDataISO), splitArea: { show: true } },
      yAxis: { type: "category", data: mesos, splitArea: { show: true } },
      visualMap: {
        min: 0,
        max,
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        inRange: { color: ["#f7fbff", "#6baed6", "#08306b"] },
      },
      series: [{ type: "heatmap", data }],
    },
    true,
  );
}

// ── Orquestração ────────────────────────────────────────────────────────────
function clampDias(raw: string): number {
  const n = Number.parseInt(raw, 10);
  if (Number.isNaN(n)) return 7;
  return Math.min(90, Math.max(7, n));
}

async function carregar(meso: string, days: number): Promise<void> {
  const mesoQs = meso === "Todas" ? "" : `&meso=${encodeURIComponent(meso)}`;
  const [rankResp, intResp, heatResp] = await Promise.all([
    fetch(`/api/v1/precipitacao/ranking?days=${days}${mesoQs}`),
    fetch(`/api/v1/precipitacao/intensidade?days=${days}${mesoQs}`),
    fetch(`/api/v1/precipitacao/heatmap-mesorregiao?days=${days}`),
  ]);
  if (!rankResp.ok || !intResp.ok || !heatResp.ok) {
    const status = [rankResp, intResp, heatResp].find((r) => !r.ok)?.status ?? 0;
    setText("precip-erro", `Erro ao carregar dados (HTTP ${status})`);
    return;
  }
  toggle(byId("precip-erro"), false);
  renderRanking(((await rankResp.json()) as { rows: RankItem[] }).rows, meso, days);
  renderIntensidade(((await intResp.json()) as { rows: IntRow[] }).rows, days);
  renderHeatmap(((await heatResp.json()) as { rows: HeatRow[] }).rows, days);
}

export function initPrecipitacao(): void {
  const select = byId<HTMLSelectElement>("filtro-mesorregiao");
  const diasInput = byId<HTMLInputElement>("filtro-dias");
  if (select === null || diasInput === null) return;

  void carregarCaption();
  void popularMesorregioes(select).then(() => carregar(select.value, clampDias(diasInput.value)));

  const rerender = (): void => void carregar(select.value, clampDias(diasInput.value));
  select.addEventListener("change", rerender);
  diasInput.addEventListener("change", rerender);
}
