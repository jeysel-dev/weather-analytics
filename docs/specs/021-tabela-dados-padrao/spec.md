# Tabela de dados — padrão responsivo para relatórios

## Tipo
[ ] Nova feature  [x] Melhoria  [ ] Bug fix  [x] Refatoração  [ ] Spec retroativa

## Status
[x] implementado — `.data-table` (CSS) + `web/src/table.ts` (`renderTable`);
`relatorio-cidade` e `comparativo` migrados; `alertas` e `cidades`
(aba Alertas) migrados mantendo a paginação "ver mais".

## Resumo
A `/relatorio-cidade` renderiza numa `<table>` dentro de `.table-scroll`
(só `overflow-x: auto`): no desktop já nasce com barra de rolagem
horizontal (8 colunas × `white-space: nowrap`) e no celular é ilegível —
não há nenhum breakpoint para tabela no `style.css`. Como vêm mais páginas
de relatório, esta spec define **um padrão único**:

1. **`.data-table`** (evolui `.table-scroll`): 1ª coluna ancorada no scroll
   horizontal e, em ≤ 720 px, cada linha vira um **cartão rótulo/valor**
   (sem rolagem lateral).
2. **`web/src/table.ts` → `renderTable(table, rows, opts)`**: renderizador
   declarativo que preenche o `<tbody>`, copia `data-label` de cada `<th>`
   para o `<td>` correspondente (é o que habilita o cartão), marca
   `.col-num` e trata linha vazia / linhas de fecho (`row-subtotal`,
   `row-total`).

Junto vem um princípio de modelagem: **coluna = granularidade da linha**;
agregado que só faz sentido por grupo vai *dentro* da célula do subtotal,
não como coluna própria sempre vazia. Aplicado ao relatório: as colunas
"Temp. Máxima Média" / "Temp. Mínima Média" (hoje `—` em toda linha
diária) somem; a média entra na célula de "Temp. Máxima" / "Temp. Mínima"
das linhas de subtotal/total (`28.6 · méd 23.5`). 8 → 6 colunas.

## Contexto
- 4 tabelas hoje, todas `.table-scroll` + loop de `<tr>/<td>` bespoke no
  respectivo `web/src/pages/*.ts`, nenhuma com `data-label` nem breakpoint:
  `relatorio-cidade` (`#tabela-relatorio`, grupo + subtotal + total),
  `comparativo` (`#tabela-resumo`, 4 col, sem grupo), `alertas`
  (`#tabela-recentes`) e `cidades` aba Alertas (`#tabela-alertas`) — estas
  duas com paginação client-side "ver mais" (spec 018 / o mesmo padrão em
  `alertas.ts`).
- `style.css` bloco `/* ── Tabelas ── */` (`.table-scroll`, ~40 linhas).
  Tokens do projeto: `--bg`, `--bg-card`, `--border`, `--text`, `--text-h`;
  breakpoint único do site em `@media (max-width: 720px)`.
- Front sem framework de UI, bundle único (sem code splitting), 2 libs
  (`echarts`, `tom-select`). O template é esqueleto; o TS preenche.

## Requirements (EARS)

### `.data-table` (CSS)
- THE `.data-table` SHALL substituir `.table-scroll` (mesma aparência no
  desktop: borda, `overflow-x: auto`, cabeçalho, zebra de subtotal/total).
- THE 1ª coluna (`th`/`td:first-child`) SHALL usar `position: sticky;
  left: 0` para permanecer visível durante o scroll horizontal.
- THE colunas numéricas SHALL receber `.col-num` (`text-align: right`); o
  `<th>` correspondente SHALL ter `class="col-num"` no template.
- WHEN a viewport é ≤ 720 px, THE `.data-table` SHALL desligar o scroll
  horizontal e renderizar cada `<tr>` como um cartão: `<thead>` oculto,
  `<td>` em `display: flex` com o rótulo (`::before { content:
  attr(data-label) }`) à esquerda e o valor à direita.
- WHEN uma célula está vazia (`data-empty`), THE cartão mobile SHALL
  omití-la (`display: none`); no desktop ela renderiza `—` (ou vazia, na
  1ª coluna das linhas de fecho).
- THE linhas `.row-subtotal` / `.row-total` SHALL manter destaque visual
  (peso, fundo `--bg-card`, borda superior) nos dois layouts.
- THE CSS SHALL usar só tokens existentes — tema escuro sai de graça.

### `renderTable(table, rows, opts?)` (`web/src/table.ts`)
- THE `renderTable` SHALL ler os rótulos e a marca `.col-num` do
  `<thead><tr>` já presente no template (os rótulos ficam no HTML, junto
  do resto do texto estático da página — não migram para o TS).
