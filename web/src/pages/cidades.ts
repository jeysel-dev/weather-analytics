// Página Cidades / "Perfil por Município" (spec 011) —
// migração de streamlit/pages/5_Cidades.py.
//
// Cabeçalho + 4 KPIs + 4 abas lendo /api/v1/cidades/*:
//   - lista (municípios COM metadados: lat/lon/altitude/mesorregião)
//   - clima (linhas diárias + resumo agregado para os KPIs)
//   - alertas (tabela HTML, ≤100)
//
// altitude_m nulo -> placeholder "—" no cabeçalho (correção deliberada de
// robustez, spec 011). Rótulo/cor de classe e tradução de alerta: labels.ts
// (spec 014) — clima devolve o valor cru; alertas já vêm traduzidos.

import { enhanceCitySelect } from "../citypicker";
import { fmt1, fmtN, fmtSigned, formatarDataISO } from "../format";
import { CLASS_COLORS, CLASS_LABELS_PT, SEV_ICON } from "../labels";
import { byId, chartFor, initTabs, setText, toggle } from "../ui";

interface CidadeMeta {
  city_name: string;
  mesoregion: string | null;
  latitude: number | null;
  longitude: number | null;
  altitude_m: number | null;
}
interface ClimaRow {
  date: string;
  temp_max_c: number | null;
  temp_min_c: number | null;
  temp_avg_c: number | null;
  temp_anomaly_c: number | null;
  precipitation_mm: number | null;
  precipitation_class: string | null;
  wind_speed_max_kmh: number | null;
  uv_index_max: number | null;
}
interface ClimaResumo {
  temp_max_mean: number | null;
  temp_min_mean: number | null;
  temp_anomaly_mean: number | null;
  precip_total: number | null;
  dias_chuva: number;
  dias_total: number;
}
interface ClimaResponse {
  resumo: ClimaResumo | null;
  rows: ClimaRow[];
}
interface AlertaRow {
  date: string;
  alert_type_pt: string;
  severity: string;
  severity_pt: string;
  temp_max: number | null;
  anomalia: number | null;
  precip: number | null;
  vento: number | null;
  uv_index_max: number | null;
}

const meta = new Map<string, CidadeMeta>();

// Paginação client-side da tabela de alertas (spec 018). Estado de módulo, não
// global: quantas linhas mostrar e a última resposta de /alertas, pra o botão
// "Ver mais" re-renderizar sem refazer a busca.
const ALERTAS_PAGE = 10;
let alertasMax = ALERTAS_PAGE;
let ultimoAlertas: { rows: AlertaRow[]; city: string; days: number } | null = null;

function hemisferio(valor: number, neg: string, pos: string): string {
  return `${Math.abs(valor).toFixed(2)}°${valor < 0 ? neg : pos}`;
}

function renderCabecalho(info: CidadeMeta): void {
  setText("cidade-nome", `📍 ${info.city_name}`);
  const alt = info.altitude_m === null ? "—" : `${info.altitude_m.toFixed(0)} m`;
  const coords =
    info.latitude !== null && info.longitude !== null
      ? ` · ${hemisferio(info.latitude, "S", "N")}, ${hemisferio(info.longitude, "W", "E")}`
      : "";
  setText(
    "cidade-caption",
    `Mesorregião: ${info.mesoregion ?? "—"} · Altitude: ${alt}${coords}`,
  );
}

function renderKpis(r: ClimaResumo): void {
  // Sem lógica condicional aqui: o servidor já decide o que é "sem dado"
  // (campos null no resumo agregado, ver _mean() em api/app/routers/cidades.py)
  // e fmt1/fmtSigned viram "—". Em particular a Anomalia Média é "—" quando
  // não há dado, não "+0.0" como no Streamlit.
  setText("kpi-temp-max", `${fmt1(r.temp_max_mean)} °C`);
  setText("kpi-temp-min", `${fmt1(r.temp_min_mean)} °C`);
  setText("kpi-precip", `${fmt1(r.precip_total)} mm`);
  setText("kpi-anomalia", `${fmtSigned(r.temp_anomaly_mean)} °C`);
  setText("kpi-total-chuva", `${fmt1(r.precip_total)} mm`);
  setText("kpi-dias-chuva", `${r.dias_chuva} de ${r.dias_total}`);
}

