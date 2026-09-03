// Página Detalhamento Horário (spec 023) — relatório puramente tabular.
//
// Tabula o dado horário que hoje só existe em gráfico em /horario (abas
// Temperatura & Umidade e Vento & Chuva): para um município + janela
// (3–30 dias), duas tabelas — extremos do período (com o instante) e
// resumo diário (com linha de total). Sem gráfico, sem estado na URL.

import { fmt1, formatarDataISO } from "../format";
import { compartilharWhatsapp, esconderCompartilhar, escreverURL, lerURL } from "../share";
import { renderTable, type RowDef } from "../table";
import { byId, setText, toggle } from "../ui";

interface ExtremoHorario {
  indicador: string;
  valor: number | null;
  quando: string | null;
}
interface DiaHorario {
  date: string | null;
  temp_min: number | null;
  temp_avg: number | null;
  temp_max: number | null;
  humidity_min: number | null;
  humidity_avg: number | null;
  humidity_max: number | null;
  precip_total: number | null;
  wind_max: number | null;
}
interface RelHorarioResponse {
  max_date: string | null;
  extremos: ExtremoHorario[];
  dias: DiaHorario[];
  total: DiaHorario | null;
}

function clampDias(raw: string | null): number {
  const n = Number.parseInt(raw ?? "", 10);
  if (Number.isNaN(n)) return 7;
  return Math.min(30, Math.max(3, n));
}

async function popularMunicipios(select: HTMLSelectElement): Promise<void> {
  const resposta = await fetch("/api/v1/horario/cidades");
  if (!resposta.ok) return;
  for (const cidade of (await resposta.json()) as string[]) {
    const opt = document.createElement("option");
    opt.value = cidade;
    opt.textContent = cidade;
    select.appendChild(opt);
  }
}

function celulasDia(rotuloData: string, d: DiaHorario): (string | null)[] {
  return [
    rotuloData,
    fmt1(d.temp_min),
    fmt1(d.temp_avg),
    fmt1(d.temp_max),
    fmt1(d.humidity_min),
    fmt1(d.humidity_avg),
    fmt1(d.humidity_max),
    fmt1(d.precip_total),
    fmt1(d.wind_max),
  ];
}

function esconderTabelas(): void {
  toggle(byId("tabela-extremos-horario"), false);
  toggle(byId("tabela-resumo-horario"), false);
}

async function atualizar(city: string, days: number): Promise<void> {
  const tExtremos = byId<HTMLTableElement>("tabela-extremos-horario");
  const tResumo = byId<HTMLTableElement>("tabela-resumo-horario");
  if (tExtremos === null || tResumo === null) return;

  toggle(byId("horario-rel-subtitulo"), false);
  toggle(byId("horario-rel-caption"), false);
  esconderTabelas();
  esconderCompartilhar();

  if (city === "") {
    escreverURL(new URLSearchParams());
    setText("horario-rel-msg", "Selecione um município para gerar o relatório.");
    return;
  }

  const params = new URLSearchParams({ city, days: String(days) });
  escreverURL(params);
  const resposta = await fetch(
    `/api/v1/relatorio-horario/dados?city=${encodeURIComponent(city)}&days=${days}`,
  );
  if (!resposta.ok) {
    setText("horario-rel-msg", `Erro ao carregar o relatório (HTTP ${resposta.status})`);
    return;
  }
  const dados = (await resposta.json()) as RelHorarioResponse;

  if (dados.max_date === null || dados.dias.length === 0) {
    setText(
      "horario-rel-msg",
      "Sem dados horários para este município no período selecionado.",
    );
    return;
  }

  toggle(byId("horario-rel-msg"), false);
  setText("horario-rel-subtitulo", `${city} — últimos ${days} dias`);
  setText("horario-rel-caption", `Dados disponíveis até ${formatarDataISO(dados.max_date)}`);

  renderTable(
    tExtremos,
    dados.extremos.map((e) => ({ cells: [e.indicador, fmt1(e.valor), e.quando] })),
  );

  const rows: RowDef[] = dados.dias.map((d) => ({
    cells: celulasDia(formatarDataISO(d.date), d),
  }));
  if (dados.total !== null) {
    rows.push({ cells: celulasDia("Total do período", dados.total), variant: "total" });
  }
  renderTable(tResumo, rows);

  compartilharWhatsapp(`Detalhamento horário — ${city}, últimos ${days} dias.`, params);
}

export function initRelatorioHorario(): void {
  const select = byId<HTMLSelectElement>("filtro-municipio");
  const diasInput = byId<HTMLInputElement>("filtro-dias");
  if (select === null || diasInput === null) return;

  const url = lerURL();
  const days = clampDias(url.get("days") ?? diasInput.value);
  diasInput.value = String(days);

  const rerender = (): void => void atualizar(select.value, clampDias(diasInput.value));
  select.addEventListener("change", rerender);
  diasInput.addEventListener("change", rerender);

  void popularMunicipios(select).then(() => {
    const cidade = url.get("city");
    if (cidade !== null && [...select.options].some((o) => o.value === cidade)) {
      select.value = cidade;
      void atualizar(select.value, clampDias(diasInput.value));
    }
  });
}
