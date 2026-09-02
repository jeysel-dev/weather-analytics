// Página Temperatura (spec 007) — migração de streamlit/pages/1_Temperatura.py.
//
// 3 blocos lendo /api/v1/temperatura/*:
//   - Rankings quente/frio (janela FIXA 7d, sensível a `meso`)  -> /rankings
//   - Tendência média por mesorregião (janela `days`)           -> /tendencia-mesorregiao
//   - Heatmap de anomalia térmica (janela `days`, ignora `meso`) -> /anomalia
//
// Lista de mesorregiões e caption de data vêm da camada de referência
// (spec 014): /api/v1/ref/mesorregioes e /api/v1/ref/daily-meta.

import { fmt1, formatarDataISO } from "../format";
import { byId, chartFor, setText, toggle } from "../ui";

interface RankingItem {
  city_name: string;
  mesoregion: string | null;
  media: number | null;
}
interface RankingsResponse {
  quentes: RankingItem[];
  frios: RankingItem[];
}
interface TendenciaRow {
  date: string;
  mesoregion: string | null;
  temp_avg: number | null;
}
interface AnomaliaRow {
  date: string;
  mesoregion: string | null;
  anomaly: number | null;
}

const tempFormatter = (value: unknown): string =>
  `${fmt1(typeof value === "number" ? value : Number(value))}°C`;

// ── Filtros de referência ───────────────────────────────────────────────────
async function popularMesorregioes(select: HTMLSelectElement): Promise<void> {
  const resposta = await fetch("/api/v1/ref/mesorregioes");
  if (!resposta.ok) return;
  const mesos = (await resposta.json()) as string[];
  for (const meso of mesos) {
    const opt = document.createElement("option");
    opt.value = meso;
    opt.textContent = meso;
    select.appendChild(opt);
  }
}

async function carregarCaption(): Promise<void> {
  const resposta = await fetch("/api/v1/ref/daily-meta");
  if (!resposta.ok) {
    setText("temp-erro", `Erro ao carregar metadados (HTTP ${resposta.status})`);
    return;
  }
  const meta = (await resposta.json()) as { min_date: string | null; max_date: string | null };
  if (meta.max_date === null) {
    setText("temp-erro", "Sem dados climáticos disponíveis.");
    return;
  }
  setText("temp-caption", `Dados disponíveis até ${formatarDataISO(meta.max_date)}`);
}

// ── Rankings ────────────────────────────────────────────────────────────────
function renderRanking(
  id: string,
  emptyId: string,
  items: RankingItem[],
  eixoNome: string,
  cores: [string, string],
): void {
  const chart = chartFor(id);
  if (chart === null) return;
  const validos = items.filter((r) => typeof r.media === "number");
  if (validos.length === 0) {
    toggle(byId(emptyId), true);
    chart.clear();
    return;
  }
  toggle(byId(emptyId), false);
  // Streamlit usa yaxis autorange="reversed" (maior valor no topo). O eixo
  // de categoria do ECharts desenha de baixo p/ cima — invertendo a ordem
  // das linhas o 1º item (já ordenado pelo backend) fica no topo.
  const linhas = [...validos].reverse();
  const valores = linhas.map((r) => r.media as number);
  chart.setOption(
    {
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: tempFormatter },
      grid: { left: 8, right: 64, top: 8, bottom: 8, containLabel: true },
      visualMap: {
        show: false,
        min: Math.min(...valores),
        max: Math.max(...valores),
        inRange: { color: cores },
      },
      xAxis: { type: "value", name: eixoNome },
      yAxis: { type: "category", data: linhas.map((r) => r.city_name) },
      series: [
        {
          type: "bar",
          data: valores,
          label: {
            show: true,
            position: "right",
            formatter: (p: { value: unknown }) => tempFormatter(p.value),
          },
        },
      ],
    },
    true,
  );
}

// ── Tendência por mesorregião ───────────────────────────────────────────────
function renderTendencia(rows: TendenciaRow[]): void {
  const chart = chartFor("chart-tendencia");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-tendencia-vazio"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-tendencia-vazio"), false);
  const datas = [...new Set(rows.map((r) => r.date))].sort();
  const porMeso = new Map<string, Map<string, number | null>>();
  for (const r of rows) {
    const nome = r.mesoregion ?? "—";
    let m = porMeso.get(nome);
    if (m === undefined) {
      m = new Map();
      porMeso.set(nome, m);
    }
    m.set(r.date, r.temp_avg);
  }
  chart.setOption(
    {
      tooltip: { trigger: "axis", valueFormatter: tempFormatter },
      legend: { top: 0, type: "scroll" },
      grid: { left: 52, right: 16, top: 40, bottom: 32 },
      xAxis: { type: "category", data: datas.map(formatarDataISO) },
      yAxis: { type: "value", name: "°C" },
      series: [...porMeso].map(([nome, valores]) => ({
        name: nome,
        type: "line",
        showSymbol: false,
        data: datas.map((d) => valores.get(d) ?? null),
      })),
    },
    true,
  );
}