- THE função SHALL aceitar `rows: RowDef[]`, onde `RowDef = { cells:
  (string | null)[]; variant?: "subtotal" | "total" }`.
- FOR cada célula, THE função SHALL: definir `data-label` a partir do
  `<th>` de mesmo índice; aplicar `.col-num` se o `<th>` a tiver; tratar
  `null` e `"—"` como "sem dado" (texto `—` + `data-empty`) e `""` como
  "em branco" (texto vazio + `data-empty`).
- WHEN `rows` está vazio, THE função SHALL esconder a `<table>`, chamar
  `opts.onEmpty?.()` e retornar `false`; senão exibir a `<table>`,
  renderizar `rows.slice(0, opts.limit ?? rows.length)` e retornar `true`.
- THE função SHALL substituir todo o `<tbody>` a cada chamada
  (`replaceChildren`) e não tocar em nenhum outro elemento da página.
- THE `renderTable` SHALL NOT conter lógica de agrupamento/subtotal nem de
  paginação — o agrupamento fica em cada página (poucas linhas, específico
  do payload); o botão "ver mais" continua na página, que só passa
  `opts.limit` e calcula "restantes".

### Migração
- THE `relatorio-cidade` SHALL passar a 6 colunas (Data, Cidade, Temp.
  Máxima, Temp. Mínima, Precip., Vento Máx.); as linhas de subtotal e
  total geral SHALL exibir a média dobrada na célula de temperatura
  (`{max} · méd {média}`), ou `—` quando não houver dado.
- THE `comparativo` `renderResumo` SHALL usar `renderTable` (sem
  `variant`, sem `limit`).
- THE `alertas.ts` `renderRecentes` e `cidades.ts` `renderAlertas` SHALL
  usar `renderTable` com `opts.limit = maxDisplayed` e `opts.onEmpty`
  para esconder o botão e mostrar a mensagem vazia; a contagem
  "restantes" e o texto do botão continuam calculados na página após um
  retorno `true`.
- THE endpoint `/api/v1/relatorio-cidade/dados` e o schema
  `SubtotalRow` SHALL permanecer inalterados (as duas médias continuam no
  payload — só deixam de ser coluna).

## Design

### Decisões de arquitetura
| Decisão | Alternativa | Motivo |
|---|---|---|
| `renderTable` lê o `<thead>` do template (rótulos + `.col-num`) | Passar `columns: ColumnDef[]` em TS e o helper montar o `<thead>` | Rótulo de coluna é conteúdo — fica no Jinja, junto do resto do texto da página, e continua traduzível/revisável sem abrir o TS. O helper só precisa que o `<thead>` exista. |
| Helper cell-level (recebe `string[]` já formatado) | Helper data-level (recebe linhas + `format`/`group`/`subtotal`) | Cada página formata com `fmt1`/`fmtN`/`fmtSigned`/ícone de severidade de um jeito próprio, e o agrupamento do relatório é 15 linhas coladas ao formato do payload. Um helper data-level genérico viraria um mini-framework. O ganho real (thead, `data-label`, `col-num`, vazio, classes de fecho) é todo cell-level. |
| Layout de cartão no mobile | Manter scroll horizontal; ou esconder colunas de baixa prioridade | Cartão é o padrão consagrado de tabela responsiva e não perde nenhum dado. Esconder coluna perde informação e ainda exige decidir prioridade por página. |
| Regras mobile num `@media` co-locado com `.data-table` | Somar ao `@media (max-width: 720px)` único no fim do arquivo | O padrão de tabela se lê melhor como um bloco só. O arquivo já tem `@media` espalhado (ex.: Tom Select). |
| Dobrar a média na célula de temperatura do subtotal | Manter as 2 colunas "Média"; ou coluna extra só no subtotal | Coluna que é `—` em ~95% das linhas é ruído que empurra a largura (a causa do scroll no desktop). O dado só existe por grupo → pertence à linha de grupo. |
| `.table-scroll` renomeada, sem alias | Manter `.table-scroll` como alias de `.data-table` | Só 4 templates usam; rename é 4 trocas e evita dois nomes para a mesma coisa. |
| `alertas`/`cidades` migrados agora (não só "toque leve") | Só trocar a classe e deixar o loop bespoke | `renderTable` com `opts.limit` absorve o `slice` das duas sem mexer na lógica de botão; deixa as 4 tabelas no mesmo caminho. |

### Componentes afetados
- **`web/src/table.ts`** — novo. `RowDef`, `RenderTableOptions`, `renderTable`.
- **`web/src/style.css`** — bloco `/* ── Tabelas ── */` reescrito como
  `.data-table` (desktop + `.col-num` + sticky 1ª coluna + `@media`
  mobile de cartão).
- **`api/app/templates/relatorio-cidade.html`** — `.table-scroll` →
  `.data-table`; `<thead>` de 8 → 6 `<th>`, numéricas com `class="col-num"`.
