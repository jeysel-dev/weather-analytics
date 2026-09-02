// Página Alertas (spec 009) — migração de streamlit/pages/3_Alertas.py.
//
// 4 blocos, mesmo WHERE (dias 7–60 / mesorregião / severidade):
//   - 5 KPIs (tiles HTML)                       -> /api/v1/alertas/resumo
//   - Por tipo de alerta (bar horizontal stack) -> /api/v1/alertas/por-tipo
//   - Municípios mais afetados (bar horizontal) -> /api/v1/alertas/municipios
//   - Alertas recentes (tabela HTML, ≤200)      -> /api/v1/alertas/recentes
//
// Tradução de alert_type/severity vem PRONTA do backend (spec 009/014);
// cor/ícone por severidade vêm de web/src/labels.ts.

import { fmtN, formatarDataISO } from "../format";
import { SEV_COLORS, SEV_ICON } from "../labels";
import { byId, chartFor, setText, toggle } from "../ui";

interface Resumo {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}
interface PorTipoRow {
  alert_type_pt: string;
  severity: string;
  severity_pt: string;
  qtd: number;
}
interface MunicipioRow {
  city_name: string;
  mesoregion: string | null;
  alertas: number;
}
interface RecenteRow {
  date: string;
  city_name: string;
  mesoregion: string | null;
  alert_type_pt: string;
  severity: string;
  severity_pt: string;
  temp_max: number | null;
  anomalia: number | null;
  precip: number | null;
  vento_max: number | null;
  uv_index_max: number | null;
}

const SEV_ORDER = ["critical", "high", "medium", "low"] as const;
const MESO_PALETTE = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272"];

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
  const resposta = await fetch("/api/v1/ref/alerts-meta");
  if (!resposta.ok) return;
  const meta = (await resposta.json()) as { max_date: string | null };
  if (meta.max_date !== null) {
    setText("alertas-caption", `Dados disponíveis até ${formatarDataISO(meta.max_date)}`);
  }
}

// ── KPIs ────────────────────────────────────────────────────────────────────
function renderResumo(r: Resumo): void {
  setText("kpi-total", String(r.total ?? 0));
  setText("kpi-critical", String(r.critical ?? 0));
  setText("kpi-high", String(r.high ?? 0));
  setText("kpi-medium", String(r.medium ?? 0));
  setText("kpi-low", String(r.low ?? 0));
}

// ── Por tipo de alerta ──────────────────────────────────────────────────────
function renderPorTipo(rows: PorTipoRow[]): void {
  const chart = chartFor("chart-portipo");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-portipo-vazio"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-portipo-vazio"), false);

  const tipos = [...new Set(rows.map((r) => r.alert_type_pt))];
  const sevPresentes = SEV_ORDER.filter((s) => rows.some((r) => r.severity === s));
  const chave = (tipo: string, sev: string): number =>
    rows.find((r) => r.alert_type_pt === tipo && r.severity === sev)?.qtd ?? 0;
  const rotuloSev = (sev: string): string =>
    rows.find((r) => r.severity === sev)?.severity_pt ?? sev;

  chart.setOption(
    {
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { top: 0 },
      grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: "value", name: "Ocorrências" },
      yAxis: { type: "category", data: [...tipos].reverse() },
      series: sevPresentes.map((sev) => ({
        name: rotuloSev(sev),
        type: "bar",
        stack: "sev",
        itemStyle: { color: SEV_COLORS[sev] },
        data: [...tipos].reverse().map((t) => chave(t, sev)),
      })),
    },
    true,
  );
}

// ── Municípios mais afetados ────────────────────────────────────────────────
function renderMunicipios(rows: MunicipioRow[]): void {
  const chart = chartFor("chart-municipios");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-municipios-vazio"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-municipios-vazio"), false);

  const linhas = [...rows].reverse();
  const mesos = [...new Set(linhas.map((r) => r.mesoregion ?? "—"))];
  const container = byId<HTMLElement>("chart-municipios");
  if (container !== null) container.style.height = `${Math.max(320, linhas.length * 22)}px`;
  chart.resize();

  chart.setOption(
    {
      tooltip: { trigger: "item", formatter: "{b} — {a}: {c}" },
      legend: { top: 0, type: "scroll" },
      grid: { left: 8, right: 24, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: "value", name: "Nº de Alertas" },
      yAxis: { type: "category", data: linhas.map((r) => r.city_name) },
      series: mesos.map((m, i) => ({
        name: m,
        type: "bar",
        stack: "total",
        itemStyle: { color: MESO_PALETTE[i % MESO_PALETTE.length] },
        data: linhas.map((r) => ((r.mesoregion ?? "—") === m ? r.alertas : null)),
      })),
    },
    true,
  );
}

