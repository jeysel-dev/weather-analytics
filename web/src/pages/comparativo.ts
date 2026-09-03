// Página Comparativo / "Análise Comparativa" (spec 012) —
// migração de streamlit/pages/6_Comparativo.py.
//
// 3 abas independentes, filtros NO CORPO de cada aba:
//   1. Comparativo de Cidades -> /api/v1/comparativo/cidades-serie
//   2. Quando Choveu          -> /api/v1/comparativo/chuva-heatmap
//   3. Dia vs Histórico       -> /api/v1/comparativo/datas-disponiveis + /dia-vs-historico
//
// Listas de referência: /api/v1/ref/cidades e /api/v1/ref/mesorregioes (spec 014).

import { enhanceCitySelect } from "../citypicker";
import { fmt1, fmtSigned, formatarDataISO } from "../format";
import { byId, chartFor, initTabs, setText, toggle } from "../ui";

interface SerieRow {
  date: string;
  city_name: string;
  valor: number | null;
}
interface ResumoCidade {
  city_name: string;
  min: number | null;
  max: number | null;
  mean: number | null;
}
interface ChuvaRow {
  date: string;
  city_name: string;
  precipitation_mm: number | null;
}
interface PerfilHora {
  hour: number;
  temp: number | null;
  humidity: number | null;
}
interface HistHora {
  hour: number;
  avg_temp: number | null;
  avg_humidity: number | null;
}
interface DiaVsHistorico {
  atual: PerfilHora[];
  historico: HistHora[];
  desvio: { medio: number | null; maximo: number | null; minimo: number | null } | null;
}

const METRIC_LABEL: Record<string, string> = {
  temp_max: "Temperatura Máxima (°C)",
  temp_min: "Temperatura Mínima (°C)",
  temp_avg: "Temperatura Média (°C)",
  precip: "Precipitação (mm)",
};

async function fetchLista(url: string): Promise<string[]> {
  const resposta = await fetch(url);
  return resposta.ok ? ((await resposta.json()) as string[]) : [];
}

function preencher(select: HTMLSelectElement, valores: string[], manterPrimeiro = false): void {
  if (!manterPrimeiro) select.replaceChildren();
  for (const v of valores) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    select.appendChild(opt);
  }
}

function selecionarSePresente(select: HTMLSelectElement, valor: string): void {
  if ([...select.options].some((o) => o.value === valor)) select.value = valor;
}

// ══ Aba 1 — Comparativo de Cidades ═════════════════════════════════════════
function renderSerie(rows: SerieRow[], ylabel: string): void {
  const chart = chartFor("chart-cidades");
  if (chart === null) return;
  if (rows.length === 0) {
    toggle(byId("msg-cidades-vazio"), true);
    chart.clear();
    return;
  }
  toggle(byId("msg-cidades-vazio"), false);
  const datas = [...new Set(rows.map((r) => r.date))].sort();
  const cidades = [...new Set(rows.map((r) => r.city_name))];
  const porCidade = new Map<string, Map<string, number | null>>();
  for (const r of rows) {
    let m = porCidade.get(r.city_name);
    if (m === undefined) {
      m = new Map();
      porCidade.set(r.city_name, m);
    }
    m.set(r.date, r.valor);
  }
  chart.setOption(
    {
      tooltip: { trigger: "axis", valueFormatter: (v: unknown) => fmt1(Number(v)) },
      legend: { top: 0 },
      grid: { left: 52, right: 16, top: 40, bottom: 32 },
      xAxis: { type: "category", data: datas.map(formatarDataISO) },
      yAxis: { type: "value", name: ylabel },
      series: cidades.map((c) => ({
        name: c,
        type: "line",
        showSymbol: false,
        data: datas.map((d) => porCidade.get(c)?.get(d) ?? null),
      })),
    },
    true,
  );
}

