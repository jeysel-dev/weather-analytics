// Seletor de município com busca (spec 020). Envolve um <select> nativo já
// populado com <option>s de cidades (ordem alfabética vinda de
// /api/v1/ref/cidades ou /api/v1/cidades/lista) num combobox pesquisável.
//
// Por que Tom Select e não Tailwind/Headless UI: o front é TS puro (sem
// framework) e o parecer da spec 020 descartou Tailwind via CDN. Tom Select
// é vanilla, ~16 KB gz, e entra no bundle único do Vite como qualquer outro
// import. O CSS base é importado em main.ts (antes de style.css) e
// re-tematizado lá com os tokens do projeto (claro/escuro).
//
// `tom-select/popular` = core + plugin `remove_button` (o X em cada tag do
// modo múltiplo), sem drag_drop/virtual_scroll/clear_button — nenhum tem
// uso aqui (lista local de 295, sem async).

import TomSelect from "tom-select/popular";

export interface CityPickerOptions {
  /** Placeholder do campo de busca. Default varia entre único e múltiplo. */
  placeholder?: string;
}

// Instancia o Tom Select sobre `select`. Chamar UMA vez, DEPOIS de inserir
// as <option>s e de aplicar a seleção inicial no <select> nativo — o widget
// herda esse estado. `select.multiple` decide único vs. múltiplo (com tags
// + botão de remover). Devolve a instância para o chamador ajustar a
// seleção via setValue() quando precisar (ex.: estado na URL do relatório).
export function enhanceCitySelect(
  select: HTMLSelectElement,
  opts: CityPickerOptions = {},
): TomSelect {
  const multi = select.multiple;
  return new TomSelect(select, {
    maxItems: multi ? null : 1,
    maxOptions: null, // ~295 municípios — listar todos, sem corte
    plugins: multi ? ["remove_button"] : [],
    placeholder:
      opts.placeholder ?? (multi ? "Buscar municípios…" : "Buscar município…"),
    // Lista fechada: o backend valida contra o seed `locations`.
    create: false,
    // Sem sortField de propósito: as options já chegam em ordem alfabética
    // do backend, e manter a ordem do DOM preserva sentinelas como a
    // <option value="—"> do #cmp-cidade-c (Comparativo).
    render: {
      no_results: () =>
        '<div class="no-results">Nenhum município encontrado</div>',
    },
  });
}
