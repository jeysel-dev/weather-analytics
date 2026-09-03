// Página Relatório por Cidade (spec 013) —
// migração de streamlit/pages/7_Relatorio_Cidade.py.
//
// Única página com ESTADO NA URL (deep link) e SEM gráfico. Lê/escreve
// ?cidades=&inicio=&fim= na query string; a razão de existir é o
// compartilhamento por link (botão -> wa.me).
//
// Referência: /api/v1/ref/cidades + /api/v1/ref/daily-meta (spec 014).
// Dados: /api/v1/relatorio-cidade/dados.

import { enhanceCitySelect } from "../citypicker";
import { fmt1, formatarDataISO } from "../format";

// Esta página NÃO importa de ../ui de propósito. O bundle é único (um só
// entry em vite.config.ts, sem code splitting), então o ECharts já entra
// no arquivo final pelas outras páginas — não importar de ui.ts aqui não
// muda o que o navegador baixa. O motivo é local: esta página não tem
// gráfico, e os helpers de chart de ui.ts seriam código morto neste
// módulo. Os 3 helpers de DOM abaixo são cópias locais.
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

interface DiaRow {
  date: string;
  city_name: string;
  temp_max_c: number | null;
  temp_min_c: number | null;
  precipitation_mm: number | null;
  wind_speed_max_kmh: number | null;
}

interface SubtotalRow {
  city_name: string;
  temp_maxima: number | null;
  temp_maxima_media: number | null;
  temp_minima: number | null;
  temp_minima_media: number | null;
  precip_acumulada: number | null;
  vento_maximo: number | null;
}

interface RelatorioResponse {
  dias: DiaRow[];
  subtotais: SubtotalRow[];
  total_geral: SubtotalRow | null;
}

const DOMINIO_PUBLICO = "https://weather.jeysel.dev/relatorio-cidade";

let CIDADES_VALIDAS = new Set<string>();
let MIN_DATE = "";
let MAX_DATE = "";

function subtrairDias(iso: string, dias: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - dias);
  return d.toISOString().slice(0, 10);
}

function cidadesSelecionadas(select: HTMLSelectElement): string[] {
  return [...select.selectedOptions].map((o) => o.value);
}

// ── Estado na URL ──────────────────────────────────────────────────────────
function lerURL(): { cidades: string[]; inicio: string | null; fim: string | null } {
  const qs = new URLSearchParams(window.location.search);
  const cidadesRaw = qs.get("cidades");
  const cidades = cidadesRaw
    ? cidadesRaw.split(",").filter((c) => CIDADES_VALIDAS.has(c))
    : [];
  let inicio = qs.get("inicio");
  let fim = qs.get("fim");
  // Validação (mesma regra do Streamlit): min <= inicio <= fim <= max.
  if (inicio !== null && fim !== null) {
    const ok =
      /^\d{4}-\d{2}-\d{2}$/.test(inicio) &&
      /^\d{4}-\d{2}-\d{2}$/.test(fim) &&
      MIN_DATE <= inicio &&
      inicio <= fim &&
      fim <= MAX_DATE;
    if (!ok) {
      inicio = null;
      fim = null;
    }
  } else {
    inicio = null;
    fim = null;
  }
  return { cidades, inicio, fim };
}

function escreverURL(cidades: string[], inicio: string, fim: string): void {
  const qs = new URLSearchParams();
  if (cidades.length > 0) qs.set("cidades", cidades.join(","));
  if (inicio !== "") qs.set("inicio", inicio);
  if (fim !== "") qs.set("fim", fim);
  const nova = qs.toString();
  window.history.replaceState(null, "", nova === "" ? window.location.pathname : `?${nova}`);
}