// ── Heatmap de anomalia ─────────────────────────────────────────────────────
function renderAnomalia(rows: AnomaliaRow[]): void {
  const chart = chartFor("chart-anomalia");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-anomalia-vazio"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-anomalia-vazio"), false);
  const datas = [...new Set(rows.map((r) => r.date))].sort();
  const mesos = [...new Set(rows.map((r) => r.mesoregion ?? "—"))].sort();
  const data = rows.map((r) => [
    datas.indexOf(r.date),
    mesos.indexOf(r.mesoregion ?? "—"),
    r.anomaly,
  ]);
  const maxAbs = Math.max(...rows.map((r) => Math.abs(r.anomaly ?? 0)), 0.1);
  chart.setOption(
    {
      tooltip: {
        position: "top",
        formatter: (p: { value: [number, number, number | null] }) =>
          `${mesos[p.value[1]]} · ${formatarDataISO(datas[p.value[0]])}: ${fmt1(p.value[2] ?? null)}°C`,
      },
      grid: { left: 140, right: 16, top: 8, bottom: 60, containLabel: true },
      xAxis: { type: "category", data: datas.map(formatarDataISO), splitArea: { show: true } },
      yAxis: { type: "category", data: mesos, splitArea: { show: true } },
      visualMap: {
        min: -maxAbs,
        max: maxAbs,
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        inRange: { color: ["#2166ac", "#4393c3", "#f7f7f7", "#d6604d", "#b2182b"] },
        text: ["+ quente", "+ frio"],
      },
      series: [{ type: "heatmap", data }],
    },
    true,
  );
}

// ── Orquestração ────────────────────────────────────────────────────────────
function clampDias(raw: string): number {
  const n = Number.parseInt(raw, 10);
  if (Number.isNaN(n)) return 30;
  return Math.min(90, Math.max(7, n));
}

async function carregarRankings(meso: string): Promise<void> {
  const qs = meso === "Todas" ? "" : `?meso=${encodeURIComponent(meso)}`;
  const resposta = await fetch(`/api/v1/temperatura/rankings${qs}`);
  if (!resposta.ok) {
    setText("temp-erro", `Erro ao carregar rankings (HTTP ${resposta.status})`);
    return;
  }
  toggle(byId("temp-erro"), false);
  const dados = (await resposta.json()) as RankingsResponse;
  renderRanking("chart-quentes", "msg-quentes-vazio", dados.quentes, "Temp Máx Média (°C)", [
    "#fee0d2",
    "#a50f15",
  ]);
  renderRanking("chart-frios", "msg-frios-vazio", dados.frios, "Temp Mín Média (°C)", [
    "#08306b",
    "#deebf7",
  ]);
}

async function carregarTendencia(meso: string, days: number): Promise<void> {
  setText("tendencia-titulo", `Temperatura média por mesorregião — últimos ${days} dias`);
  const params = new URLSearchParams({ days: String(days) });
  if (meso !== "Todas") params.set("meso", meso);
  const resposta = await fetch(`/api/v1/temperatura/tendencia-mesorregiao?${params.toString()}`);
  if (!resposta.ok) {
    setText("temp-erro", `Erro ao carregar tendência (HTTP ${resposta.status})`);
    return;
  }
  const dados = (await resposta.json()) as { rows: TendenciaRow[] };
  renderTendencia(dados.rows);
}

async function carregarAnomalia(days: number): Promise<void> {
  setText("anomalia-titulo", `Anomalia térmica por mesorregião — últimos ${days} dias`);
  const resposta = await fetch(`/api/v1/temperatura/anomalia?days=${days}`);
  if (!resposta.ok) {
    setText("temp-erro", `Erro ao carregar anomalia (HTTP ${resposta.status})`);
    return;
  }
  const dados = (await resposta.json()) as { rows: AnomaliaRow[] };
  renderAnomalia(dados.rows);
}

function carregar(meso: string, days: number): void {
  void carregarRankings(meso);
  void carregarTendencia(meso, days);
  void carregarAnomalia(days);
}

export function initTemperatura(): void {
  const select = byId<HTMLSelectElement>("filtro-mesorregiao");
  const diasInput = byId<HTMLInputElement>("filtro-dias");
  if (select === null || diasInput === null) return;

  void carregarCaption();
  void popularMesorregioes(select).then(() => carregar(select.value, clampDias(diasInput.value)));

  const rerender = (): void => carregar(select.value, clampDias(diasInput.value));
  select.addEventListener("change", rerender);
  diasInput.addEventListener("change", rerender);
}