function renderResumo(resumo: ResumoCidade[]): void {
  const tabela = byId<HTMLTableElement>("tabela-resumo");
  const tbody = tabela?.querySelector("tbody");
  if (tabela === null || tbody === undefined || tbody === null) return;
  tbody.replaceChildren();
  if (resumo.length === 0) {
    toggle(tabela, false);
    return;
  }
  toggle(tabela, true);
  for (const r of resumo) {
    const tr = document.createElement("tr");
    for (const texto of [r.city_name, fmt1(r.min), fmt1(r.max), fmt1(r.mean)]) {
      const td = document.createElement("td");
      td.textContent = texto;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

async function carregarCidades(): Promise<void> {
  const a = byId<HTMLSelectElement>("cmp-cidade-a");
  const b = byId<HTMLSelectElement>("cmp-cidade-b");
  const c = byId<HTMLSelectElement>("cmp-cidade-c");
  const metrica = byId<HTMLSelectElement>("cmp-metrica");
  const dias = byId<HTMLInputElement>("cmp-dias");
  if (a === null || b === null || c === null || metrica === null || dias === null) return;

  const cidades = [a.value, b.value];
  if (c.value !== "—") cidades.push(c.value);
  const params = new URLSearchParams();
  for (const cid of cidades) params.append("cities", cid);
  params.set("metric", metrica.value);
  params.set("days", String(clamp(dias.value, 7, 180, 30)));

  const resposta = await fetch(`/api/v1/comparativo/cidades-serie?${params.toString()}`);
  if (!resposta.ok) {
    setText("msg-cidades-vazio", `Erro ao carregar dados (HTTP ${resposta.status})`);
    return;
  }
  const dados = (await resposta.json()) as { rows: SerieRow[]; resumo: ResumoCidade[] };
  renderSerie(dados.rows, METRIC_LABEL[metrica.value] ?? "");
  renderResumo(dados.resumo);
}

// ══ Aba 2 — Quando Choveu ══════════════════════════════════════════════════
function renderChuva(rows: ChuvaRow[], meso: string): void {
  const chart = chartFor("chart-chuva");
  if (chart === null) return;
  if (rows.length === 0) {
    setText("msg-chuva-vazio", `Sem dados para ${meso} no período selecionado.`);
    chart.clear();
    return;
  }
  toggle(byId("msg-chuva-vazio"), false);
  const datas = [...new Set(rows.map((r) => r.date))].sort();
  const cidades = [...new Set(rows.map((r) => r.city_name))].sort();
  const data = rows.map((r) => [
    datas.indexOf(r.date),
    cidades.indexOf(r.city_name),
    r.precipitation_mm,
  ]);
  const container = byId<HTMLElement>("chart-chuva");
  if (container !== null) container.style.height = `${Math.max(320, cidades.length * 22)}px`;
  chart.resize();
  chart.setOption(
    {
      tooltip: {
        position: "top",
        formatter: (p: { value: [number, number, number | null] }) =>
          `${cidades[p.value[1]]} · ${formatarDataISO(datas[p.value[0]])}: ${fmt1(p.value[2] ?? null)} mm`,
      },
      grid: { left: 120, right: 16, top: 8, bottom: 70, containLabel: true },
      xAxis: { type: "category", data: datas.map(formatarDataISO), splitArea: { show: true } },
      yAxis: { type: "category", data: cidades, splitArea: { show: true } },
      visualMap: {
        type: "piecewise",
        orient: "horizontal",
        left: "center",
        bottom: 0,
        pieces: [
          { min: 0, max: 0, label: "Seco (0 mm)", color: "#F5F5F5" },
          { gt: 0, lte: 5, label: "Leve (< 5 mm)", color: "#B3E5FC" },
          { gt: 5, lte: 20, label: "Moderado (5–20 mm)", color: "#0288D1" },
          { gt: 20, lte: 50, label: "Forte (20–50 mm)", color: "#1565C0" },
          { gt: 50, label: "Extremo (> 50 mm)", color: "#4A148C" },
        ],
      },
      series: [{ type: "heatmap", data }],
    },
    true,
  );
}

async function carregarChuva(): Promise<void> {
  const meso = byId<HTMLSelectElement>("cmp-meso");
  const dias = byId<HTMLInputElement>("cmp-chuva-dias");
  if (meso === null || dias === null || meso.value === "") return;
  const params = new URLSearchParams({
    meso: meso.value,
    days: String(clamp(dias.value, 14, 60, 30)),
  });
  const resposta = await fetch(`/api/v1/comparativo/chuva-heatmap?${params.toString()}`);
  if (!resposta.ok) {
    setText("msg-chuva-vazio", `Erro ao carregar dados (HTTP ${resposta.status})`);
    return;
  }
  renderChuva(((await resposta.json()) as { rows: ChuvaRow[] }).rows, meso.value);
}

// ══ Aba 3 — Dia vs Histórico ══════════════════════════════════════════════
function renderPerfil(
  id: string,
  atualNome: string,
  atual: (number | null)[],
  hist: (number | null)[] | null,
  histNome: string,
  eixo: string,
  cor: string,
  range?: [number, number],
): void {
  const chart = chartFor(id);
  if (chart === null) return;
  const horas = Array.from({ length: 24 }, (_, h) => h);
  const series: Record<string, unknown>[] = [];
  if (hist !== null) {
    series.push({
      name: histNome,
      type: "line",
      data: hist,
      lineStyle: { type: "dashed", color: "#90A4AE" },
      itemStyle: { color: "#90A4AE" },
      showSymbol: false,
    });
  }
  series.push({
    name: atualNome,
    type: "line",
    data: atual,
    itemStyle: { color: cor },
    lineStyle: { color: cor, width: 3 },
  });
  chart.setOption(
    {
      tooltip: { trigger: "axis", valueFormatter: (v: unknown) => fmt1(Number(v)) },
      legend: { top: 0 },
      grid: { left: 48, right: 16, top: 40, bottom: 40 },
      xAxis: { type: "category", name: "Hora do dia", data: horas },
      yAxis: { type: "value", name: eixo, ...(range !== undefined ? { min: range[0], max: range[1] } : {}) },
      series,
    },
    true,
  );
}

function porHora<T extends { hour: number }>(rows: T[], campo: keyof T): (number | null)[] {
  const m = new Map(rows.map((r) => [r.hour, r[campo] as number | null]));
  return Array.from({ length: 24 }, (_, h) => m.get(h) ?? null);
}

async function carregarHistoricoDatas(): Promise<void> {
  const cidade = byId<HTMLSelectElement>("cmp-hist-cidade");
  const dataSel = byId<HTMLSelectElement>("cmp-hist-data");
  if (cidade === null || dataSel === null || cidade.value === "") return;
  const resposta = await fetch(
    `/api/v1/comparativo/datas-disponiveis?city=${encodeURIComponent(cidade.value)}`,
  );
  if (!resposta.ok) return;
  const dates = ((await resposta.json()) as { dates: string[] }).dates;
  dataSel.replaceChildren();
  if (dates.length === 0) {
    setText("msg-hist-sem-cidade", `Sem dados horários disponíveis para ${cidade.value}.`);
    toggle(byId("chart-hist-temp"), false);
    toggle(byId("chart-hist-umidade"), false);
    toggle(byId("hist-deltas"), false);
    return;
  }
  toggle(byId("msg-hist-sem-cidade"), false);
  toggle(byId("chart-hist-temp"), true);
  toggle(byId("chart-hist-umidade"), true);
  for (const d of dates) {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = formatarDataISO(d);
    dataSel.appendChild(opt);
  }
  await carregarHistorico();
}

async function carregarHistorico(): Promise<void> {
  const cidade = byId<HTMLSelectElement>("cmp-hist-cidade");
  const dataSel = byId<HTMLSelectElement>("cmp-hist-data");
  if (cidade === null || dataSel === null || dataSel.value === "") return;

  const resposta = await fetch(
    `/api/v1/comparativo/dia-vs-historico?city=${encodeURIComponent(cidade.value)}&date=${dataSel.value}`,
  );
  if (!resposta.ok) return;
  const dados = (await resposta.json()) as DiaVsHistorico;

  if (dados.atual.length === 0) {
    setText(
      "msg-hist-sem-data",
      `Sem dados horários para ${cidade.value} em ${formatarDataISO(dataSel.value)}.`,
    );
    toggle(byId("chart-hist-temp"), false);
    toggle(byId("chart-hist-umidade"), false);
    toggle(byId("hist-deltas"), false);
    return;
  }
  toggle(byId("msg-hist-sem-data"), false);
  toggle(byId("chart-hist-temp"), true);
  toggle(byId("chart-hist-umidade"), true);

  const temHist = dados.historico.length > 0;
  const dataLabel = formatarDataISO(dataSel.value);
  renderPerfil(
    "chart-hist-temp",
    dataLabel,
    porHora(dados.atual, "temp"),
    temHist ? porHora(dados.historico, "avg_temp") : null,
    "Média 30 dias anteriores",
    "Temperatura (°C)",
    "#EF5350",
  );
  renderPerfil(
    "chart-hist-umidade",
    `Umidade ${dataLabel}`,
    porHora(dados.atual, "humidity"),
    temHist ? porHora(dados.historico, "avg_humidity") : null,
    "Umidade média 30d",
    "Umidade (%)",
    "#42A5F5",
    [0, 105],
  );

  if (dados.desvio !== null) {
    toggle(byId("hist-deltas"), true);
    setText("delta-medio", `${fmtSigned(dados.desvio.medio)} °C`);
    setText("delta-max", `${fmtSigned(dados.desvio.maximo)} °C`);
    setText("delta-min", `${fmtSigned(dados.desvio.minimo)} °C`);
  } else {
    toggle(byId("hist-deltas"), false);
  }
}

// ══ Orquestração ══════════════════════════════════════════════════════════
function clamp(raw: string, lo: number, hi: number, fallback: number): number {
  const n = Number.parseInt(raw, 10);
  if (Number.isNaN(n)) return fallback;
  return Math.min(hi, Math.max(lo, n));
}

export function initComparativo(): void {
  initTabs((name) => {
    if (name === "chuva") {
      chartFor("chart-chuva")?.resize();
      void carregarChuva();
    } else if (name === "historico") {
      chartFor("chart-hist-temp")?.resize();
      chartFor("chart-hist-umidade")?.resize();
      void carregarHistoricoDatas();
    } else {
      chartFor("chart-cidades")?.resize();
    }
  });

  void (async () => {
    const [cidades, mesos] = await Promise.all([
      fetchLista("/api/v1/ref/cidades"),
      fetchLista("/api/v1/ref/mesorregioes"),
    ]);
    const a = byId<HTMLSelectElement>("cmp-cidade-a");
    const b = byId<HTMLSelectElement>("cmp-cidade-b");
    const cSel = byId<HTMLSelectElement>("cmp-cidade-c");
    const meso = byId<HTMLSelectElement>("cmp-meso");
    const histCidade = byId<HTMLSelectElement>("cmp-hist-cidade");
    if (a === null || b === null || cSel === null || meso === null || histCidade === null) return;

    preencher(a, cidades);
    preencher(b, cidades);
    preencher(cSel, cidades, true); // mantém a opção "—"
    preencher(meso, mesos);
    preencher(histCidade, cidades);

    selecionarSePresente(a, "Florianópolis");
    selecionarSePresente(b, "Lages");
    selecionarSePresente(cSel, "Chapecó");
    selecionarSePresente(histCidade, "Florianópolis");

    // Comboboxes pesquisáveis (spec 020) — depois de popular e de aplicar a
    // seleção inicial no <select> nativo. #cmp-meso fica nativo (~6 itens);
    // a <option value="—"> de #cmp-cidade-c segue como opção normal.
    for (const s of [a, b, cSel, histCidade]) enhanceCitySelect(s);

    for (const id of ["cmp-cidade-a", "cmp-cidade-b", "cmp-cidade-c", "cmp-metrica", "cmp-dias"]) {
      byId(id)?.addEventListener("change", () => void carregarCidades());
    }
    for (const id of ["cmp-meso", "cmp-chuva-dias"]) {
      byId(id)?.addEventListener("change", () => void carregarChuva());
    }
    byId("cmp-hist-cidade")?.addEventListener("change", () => void carregarHistoricoDatas());
    byId("cmp-hist-data")?.addEventListener("change", () => void carregarHistorico());

    void carregarCidades();
  })();
}
