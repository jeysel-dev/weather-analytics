// Página Chuva Acumulada (spec 022) — relatório puramente tabular.
//
// Ranking de precipitação acumulada por município na janela, com dias de
// chuva e o maior volume diário (+ data). Filtros: período em dias +
// macrorregião opcional. Deep link ?dias=N&meso=… + botão Compartilhar,
// e paginação client-side (10 + "Ver mais") — spec 024.

import { fmt1, formatarDataISO } from "../format";
import { compartilharWhatsapp, esconderCompartilhar, escreverURL, lerURL } from "../share";
import { renderTable, type RowDef } from "../table";
import { byId, setText, toggle } from "../ui";

interface ChuvaRow {
  city_name: string;
  mesoregion: string | null;
  precip_acumulada: number | null;
  dias_chuva: number;
  maior_dia_mm: number | null;
  maior_dia_data: string | null;
}

const CHUVA_PAGE = 10;
let chuvaMax = CHUVA_PAGE;
let ultimoRows: ChuvaRow[] = [];

function clampDias(raw: string | null): number {
  const n = Number.parseInt(raw ?? "", 10);
  if (Number.isNaN(n)) return 30;
  return Math.min(365, Math.max(7, n));
}

function selecionarSePresente(select: HTMLSelectElement, valor: string | null): void {
  if (valor !== null && [...select.options].some((o) => o.value === valor)) {
    select.value = valor;
  }
}

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
    setText("chuva-caption", `Dados disponíveis até ${formatarDataISO(meta.max_date)}`);
  }
}

// Re-render in-place a partir de `ultimoRows` + `chuvaMax` (sem novo fetch).
function renderPagina(): void {
  const tabela = byId<HTMLTableElement>("tabela-chuva");
  const btnMais = byId<HTMLButtonElement>("btn-mais-chuva");
  if (tabela === null) return;

  const rows: RowDef[] = ultimoRows.map((r) => ({
    cells: [
      r.city_name,
      r.mesoregion,
      fmt1(r.precip_acumulada),
      String(r.dias_chuva),
      fmt1(r.maior_dia_mm),
      formatarDataISO(r.maior_dia_data),
    ],
  }));
  const ok = renderTable(tabela, rows, {
    limit: chuvaMax,
    onEmpty: () => {
      toggle(btnMais, false);
      setText("chuva-msg", "Sem dados para o período selecionado.");
    },
  });
  if (!ok) return;
  toggle(byId("chuva-msg"), false);

  const restantes = Math.max(0, ultimoRows.length - chuvaMax);
  if (btnMais !== null) {
    btnMais.hidden = restantes <= 0;
    btnMais.textContent = `Ver mais (${restantes} restantes)`;
  }
}

async function atualizar(dias: number, meso: string): Promise<void> {
  const tabela = byId<HTMLTableElement>("tabela-chuva");
  if (tabela === null) return;
  chuvaMax = CHUVA_PAGE; // filtro novo → volta ao topo
  const params = new URLSearchParams({ dias: String(dias) });
  if (meso !== "Todas") params.set("meso", meso);
  escreverURL(params);
  esconderCompartilhar();

  const resposta = await fetch(`/api/v1/relatorio-chuva-acumulada/dados?${params.toString()}`);
  if (!resposta.ok) {
    setText("chuva-msg", `Erro ao carregar o relatório (HTTP ${resposta.status})`);
    toggle(tabela, false);
    toggle(byId("btn-mais-chuva"), false);
    return;
  }
  ultimoRows = ((await resposta.json()) as { rows: ChuvaRow[] }).rows;
  renderPagina();

  if (ultimoRows.length > 0) {
    const alvo = meso === "Todas" ? "Santa Catarina" : meso;
    compartilharWhatsapp(`Chuva acumulada — ${alvo}, últimos ${dias} dias.`, params);
  }
}

export function initRelatorioChuvaAcumulada(): void {
  const diasInput = byId<HTMLInputElement>("filtro-dias");
  const mesoSelect = byId<HTMLSelectElement>("filtro-mesorregiao");
  if (diasInput === null || mesoSelect === null) return;

  const url = lerURL();
  const dias = clampDias(url.get("dias") ?? diasInput.value);
  diasInput.value = String(dias);

  void carregarCaption();
  void popularMesorregioes(mesoSelect).then(() => {
    selecionarSePresente(mesoSelect, url.get("meso"));
    void atualizar(clampDias(diasInput.value), mesoSelect.value);
  });

  const rerender = (): void => void atualizar(clampDias(diasInput.value), mesoSelect.value);
  diasInput.addEventListener("change", rerender);
  mesoSelect.addEventListener("change", rerender);
  byId("btn-mais-chuva")?.addEventListener("click", () => {
    chuvaMax += CHUVA_PAGE;
    renderPagina();
  });
}
