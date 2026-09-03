// Renderizador de tabelas de dados — padrão dos relatórios (spec 021).
//
// O `<thead>` fica no template (os rótulos são conteúdo, junto do resto do
// texto da página). Esta função lê os rótulos e a marca `.col-num` do
// cabeçalho e preenche o `<tbody>`: copia `data-label` para cada `<td>`
// (é o que habilita o layout de cartão do `.data-table` no mobile), aplica
// `.col-num` e marca as células vazias com `data-empty`.
//
// Sem agrupamento e sem paginação de propósito — o agrupamento fica coladinho
// no formato do payload de cada página; o botão "ver mais" continua na
// página, que só passa `opts.limit` e calcula quantas linhas restam.

export interface RowDef {
  /** Célula por coluna. `null` ou `"—"` = sem dado; `""` = em branco. */
  cells: (string | null)[];
  /** Linha de fecho — recebe a classe `row-subtotal` / `row-total`. */
  variant?: "subtotal" | "total";
}

export interface RenderTableOptions {
  /** Renderiza só `rows.slice(0, limit)` (paginação client-side). */
  limit?: number;
  /** Chamado quando `rows` está vazio (esconder botão, mostrar mensagem). */
  onEmpty?: () => void;
}

function isEmpty(cell: string | null): boolean {
  return cell === null || cell === "" || cell === "—";
}

/** Preenche o `<tbody>` de uma `<table class="data-table">`. Retorna `true`
 *  se renderizou ao menos uma linha. */
export function renderTable(
  table: HTMLTableElement,
  rows: RowDef[],
  opts: RenderTableOptions = {},
): boolean {
  const headCells = [...(table.tHead?.rows[0]?.cells ?? [])];
  const labels = headCells.map((th) => th.textContent?.trim() ?? "");
  const numeric = headCells.map((th) => th.classList.contains("col-num"));
  const tbody = table.tBodies[0] ?? table.createTBody();
  tbody.replaceChildren();

  if (rows.length === 0) {
    table.hidden = true;
    opts.onEmpty?.();
    return false;
  }

  table.hidden = false;
  const visiveis = opts.limit === undefined ? rows : rows.slice(0, opts.limit);
  for (const row of visiveis) {
    const tr = document.createElement("tr");
    if (row.variant !== undefined) tr.className = `row-${row.variant}`;
    row.cells.forEach((cell, i) => {
      const td = document.createElement("td");
      const vazio = isEmpty(cell);
      td.textContent = cell === null || cell === "—" ? "—" : (cell ?? "");
      if (vazio) td.dataset.empty = "";
      const label = labels[i];
      if (label !== undefined && label !== "") td.dataset.label = label;
      if (numeric[i] === true) td.className = "col-num";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
  return true;
}
