// Página Por Macrorregião (spec 022) — relatório puramente tabular.
//
// Uma linha por macrorregião (as 8 do seed) + total geral do estado:
// nº de municípios, médias de temperatura, chuva média/acumulada e nº de
// alertas na janela. Filtro único: período em dias. Deep link ?dias=N +
// botão Compartilhar (spec 024).

import { fmt1, formatarDataISO } from "../format";
import { compartilharWhatsapp, esconderCompartilhar, escreverURL, lerURL } from "../share";
import { renderTable, type RowDef } from "../table";
import { byId, setText, toggle } from "../ui";

interface MacroRow {
  mesoregion: string;
  municipios: number;
  temp_max_media: number | null;
  temp_min_media: number | null;
  precip_media: number | null;
  precip_acumulada: number | null;
  alertas: number;
}
interface MacroResponse {
  rows: MacroRow[];
  total_geral: MacroRow | null;
}

function celulas(nome: string, r: MacroRow): string[] {
  return [
    nome,
    String(r.municipios),
    fmt1(r.temp_max_media),
    fmt1(r.temp_min_media),
    fmt1(r.precip_media),
    fmt1(r.precip_acumulada),
    String(r.alertas),
  ];
}

function clampDias(raw: string | null): number {
  const n = Number.parseInt(raw ?? "", 10);
  if (Number.isNaN(n)) return 30;
  return Math.min(365, Math.max(7, n));
}

async function carregarCaption(): Promise<void> {
  const resposta = await fetch("/api/v1/ref/daily-meta");
  if (!resposta.ok) return;
  const meta = (await resposta.json()) as { max_date: string | null };
  if (meta.max_date !== null) {
    setText("macro-caption", `Dados disponíveis até ${formatarDataISO(meta.max_date)}`);
  }
}

async function atualizar(dias: number): Promise<void> {
  const tabela = byId<HTMLTableElement>("tabela-macro");
  if (tabela === null) return;
  const params = new URLSearchParams({ dias: String(dias) });
  escreverURL(params);
  esconderCompartilhar();

  const resposta = await fetch(`/api/v1/relatorio-macrorregiao/dados?dias=${dias}`);
  if (!resposta.ok) {
    setText("macro-msg", `Erro ao carregar o relatório (HTTP ${resposta.status})`);
    toggle(tabela, false);
    return;
  }
  const dados = (await resposta.json()) as MacroResponse;
  const rows: RowDef[] = dados.rows.map((r) => ({ cells: celulas(r.mesoregion, r) }));
  if (dados.total_geral !== null) {
    rows.push({ cells: celulas("Total Geral", dados.total_geral), variant: "total" });
  }
  const ok = renderTable(tabela, rows, {
    onEmpty: () => setText("macro-msg", "Sem dados para o período selecionado."),
  });
  if (ok) {
    toggle(byId("macro-msg"), false);
    compartilharWhatsapp(`Relatório por macrorregião — últimos ${dias} dias.`, params);
  }
}

export function initRelatorioMacrorregiao(): void {
  const diasInput = byId<HTMLInputElement>("filtro-dias");
  if (diasInput === null) return;
  void carregarCaption();

  const dias = clampDias(lerURL().get("dias") ?? diasInput.value);
  diasInput.value = String(dias);

  diasInput.addEventListener("change", () => void atualizar(clampDias(diasInput.value)));
  void atualizar(dias);
}
