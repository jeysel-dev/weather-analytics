// Formatação simples para tooltips do ECharts e captions. Esta página só
// lida com grandezas físicas (°C, %, mm, km/h) — sem moeda, sem
// Intl.NumberFormat.

export function fmt1(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(1);
}

// "2026-07-22" -> "22/07/2026" sem passar por Date (evita deslocamento de
// fuso). Já vem como string ISO do backend (campo `max_date`).
export function formatarDataISO(iso: string | null | undefined): string {
  if (iso === null || iso === undefined || iso === "") return "—";
  const [ano, mes, dia] = iso.split("-");
  if (ano === undefined || mes === undefined || dia === undefined) return iso;
  return `${dia}/${mes}/${ano}`;
}