// ── Tabela + compartilhamento ─────────────────────────────────────────────
// Uma linha por dia do período, agrupadas por cidade; após os dias de cada
// cidade, a linha de SUBTOTAL dela; no fim da tabela, SEMPRE (mesmo com uma
// cidade só) a linha TOTAL GERAL. "Temp. * Média" não se aplica a um dia
// isolado — célula vazia ("—") nas linhas diárias.
function renderTabela(dados: RelatorioResponse): void {
  const tabela = byId<HTMLTableElement>("tabela-relatorio");
  const tbody = tabela?.querySelector("tbody");
  if (tabela === null || tbody === undefined || tbody === null) return;
  tbody.replaceChildren();
  if (dados.dias.length === 0) {
    toggle(tabela, false);
    setText("relatorio-msg", "Sem dados para o período selecionado.");
    return;
  }
  toggle(byId("relatorio-msg"), false);
  toggle(tabela, true);

  const addRow = (celulas: string[], cls?: string): void => {
    const tr = document.createElement("tr");
    if (cls !== undefined) tr.className = cls;
    for (const texto of celulas) {
      const td = document.createElement("td");
      td.textContent = texto;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  };

  const subtotalPorCidade = new Map<string, SubtotalRow>();
  for (const s of dados.subtotais) subtotalPorCidade.set(s.city_name, s);

  // Ordem de aparição das cidades nas linhas diárias (backend já ordena
  // por city_name, date).
  const diasPorCidade = new Map<string, DiaRow[]>();
  for (const d of dados.dias) {
    const lista = diasPorCidade.get(d.city_name) ?? [];
    lista.push(d);
    diasPorCidade.set(d.city_name, lista);
  }

  for (const [cidade, dias] of diasPorCidade) {
    for (const d of dias) {
      addRow([
        formatarDataISO(d.date),
        cidade,
        fmt1(d.temp_max_c),
        "—",
        fmt1(d.temp_min_c),
        "—",
        fmt1(d.precipitation_mm),
        fmt1(d.wind_speed_max_kmh),
      ]);
    }
    const sub = subtotalPorCidade.get(cidade);
    if (sub !== undefined) {
      addRow(
        [
          "",
          `Subtotal — ${cidade}`,
          fmt1(sub.temp_maxima),
          fmt1(sub.temp_maxima_media),
          fmt1(sub.temp_minima),
          fmt1(sub.temp_minima_media),
          fmt1(sub.precip_acumulada),
          fmt1(sub.vento_maximo),
        ],
        "row-subtotal",
      );
    }
  }

  const tg = dados.total_geral;
  if (tg !== null) {
    addRow(
      [
        "",
        "Total Geral",
        fmt1(tg.temp_maxima),
        fmt1(tg.temp_maxima_media),
        fmt1(tg.temp_minima),
        fmt1(tg.temp_minima_media),
        fmt1(tg.precip_acumulada),
        fmt1(tg.vento_maximo),
      ],
      "row-total",
    );
  }
}

function atualizarCompartilhar(cidades: string[], inicio: string, fim: string): void {
  const botao = byId<HTMLAnchorElement>("btn-compartilhar");
  if (botao === null) return;
  const params = new URLSearchParams({ cidades: cidades.join(","), inicio, fim });
  const shareUrl = `${DOMINIO_PUBLICO}?${params.toString()}`;
  const msg =
    `Relatório de clima - ${cidades.join(", ")} - ` +
    `Período: ${formatarDataISO(inicio)} a ${formatarDataISO(fim)}. ` +
    `Veja o relatório completo: ${shareUrl}`;
  botao.href = `https://wa.me/?text=${encodeURIComponent(msg)}`;
  botao.hidden = false;
}

// ── Orquestração ──────────────────────────────────────────────────────────
async function atualizar(): Promise<void> {
  const select = byId<HTMLSelectElement>("filtro-cidades");
  const inicioInput = byId<HTMLInputElement>("filtro-inicio");
  const fimInput = byId<HTMLInputElement>("filtro-fim");
  if (select === null || inicioInput === null || fimInput === null) return;

  const cidades = cidadesSelecionadas(select);
  const inicio = inicioInput.value;
  const fim = fimInput.value;
  escreverURL(cidades, inicio, fim);

  const botao = byId<HTMLAnchorElement>("btn-compartilhar");
  if (botao !== null) botao.hidden = true;
  toggle(byId("tabela-relatorio"), false);
  toggle(byId("relatorio-caption"), false);

  if (cidades.length === 0) {
    setText("relatorio-msg", "Selecione ao menos uma cidade para gerar o relatório.");
    return;
  }
  if (inicio === "" || fim === "") {
    setText("relatorio-msg", "Selecione a data final do período.");
    return;
  }

  setText(
    "relatorio-caption",
    `Cidades: ${cidades.join(", ")} | Período: ${formatarDataISO(inicio)} a ${formatarDataISO(fim)}`,
  );

  const params = new URLSearchParams({ inicio, fim });
  for (const c of cidades) params.append("cidades", c);
  const resposta = await fetch(`/api/v1/relatorio-cidade/dados?${params.toString()}`);
  if (!resposta.ok) {
    setText("relatorio-msg", `Erro ao carregar o relatório (HTTP ${resposta.status})`);
    return;
  }
  const dados = (await resposta.json()) as RelatorioResponse;
  renderTabela(dados);
  if (dados.dias.length > 0) atualizarCompartilhar(cidades, inicio, fim);
}

export function initRelatorioCidade(): void {
  const select = byId<HTMLSelectElement>("filtro-cidades");
  const inicioInput = byId<HTMLInputElement>("filtro-inicio");
  const fimInput = byId<HTMLInputElement>("filtro-fim");
  if (select === null || inicioInput === null || fimInput === null) return;

  void (async () => {
    const [cidadesResp, metaResp] = await Promise.all([
      fetch("/api/v1/ref/cidades"),
      fetch("/api/v1/ref/daily-meta"),
    ]);
    if (cidadesResp.ok) {
      const cidades = (await cidadesResp.json()) as string[];
      CIDADES_VALIDAS = new Set(cidades);
      for (const c of cidades) {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        select.appendChild(opt);
      }
    }
    // Combobox pesquisável múltiplo (spec 020) — depois de popular as
    // options, antes de aplicar a seleção da URL.
    const picker = enhanceCitySelect(select);
    if (metaResp.ok) {
      const meta = (await metaResp.json()) as { min_date: string | null; max_date: string | null };
      if (meta.min_date !== null && meta.max_date !== null) {
        MIN_DATE = meta.min_date;
        MAX_DATE = meta.max_date;
        for (const input of [inicioInput, fimInput]) {
          input.min = MIN_DATE;
          input.max = MAX_DATE;
        }
      }
    }

    // Defaults + estado da URL.
    const urlState = lerURL();
    const defFim = MAX_DATE;
    const menos30 = MAX_DATE !== "" ? subtrairDias(MAX_DATE, 30) : "";
    const defInicio = menos30 !== "" && menos30 < MIN_DATE ? MIN_DATE : menos30;

    inicioInput.value = urlState.inicio ?? defInicio;
    fimInput.value = urlState.fim ?? defFim;
    // `true` = silencioso: não dispara `change` (atualizar() é chamado
    // explicitamente no fim). O Tom Select sincroniza `option.selected`,
    // então `cidadesSelecionadas()` segue lendo `select.selectedOptions`.
    picker.setValue(urlState.cidades, true);

    select.addEventListener("change", () => void atualizar());
    inicioInput.addEventListener("change", () => void atualizar());
    fimInput.addEventListener("change", () => void atualizar());

    void atualizar();
  })();
}