// ── Tabela de alertas recentes ─────────────────────────────────────────────
function renderRecentes(rows: RecenteRow[]): void {
  const tabela = byId<HTMLTableElement>("tabela-recentes");
  const tbody = tabela?.querySelector("tbody");
  if (tabela === null || tbody === undefined || tbody === null) return;
  tbody.replaceChildren();
  if (rows.length === 0) {
    toggle(tabela, false);
    toggle(byId("msg-recentes-vazio"), true);
    return;
  }
  toggle(byId("msg-recentes-vazio"), false);
  toggle(tabela, true);
  for (const r of rows) {
    const tr = document.createElement("tr");
    const celulas = [
      formatarDataISO(r.date),
      r.city_name,
      r.mesoregion ?? "—",
      r.alert_type_pt,
      `${SEV_ICON[r.severity] ?? ""} ${r.severity_pt}`.trim(),
      fmtN(r.temp_max, 1),
      fmtN(r.anomalia, 1),
      fmtN(r.precip, 1),
      fmtN(r.vento_max, 1),
      fmtN(r.uv_index_max, 0),
    ];
    for (const texto of celulas) {
      const td = document.createElement("td");
      td.textContent = texto;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

// ── Orquestração ────────────────────────────────────────────────────────────
function clampDias(raw: string): number {
  const n = Number.parseInt(raw, 10);
  if (Number.isNaN(n)) return 30;
  return Math.min(60, Math.max(7, n));
}

function buildParams(dias: number, meso: string, severidade: string): string {
  const p = new URLSearchParams({ days: String(dias) });
  if (meso !== "Todas") p.set("meso", meso);
  if (severidade !== "Todas") p.set("severity", severidade);
  return p.toString();
}

async function carregar(dias: number, meso: string, severidade: string): Promise<void> {
  setText("recentes-titulo", `Alertas recentes — últimos ${dias} dias`);
  const qs = buildParams(dias, meso, severidade);
  const [resumo, porTipo, municipios, recentes] = await Promise.all([
    fetch(`/api/v1/alertas/resumo?${qs}`),
    fetch(`/api/v1/alertas/por-tipo?${qs}`),
    fetch(`/api/v1/alertas/municipios?${qs}`),
    fetch(`/api/v1/alertas/recentes?${qs}`),
  ]);
  const respostas = [resumo, porTipo, municipios, recentes];
  if (respostas.some((r) => !r.ok)) {
    const status = respostas.find((r) => !r.ok)?.status ?? 0;
    setText("alertas-erro", `Erro ao carregar dados (HTTP ${status})`);
    return;
  }
  toggle(byId("alertas-erro"), false);
  renderResumo((await resumo.json()) as Resumo);
  renderPorTipo(((await porTipo.json()) as { rows: PorTipoRow[] }).rows);
  renderMunicipios(((await municipios.json()) as { rows: MunicipioRow[] }).rows);
  renderRecentes(((await recentes.json()) as { rows: RecenteRow[] }).rows);
}

export function initAlertas(): void {
  const dias = byId<HTMLInputElement>("filtro-dias");
  const meso = byId<HTMLSelectElement>("filtro-mesorregiao");
  const sev = byId<HTMLSelectElement>("filtro-severidade");
  if (dias === null || meso === null || sev === null) return;

  void carregarCaption();
  void popularMesorregioes(meso).then(() =>
    carregar(clampDias(dias.value), meso.value, sev.value),
  );

  const rerender = (): void => void carregar(clampDias(dias.value), meso.value, sev.value);
  for (const el of [dias, meso, sev]) el.addEventListener("change", rerender);
}
