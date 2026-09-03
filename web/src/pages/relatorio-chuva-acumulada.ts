// Página Chuva Acumulada (spec 022) — relatório puramente tabular.
//
// Ranking de precipitação acumulada por município na janela, com dias de
// chuva e o maior volume diário (+ data). Filtros: período em dias +
// macrorregião opcional. Sem linha de total.

import { fmt1, formatarDataISO } from "../format";
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
    setText("chuva-caption", `Dados disponíveis até ${formatarDataISO(meta.max_date)}`);
  }
}

async function atualizar(dias: number, meso: string): Promise<void> {
  const tabela = byId<HTMLTableElement>("tabela-chuva");
  if (tabela === null) return;
  const mesoQs = meso === "Todas" ? "" : `&meso=${encodeURIComponent(meso)}`;
  const resposta = await fetch(
    `/api/v1/relatorio-chuva-acumulada/dados?dias=${dias}${mesoQs}`,
  );
  if (!resposta.ok) {
    setText("chuva-msg", `Erro ao carregar o relatório (HTTP ${resposta.status})`);
    toggle(tabela, false);
    return;
  }
  const dados = (await resposta.json()) as { rows: ChuvaRow[] };
  const rows: RowDef[] = dados.rows.map((r) => ({
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
    onEmpty: () => setText("chuva-msg", "Sem dados para o período selecionado."),
  });
  if (ok) toggle(byId("chuva-msg"), false);
}

export function initRelatorioChuvaAcumulada(): void {
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
