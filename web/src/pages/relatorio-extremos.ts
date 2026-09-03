// Página Extremos e Recordes (spec 022) — relatório puramente tabular.
//
// 6 linhas fixas (uma por indicador): o recorde da janela com valor,
// cidade e data. Filtros: período em dias + macrorregião opcional.

import { fmt1, formatarDataISO } from "../format";
import { renderTable, type RowDef } from "../table";
import { byId, setText, toggle } from "../ui";

interface ExtremoRow {
  indicador: string;
  valor: number | null;
  city_name: string | null;
  date: string | null;
}

function clampDias(raw: string): number {
  const n = Number.parseInt(raw, 10);
  if (Number.isNaN(n)) return 30;
  return Math.min(365, Math.max(7, n));
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
  const mesoQs = meso === "Todas" ? "" : `&meso=${encodeURIComponent(meso)}`;
  const resposta = await fetch(`/api/v1/relatorio-extremos/dados?dias=${dias}${mesoQs}`);
  if (!resposta.ok) {
    setText("extremos-msg", `Erro ao carregar o relatório (HTTP ${resposta.status})`);
    toggle(tabela, false);
    return;
  }
  const dados = (await resposta.json()) as { rows: ExtremoRow[] };
  const rows: RowDef[] = dados.rows.map((r) => ({
    cells: [r.indicador, fmt1(r.valor), r.city_name, formatarDataISO(r.date)],
  }));
  const ok = renderTable(tabela, rows, {
    onEmpty: () => setText("extremos-msg", "Sem dados para o período selecionado."),
  });
  if (ok) toggle(byId("extremos-msg"), false);
}

export function initRelatorioExtremos(): void {
  const diasInput = byId<HTMLInputElement>("filtro-dias");
  const mesoSelect = byId<HTMLSelectElement>("filtro-mesorregiao");
  if (diasInput === null || mesoSelect === null) return;

  void carregarCaption();
  void popularMesorregioes(mesoSelect).then(() =>
    atualizar(clampDias(diasInput.value), mesoSelect.value),
  );

  const rerender = (): void => void atualizar(clampDias(diasInput.value), mesoSelect.value);
  diasInput.addEventListener("change", rerender);
  mesoSelect.addEventListener("change", rerender);
}
