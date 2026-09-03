// Página Extremos e Recordes (spec 022) — relatório puramente tabular.
//
// 6 linhas fixas (uma por indicador): o recorde da janela com valor,
// cidade e data. Filtros: período em dias + macrorregião opcional.
// Deep link ?dias=N&meso=… + botão Compartilhar (spec 024).

import { fmt1, formatarDataISO } from "../format";
import { compartilharWhatsapp, esconderCompartilhar, escreverURL, lerURL } from "../share";
import { renderTable, type RowDef } from "../table";
import { byId, setText, toggle } from "../ui";

interface ExtremoRow {
  indicador: string;
  valor: number | null;
  city_name: string | null;
  date: string | null;
}

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
    setText("extremos-caption", `Dados disponíveis até ${formatarDataISO(meta.max_date)}`);
  }
}

async function atualizar(dias: number, meso: string): Promise<void> {
  const tabela = byId<HTMLTableElement>("tabela-extremos");
  if (tabela === null) return;
  const params = new URLSearchParams({ dias: String(dias) });
  if (meso !== "Todas") params.set("meso", meso);
  escreverURL(params);
  esconderCompartilhar();

  const resposta = await fetch(`/api/v1/relatorio-extremos/dados?${params.toString()}`);
  if (!resposta.ok) {
    setText("extremos-msg", `Erro ao carregar o relatório (HTTP ${resposta.status})`);
    toggle(tabela, false);
    return;
  }
  const dados = (await resposta.json()) as { rows: ExtremoRow[] };

  // O endpoint devolve sempre 6 linhas; "sem dado" = todas com valor nulo.
  if (!dados.rows.some((r) => r.valor !== null)) {
    setText("extremos-msg", "Sem dados para o período selecionado.");
    toggle(tabela, false);
    return;
  }

  const rows: RowDef[] = dados.rows.map((r) => ({
    cells: [r.indicador, fmt1(r.valor), r.city_name, formatarDataISO(r.date)],
  }));
  renderTable(tabela, rows);
  toggle(byId("extremos-msg"), false);

  const alvo = meso === "Todas" ? "Santa Catarina" : meso;
  compartilharWhatsapp(`Extremos e recordes — ${alvo}, últimos ${dias} dias.`, params);
}

export function initRelatorioExtremos(): void {
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
}
