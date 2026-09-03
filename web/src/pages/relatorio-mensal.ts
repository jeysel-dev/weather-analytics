// Página Consolidado Mensal (spec 022) — relatório puramente tabular.
//
// Cidade(s) × mês: médias de temperatura, amplitude, chuva acumulada, dias
// com chuva e vento máximo. Agrupado por cidade com subtotal + total geral
// (mesmo formato de 3 partes do /relatorio-cidade). Sem estado na URL, sem
// gráfico, sem botão de compartilhar.

import { enhanceCitySelect } from "../citypicker";
import { fmt1, formatarMesISO } from "../format";
import { renderTable, type RowDef } from "../table";
import { byId, setText, toggle } from "../ui";

interface MesRow {
  year_month: string;
  city_name: string;
  temp_max_media: number | null;
  temp_min_media: number | null;
  amplitude_media: number | null;
  precip_acumulada: number | null;
  dias_chuva: number;
  vento_maximo: number | null;
}
interface MensalAgg {
  city_name: string;
  temp_max_media: number | null;
  temp_min_media: number | null;
  amplitude_media: number | null;
  precip_acumulada: number | null;
  dias_chuva: number;
  vento_maximo: number | null;
}
interface MensalResponse {
  meses: MesRow[];
  subtotais: MensalAgg[];
  total_geral: MensalAgg | null;
}

let MIN_MES = "";
let MAX_MES = "";

function subtrairMeses(ym: string, n: number): string {
  const [ano, mes] = ym.split("-").map((s) => Number.parseInt(s, 10));
  if (ano === undefined || mes === undefined) return ym;
  const total = ano * 12 + (mes - 1) - n;
  const y = Math.floor(total / 12);
  const m = (total % 12) + 1;
  return `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}`;
}

function celulasAgg(rotuloMes: string, cidade: string, a: MensalAgg): string[] {
  return [
    rotuloMes,
    cidade,
    fmt1(a.temp_max_media),
    fmt1(a.temp_min_media),
    fmt1(a.amplitude_media),
    fmt1(a.precip_acumulada),
    String(a.dias_chuva),
    fmt1(a.vento_maximo),
  ];
}

function renderTabela(dados: MensalResponse): void {
  const tabela = byId<HTMLTableElement>("tabela-mensal");
  if (tabela === null) return;

  const subtotalPorCidade = new Map<string, MensalAgg>();
  for (const s of dados.subtotais) subtotalPorCidade.set(s.city_name, s);

  const mesesPorCidade = new Map<string, MesRow[]>();
  for (const m of dados.meses) {
    const lista = mesesPorCidade.get(m.city_name) ?? [];
    lista.push(m);
    mesesPorCidade.set(m.city_name, lista);
  }

  const rows: RowDef[] = [];
  for (const [cidade, meses] of mesesPorCidade) {
    for (const m of meses) {
      rows.push({
        cells: [
          formatarMesISO(m.year_month),
          cidade,
          fmt1(m.temp_max_media),
          fmt1(m.temp_min_media),
          fmt1(m.amplitude_media),
          fmt1(m.precip_acumulada),
          String(m.dias_chuva),
          fmt1(m.vento_maximo),
        ],
      });
    }
    const sub = subtotalPorCidade.get(cidade);
    if (sub !== undefined) {
      rows.push({ cells: celulasAgg("", `Subtotal — ${cidade}`, sub), variant: "subtotal" });
    }
  }
  if (dados.total_geral !== null) {
    rows.push({ cells: celulasAgg("", "Total Geral", dados.total_geral), variant: "total" });
  }

  const ok = renderTable(tabela, rows, {
    onEmpty: () => setText("mensal-msg", "Sem dados para o período selecionado."),
  });
  if (ok) toggle(byId("mensal-msg"), false);
}

async function carregarCaption(): Promise<void> {
  const resposta = await fetch("/api/v1/ref/daily-meta");
  if (!resposta.ok) return;
  const meta = (await resposta.json()) as { max_date: string | null };
  if (meta.max_date !== null) {
    const [a, m] = meta.max_date.split("-");
    setText("mensal-caption", `Dados disponíveis até ${m}/${a}`);
  }
}

async function atualizar(): Promise<void> {
  const select = byId<HTMLSelectElement>("filtro-cidades");
  const inicioInput = byId<HTMLInputElement>("filtro-inicio");
  const fimInput = byId<HTMLInputElement>("filtro-fim");
  if (select === null || inicioInput === null || fimInput === null) return;

  const cidades = [...select.selectedOptions].map((o) => o.value);
  const inicio = inicioInput.value;
  const fim = fimInput.value;

  toggle(byId("tabela-mensal"), false);
  if (cidades.length === 0) {
    setText("mensal-msg", "Selecione ao menos uma cidade para gerar o relatório.");
    return;
  }
  if (inicio === "" || fim === "") {
    setText("mensal-msg", "Selecione o mês inicial e o final.");
    return;
  }
  if (inicio > fim) {
    setText("mensal-msg", "O mês inicial é posterior ao final.");
    return;
  }

  const params = new URLSearchParams({ inicio, fim });
  for (const c of cidades) params.append("cidades", c);
  const resposta = await fetch(`/api/v1/relatorio-mensal/dados?${params.toString()}`);
  if (!resposta.ok) {
    setText("mensal-msg", `Erro ao carregar o relatório (HTTP ${resposta.status})`);
    return;
  }
  renderTabela((await resposta.json()) as MensalResponse);
}

export function initRelatorioMensal(): void {
  const select = byId<HTMLSelectElement>("filtro-cidades");
  const inicioInput = byId<HTMLInputElement>("filtro-inicio");
  const fimInput = byId<HTMLInputElement>("filtro-fim");
  if (select === null || inicioInput === null || fimInput === null) return;

  void carregarCaption();
  void (async () => {
    const [cidadesResp, metaResp] = await Promise.all([
      fetch("/api/v1/ref/cidades"),
      fetch("/api/v1/ref/daily-meta"),
    ]);
    if (cidadesResp.ok) {
      for (const c of (await cidadesResp.json()) as string[]) {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        select.appendChild(opt);
      }
    }
    enhanceCitySelect(select);

    if (metaResp.ok) {
      const meta = (await metaResp.json()) as { min_date: string | null; max_date: string | null };
      if (meta.min_date !== null && meta.max_date !== null) {
        MIN_MES = meta.min_date.slice(0, 7);
        MAX_MES = meta.max_date.slice(0, 7);
        for (const input of [inicioInput, fimInput]) {
          input.min = MIN_MES;
          input.max = MAX_MES;
        }
      }
    }
    fimInput.value = MAX_MES;
    const menos12 = MAX_MES !== "" ? subtrairMeses(MAX_MES, 11) : "";
    inicioInput.value = menos12 !== "" && menos12 < MIN_MES ? MIN_MES : menos12;

    select.addEventListener("change", () => void atualizar());
    inicioInput.addEventListener("change", () => void atualizar());
    fimInput.addEventListener("change", () => void atualizar());

    void atualizar();
  })();
}