- **`api/app/templates/comparativo.html`**, **`cidades.html`**,
  **`alertas.html`** — `.table-scroll` → `.data-table`; `class="col-num"`
  nos `<th>` numéricos.
- **`web/src/pages/relatorio-cidade.ts`** — `renderTabela` reescrita sobre
  `renderTable`; interface `SubtotalRow`/`DiaRow` intactas; helper local
  `foldMedia`.
- **`web/src/pages/comparativo.ts`** — `renderResumo` sobre `renderTable`.
- **`web/src/pages/alertas.ts`** — `renderRecentes` sobre `renderTable`.
- **`web/src/pages/cidades.ts`** — `renderAlertas` sobre `renderTable`.

### `renderTable` — forma
```ts
export interface RowDef {
  cells: (string | null)[];              // null | "—" → sem dado; "" → em branco
  variant?: "subtotal" | "total";
}
export interface RenderTableOptions {
  limit?: number;                         // renderiza rows.slice(0, limit)
  onEmpty?: () => void;                   // chamado quando rows.length === 0
}
export function renderTable(
  table: HTMLTableElement,
  rows: RowDef[],
  opts?: RenderTableOptions,
): boolean;                               // true se renderizou ≥ 1 linha
```

## Casos de borda
- **Célula vazia na 1ª coluna (linhas de fecho)** → `""` → `data-empty`,
  desktop renderiza `<td>` vazio (sticky, fundo `--bg-card`), mobile
  omite.
- **`fmt1(null)` já devolve `"—"`** → `renderTable` trata a string `"—"`
  como "sem dado" (mesmo caminho de `null`).
- **`opts.limit` maior que `rows.length`** → `slice` devolve tudo; sem
  erro. **`rows` vazio com `limit` definido** → retorna `false` antes de
  fatiar.
- **Relatório com 1 cidade só** → 1 bloco de dias + 1 subtotal + total
  geral (o backend já manda `total_geral` mesmo com 1 cidade).
- **Subtotal sem dado no período** (`temp_maxima === null`) → `foldMedia`
  devolve `"—"`, não `"— · méd —"`.
- **Trocar de aba em `/comparativo` e voltar** → `renderResumo`
  re-renderiza do zero (`replaceChildren`), sem duplicar linhas.
- **`cidades.ts`: mudar só os dias após expandir** → `alertasMax`
  preservado (spec 018); `renderTable` recebe o `limit` corrente.
- **Tabela muito larga mesmo com 6 colunas** (nomes de cidade longos +
  fonte grande) → `overflow-x` continua ativo no desktop; a 1ª coluna
  sticky mantém a âncora. Mobile não rola (cartão).
- **`prefers-color-scheme: dark`** → sem cor literal no bloco novo; herda
  os tokens redefinidos no `@media` de tema.

## Fora do escopo
- Ordenação/filtro por coluna, resize de coluna, export CSV.
- Paginação server-side ou virtualização de linhas.
- Cabeçalho fixo no scroll **vertical** (exigiria `max-height` no
  container — decisão à parte).
- Biblioteca de grid da comunidade (Grid.js/Tabulator) — reavaliar só se
  surgir demanda de ordenação/busca em várias telas.
- Mudança no endpoint/SQL do relatório (as médias seguem no payload).
- Deep-link/URL, botão Compartilhar (inalterados na página de relatório).

## Referências de código
- `web/src/style.css` — bloco `/* ── Tabelas ── */` (será `.data-table`);
  `@media (max-width: 720px)` no fim; `.btn-mais-alertas` (padrão de botão
  da paginação).
- `web/src/pages/relatorio-cidade.ts` — `renderTabela`, `RRelatorioResponse`.
- `web/src/pages/comparativo.ts` — `renderResumo`.
- `web/src/pages/alertas.ts` / `web/src/pages/cidades.ts` — `renderRecentes`
  / `renderAlertas` (`slice(0, maxDisplayed)` + botão "ver mais").
- `web/src/format.ts` — `fmt1`, `fmtN`, `fmtSigned`, `formatarDataISO`.
- `api/app/routers/relatorio_cidade.py` / `api/app/schemas/relatorio_cidade.py`
  — payload de 3 partes (`dias` / `subtotais` / `total_geral`).

## Ver também
- [[013-pagina-relatorio-cidade]] — a página de referência do padrão.
- [[018-paginacao-ver-mais-alertas]] — a paginação "ver mais" que
  `renderTable` passa a acomodar via `opts.limit`.
- [[006-arquitetura-frontend-fastapi]] — template = esqueleto, TS preenche.
- [[012-pagina-comparativo]] / [[009-pagina-alertas]] /
  [[011-pagina-cidades]] — as outras tabelas migradas.