// ── Aba Temperatura ────────────────────────────────────────────────────────
function renderTemp(rows: ClimaRow[]): void {
  const chart = chartFor("chart-temp");
  if (chart === null) return;
  const datas = rows.map((r) => formatarDataISO(r.date));
  chart.setOption(
    {
      tooltip: { trigger: "axis", valueFormatter: (v: unknown) => fmt1(Number(v)) },
      legend: { top: 0 },
      grid: { left: 48, right: 56, top: 36, bottom: 32 },
      xAxis: { type: "category", data: datas },
      yAxis: [
        { type: "value", name: "°C" },
        { type: "value", name: "Anomalia (°C)", position: "right" },
      ],
      series: [
        { name: "Máxima", type: "line", showSymbol: false, itemStyle: { color: "#EF5350" }, data: rows.map((r) => r.temp_max_c) },
        { name: "Média", type: "line", showSymbol: false, itemStyle: { color: "#FFA726" }, data: rows.map((r) => r.temp_avg_c) },
        { name: "Mínima", type: "line", showSymbol: false, itemStyle: { color: "#42A5F5" }, data: rows.map((r) => r.temp_min_c) },
        {
          name: "Anomalia",
          type: "bar",
          yAxisIndex: 1,
          // null (dado ausente) -> null puro: o ECharts trata como gap e não
          // desenha barra. Converter para 0 faria um dia sem dado virar uma
          // barra de altura zero, indistinguível de anomalia real igual a zero
          // (mesmo problema já corrigido no KPI agregado).
          data: rows.map((r) => {
            const v = r.temp_anomaly_c;
            return v === null
              ? null
              : { value: v, itemStyle: { color: v > 0 ? "#D32F2F" : "#1565C0", opacity: 0.45 } };
          }),
        },
      ],
    },
    true,
  );
}

// ── Aba Precipitação ──────────────────────────────────────────────────────
function renderPrecip(rows: ClimaRow[]): void {
  const chart = chartFor("chart-precip");
  if (chart === null) return;
  const datas = rows.map((r) => formatarDataISO(r.date));
  const classes = [...new Set(rows.map((r) => r.precipitation_class ?? "—"))];
  chart.setOption(
    {
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { top: 0 },
      grid: { left: 48, right: 16, top: 36, bottom: 32 },
      xAxis: { type: "category", data: datas },
      yAxis: { type: "value", name: "Precipitação (mm)" },
      series: classes.map((cls) => ({
        name: CLASS_LABELS_PT[cls] ?? cls,
        type: "bar",
        stack: "chuva",
        itemStyle: { color: CLASS_COLORS[cls] },
        data: rows.map((r) => ((r.precipitation_class ?? "—") === cls ? r.precipitation_mm : null)),
      })),
    },
    true,
  );
}

// ── Aba Vento & UV ────────────────────────────────────────────────────────
function renderVento(rows: ClimaRow[]): void {
  const chart = chartFor("chart-vento");
  if (chart === null) return;
  const datas = rows.map((r) => formatarDataISO(r.date));
  chart.setOption(
    {
      tooltip: { trigger: "axis", valueFormatter: (v: unknown) => fmt1(Number(v)) },
      legend: { top: 0 },
      grid: { left: 48, right: 56, top: 36, bottom: 32 },
      xAxis: { type: "category", data: datas },
      yAxis: [
        { type: "value", name: "Vento Máx (km/h)" },
        { type: "value", name: "Índice UV", position: "right" },
      ],
      series: [
        { name: "Vento Máx (km/h)", type: "bar", itemStyle: { color: "#66BB6A" }, data: rows.map((r) => r.wind_speed_max_kmh) },
        { name: "Índice UV Máx", type: "line", showSymbol: false, yAxisIndex: 1, itemStyle: { color: "#FF8F00" }, data: rows.map((r) => r.uv_index_max) },
      ],
    },
    true,
  );
}

