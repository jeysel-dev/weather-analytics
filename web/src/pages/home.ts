// Página Home ("/") — KPIs reais buscados da camada de referência
// (spec 014), sem fabricar número nenhum. Falha de fetch = mantém "—",
// mesmo padrão de degradação das outras páginas.

import { formatarDataISO } from "../format";
import { setText } from "../ui";

function diasEntre(iso1: string, iso2: string): number {
  const a = new Date(`${iso1}T00:00:00Z`).getTime();
  const b = new Date(`${iso2}T00:00:00Z`).getTime();
  return Math.round((b - a) / 86_400_000);
}

export function initHome(): void {
  void (async () => {
    const [cidadesResp, mesosResp, metaResp] = await Promise.all([
      fetch("/api/v1/ref/cidades"),
      fetch("/api/v1/ref/mesorregioes"),
      fetch("/api/v1/ref/daily-meta"),
    ]);
    if (cidadesResp.ok) {
      setText("kpi-municipios", String(((await cidadesResp.json()) as string[]).length));
    }
    if (mesosResp.ok) {
      setText("kpi-mesorregioes", String(((await mesosResp.json()) as string[]).length));
    }
    if (metaResp.ok) {
      const meta = (await metaResp.json()) as { min_date: string | null; max_date: string | null };
      if (meta.min_date !== null && meta.max_date !== null) {
        setText("kpi-dias-historico", String(diasEntre(meta.min_date, meta.max_date)));
        setText("kpi-ultima-atualizacao", formatarDataISO(meta.max_date));
      }
    }
  })();
}