// ── Aba Alertas ───────────────────────────────────────────────────────────
// Renderiza só as primeiras `maxDisplayed` linhas (spec 018). O botão
// "Ver mais" chama de novo com um valor maior — sem refazer a busca, a lista
// completa fica em `ultimoAlertas`.
function renderAlertas(
  rows: AlertaRow[],
  city: string,
  days: number,
  maxDisplayed = ALERTAS_PAGE,
): void {
  const tabela = byId<HTMLTableElement>("tabela-alertas");
  const tbody = tabela?.querySelector("tbody");
  const btnMais = byId<HTMLButtonElement>("btn-mais-alertas");
  if (tabela === null || tbody === undefined || tbody === null) return;
  tbody.replaceChildren();
  if (rows.length === 0) {
    toggle(tabela, false);
    toggle(btnMais, false);
    setText("msg-sem-alertas", `Nenhum alerta registrado para ${city} nos últimos ${days} dias.`);
    return;
  }
  toggle(byId("msg-sem-alertas"), false);
  toggle(tabela, true);
  for (const r of rows.slice(0, maxDisplayed)) {
    const tr = document.createElement("tr");
    const celulas = [
      formatarDataISO(r.date),
      r.alert_type_pt,
      `${SEV_ICON[r.severity] ?? ""} ${r.severity_pt}`.trim(),
      fmtN(r.temp_max, 1),
      fmtN(r.anomalia, 1),
      fmtN(r.precip, 1),
      fmtN(r.vento, 1),
      fmtN(r.uv_index_max, 0),
    ];
    for (const texto of celulas) {
      const td = document.createElement("td");
      td.textContent = texto;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }

  const restantes = Math.max(0, rows.length - maxDisplayed);
  if (btnMais !== null) {
    btnMais.hidden = restantes <= 0;
    btnMais.textContent = `Ver mais alertas (${restantes} restantes)`;
  }
}

// ── Orquestração ──────────────────────────────────────────────────────────
function clampDias(raw: string): number {
  const n = Number.parseInt(raw, 10);
  if (Number.isNaN(n)) return 90;
  return Math.min(365, Math.max(30, n));
}

async function carregar(city: string, days: number): Promise<void> {
  if (city === "") return;
  const info = meta.get(city);
  if (info !== undefined) renderCabecalho(info);

  const [climaResp, alertasResp] = await Promise.all([
    fetch(`/api/v1/cidades/clima?city=${encodeURIComponent(city)}&days=${days}`),
    fetch(`/api/v1/cidades/alertas?city=${encodeURIComponent(city)}&days=${days}`),
  ]);
  if (!climaResp.ok || !alertasResp.ok) {
    const status = !climaResp.ok ? climaResp.status : alertasResp.status;
    toggle(byId("cidade-conteudo"), false);
    setText("cidades-erro", `Erro ao carregar dados (HTTP ${status})`);
    return;
  }
  toggle(byId("cidades-erro"), false);

  const clima = (await climaResp.json()) as ClimaResponse;
  if (clima.resumo === null || clima.rows.length === 0) {
    toggle(byId("cidade-conteudo"), false);
    setText("msg-sem-dados", `Sem dados para ${city} no período de ${days} dias.`);
    return;
  }
  toggle(byId("msg-sem-dados"), false);
  toggle(byId("cidade-conteudo"), true);

  renderKpis(clima.resumo);
  renderTemp(clima.rows);
  renderPrecip(clima.rows);
  renderVento(clima.rows);
  const alertaRows = ((await alertasResp.json()) as { rows: AlertaRow[] }).rows;
  ultimoAlertas = { rows: alertaRows, city, days };
  renderAlertas(alertaRows, city, days, alertasMax);
}

export function initCidades(): void {
  const select = byId<HTMLSelectElement>("filtro-municipio");
  const diasInput = byId<HTMLInputElement>("filtro-dias");
  if (select === null || diasInput === null) return;

  // Gráficos são desenhados em containers ocultos (0px de largura); ao
  // abrir a aba, forçar o resize para o ECharts recalcular a geometria.
  initTabs((name) => chartFor(`chart-${name}`)?.resize());

  void (async () => {
    const resposta = await fetch("/api/v1/cidades/lista");
    if (!resposta.ok) {
      select.replaceChildren();
      setText("cidades-erro", "Não foi possível carregar a lista de municípios.");
      return;
    }
    const cidades = (await resposta.json()) as CidadeMeta[];
    select.replaceChildren();
    for (const c of cidades) {
      meta.set(c.city_name, c);
      const opt = document.createElement("option");
      opt.value = c.city_name;
      opt.textContent = c.city_name;
      select.appendChild(opt);
    }
    // Combobox pesquisável (spec 020) — depois de popular, antes do 1º
    // carregar(). `select.value` (1ª opção) segue válido; o listener de
    // `change` em initCidades continua disparando.
    enhanceCitySelect(select);
    if (cidades.length > 0) void carregar(select.value, clampDias(diasInput.value));
  })();

  const rerender = (): void => void carregar(select.value, clampDias(diasInput.value));
  // Trocar de município é uma lista de alertas nova — volta pra 10. Mexer só
  // no nº de dias mantém quantas linhas o usuário já revelou (spec 018).
  select.addEventListener("change", () => {
    alertasMax = ALERTAS_PAGE;
    rerender();
  });
  diasInput.addEventListener("change", rerender);

  const btnMais = byId<HTMLButtonElement>("btn-mais-alertas");
  btnMais?.addEventListener("click", () => {
    alertasMax += ALERTAS_PAGE;
    if (ultimoAlertas !== null) {
      renderAlertas(ultimoAlertas.rows, ultimoAlertas.city, ultimoAlertas.days, alertasMax);
    }
  });
}
