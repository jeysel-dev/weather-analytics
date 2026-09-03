# Ajustes nos relatórios novos (specs 022/023)

## Tipo
[ ] Nova feature  [x] Melhoria  [x] Bug fix  [ ] Refatoração  [ ] Spec retroativa

## Status
[x] implementado — 3 ajustes de revisão sobre os 5 relatórios das
specs 022/023. Ver **Adendo 1** no fim: filtro "Cidade" no
`/relatorio-chuva-acumulada` (2026-09-03).

## Resumo
Retorno da revisão dos relatórios recém-entregues:

1. **Botão "Compartilhar no WhatsApp" nos 5 relatórios novos**
   (`relatorio-mensal`, `-macrorregiao`, `-extremos`,
   `-chuva-acumulada`, `-horario`), no mesmo formato do
   `/relatorio-cidade` — link `wa.me/` com resumo + URL pública. Para o
   link ser útil, cada relatório passa a **guardar os filtros na query
   string** (deep link) e restaurá-los ao abrir. O botão do
   `/relatorio-cidade` e o `.share-button` global ganham o visual
   WhatsApp (verde + ícone).
2. **`/relatorio-mensal` — inputs de mês sem CSS.** O seletor usa
   `<input type="month">` e o `style.css` só estilizava
   `input[type="number"|"date"]`. Corrigido no seletor da `.filter-bar`.
3. **`/relatorio-chuva-acumulada` — paginação.** O ranking podia trazer
   ~295 linhas; passa a mostrar 10, com botão "Ver mais (N restantes)"
   que revela +10 por clique (mesmo padrão da spec 018), sem refazer o
   fetch.

## Contexto
- `web/src/pages/relatorio-cidade.ts` já tem o padrão de deep link
  (`lerURL`/`escreverURL` em `?cidades=&inicio=&fim=`) e de botão
  (`atualizarCompartilhar` → `wa.me/?text=`). Os 5 novos não tinham nem
  um nem outro (spec 022, "Fora do escopo": *estado na URL / compartilhar*
  — revertido aqui).
- `.share-button` (`style.css`) era um botão azul liso "Compartilhar".
- `.btn-mais-alertas` (spec 018) é o botão de "ver mais" das tabelas de
  alerta; `renderTable` já aceita `opts.limit` (spec 021).
- `.filter-field input` estilizado só para `number`/`date` em
  `style.css` (~355).

## Requirements (EARS)

### 1. Compartilhar + deep link
- THE `templates/_share_button.html` (novo) SHALL conter o markup do
  botão (`<a id="btn-compartilhar" class="share-button" target="_blank"
  rel="noopener" hidden>` com ícone SVG do WhatsApp + "Compartilhar no
  WhatsApp"); os 6 relatórios (`relatorio-cidade` + os 5 novos) SHALL
  incluí-lo via `{% include %}`.
- THE `web/src/share.ts` (novo) SHALL expor:
  - `lerURL()` → `URLSearchParams` da query string atual;
  - `escreverURL(params)` → `history.replaceState` (sem recarregar);
  - `compartilharWhatsapp(resumo, params)` → monta
    `https://wa.me/?text=<resumo + "\nVeja o relatório completo: " +
    https://weather.jeysel.dev<pathname>?<params>>` no `#btn-compartilhar`
    e remove o `[hidden]`;
  - `esconderCompartilhar()`.
- FOR cada um dos 5 relatórios novos, THE página SHALL, ao abrir, ler os
  filtros da URL (validando contra as listas de referência já
  carregadas) e aplicá-los aos controles; a cada mudança de filtro SHALL
  reescrever a URL.
- WHEN há um resultado renderizado (≥1 linha), THE página SHALL revelar o
  botão com um resumo específico; senão SHALL escondê-lo.
- Parâmetros por relatório:
  - mensal: `?cidades=A,B&inicio=YYYY-MM&fim=YYYY-MM`
  - macrorregião: `?dias=N`
  - extremos: `?dias=N&meso=…`
  - chuva-acumulada: `?dias=N&meso=…`
  - horário: `?city=…&days=N`
- THE `/relatorio-cidade` SHALL trocar o markup inline do botão pelo
  `{% include %}` (mesmo `id`/`class`; o `relatorio-cidade.ts` não muda —
  segue mexendo só em `href`/`hidden`).

### 2. CSS dos inputs de mês
- THE seletor `.filter-field input[type="number"], …[type="date"]` em
  `style.css` SHALL incluir `input[type="month"]`; idem a regra
  `color-scheme: light dark`.

### 3. Paginação de `/relatorio-chuva-acumulada`
- THE `relatorio-chuva-acumulada.html` SHALL ter
  `<button id="btn-mais-chuva" class="btn-ver-mais" hidden></button>`
  após a `.data-table`.
- THE `style.css` SHALL aplicar o estilo do "ver mais" também a
  `.btn-ver-mais` (lista de seletor junto de `.btn-mais-alertas`).
- THE `relatorio-chuva-acumulada.ts` SHALL manter `CHUVA_PAGE = 10`,
  `chuvaMax` (módulo, inicial 10) e `ultimoRows` (última resposta), e
  renderizar `renderTable(tabela, rows, { limit: chuvaMax })`.
- WHEN `ultimoRows.length > chuvaMax`, THE botão SHALL ficar visível com
  "Ver mais (N restantes)"; no clique SHALL fazer `chuvaMax += CHUVA_PAGE`
  e re-renderizar in-place (sem fetch).
- WHEN qualquer filtro muda, THE `chuvaMax` SHALL voltar a 10.

## Design

### Decisões de arquitetura
| Decisão | Alternativa | Motivo |
|---|---|---|
| Adicionar deep link aos 5 relatórios (revertendo o "fora do escopo" da spec 022) | Botão que compartilha só a URL-base + resumo em texto | Um link que abre a visão default é quase inútil para mensal/horário (cidade + período). O deep link torna o "Compartilhar" real. |
| `_share_button.html` via `{% include %}` | Repetir o `<a>` + SVG em 6 templates; ou CSS `background-image` data-URI | Um lugar só, markup legível (SVG inline), sem encoding de data-URI. |
| `web/src/share.ts` com helpers genéricos; cada página lê/escreve seus params | Um helper que serializa/deserializa um "estado" por página | Os filtros diferem por página (multi-cidade vs `dias` vs `city`); a leitura/escrita é 5–10 linhas por página e fica explícita. O compartilhado é só o `wa.me/` e o `replaceState`. |
| `relatorio-cidade.ts` não migra para `share.ts` | Unificar tudo | Funciona, tem formatação de mensagem própria (data PT, `formatarDataISO`). Só o template troca para o `{% include %}` (visual novo de graça). |
| `.share-button` global vira verde WhatsApp | Classe `--whatsapp` à parte | Todo uso do botão hoje é compartilhamento via WhatsApp; não há caso de "compartilhar genérico". |
| `.btn-ver-mais` como alias de `.btn-mais-alertas` no seletor | Renomear `.btn-mais-alertas` nos 2 templates + specs | Rename mexeria em código de alerta que funciona e em refs de spec; o alias custa 3 edições no `style.css` e deixa o nome novo disponível. |
| Paginação client-side (10 + "ver mais"), sem tocar no endpoint | `LIMIT` no SQL + parâmetro `offset` | O endpoint já devolve ≤295 linhas ordenadas; paginar no cliente é instantâneo e é o padrão da casa (spec 018). |

### Componentes afetados
- `api/app/templates/_share_button.html` — novo.
- `api/app/templates/relatorio-{mensal,macrorregiao,extremos,chuva-acumulada,horario}.html`
  — `{% include "_share_button.html" %}`; `relatorio-chuva-acumulada.html`
  ganha o `<button id="btn-mais-chuva">`.
- `api/app/templates/relatorio-cidade.html` — markup inline do botão →
  `{% include %}`.
- `web/src/share.ts` — novo.
- `web/src/pages/relatorio-{mensal,macrorregiao,extremos,chuva-acumulada,horario}.ts`
  — leitura/escrita de URL + botão; `relatorio-chuva-acumulada.ts` +
  paginação.
- `web/src/style.css` — `.share-button` (verde + ícone + `[hidden]`),
  `.share-button__icon`; `input[type="month"]` no seletor da filter-bar;
  `.btn-ver-mais` no seletor do "ver mais".

## Casos de borda
- **URL com cidade/meso inexistente** → ignorada na validação contra a
  lista de referência; filtro cai no default.
- **URL de mês fora de `[min, max]` do `daily-meta`** → ignorada; volta
  ao default (fim = mês do `max_date`, início = 12 meses antes).
- **Compartilhar antes de ter resultado** (nenhuma cidade / erro / vazio)
  → botão fica `hidden`.
- **`dias` na URL fora de 7–365 (ou 3–30 no horário)** → `clampDias`
  ajusta; a URL é reescrita com o valor clampado no 1º `atualizar`.
- **chuva-acumulada com ≤10 linhas** → botão nasce e continua `hidden`.
- **chuva-acumulada: trocar filtro depois de expandir** → volta a 10.
- **Mensagem do WhatsApp com acento/İ** → `encodeURIComponent` cobre;
  `wa.me` decodifica.
- **Deep link aberto sem JS** → a página renderiza o esqueleto; sem o TS
  os filtros não são aplicados (degradação graciosa, igual ao resto do
  site).

## Fora do escopo
- Migrar `relatorio-cidade.ts` para `share.ts`.
- Deep link / compartilhar nas páginas que não são relatório
  (`temperatura`, `alertas`, …).
- Paginação nos outros relatórios (mensal/macrorregião/extremos/horário
  têm poucas linhas por natureza).
- Botão de compartilhar para outros canais (só WhatsApp).
- Encurtador de URL.

## Referências de código
- `web/src/pages/relatorio-cidade.ts` — `lerURL`/`escreverURL`,
  `atualizarCompartilhar` (padrão replicado).
- `web/src/pages/alertas.ts` / `cidades.ts` — padrão "ver mais"
  (`RECENTES_PAGE`, `ultimoRecentes`, `renderTable(..., {limit})`).
- `web/src/table.ts` — `renderTable`, `opts.limit`.
- `web/src/style.css` — `.share-button`, `.btn-mais-alertas`,
  `.filter-field input`.

## Ver também
- [[022-relatorios-submenu]] / [[023-relatorio-horario]] — os relatórios
  ajustados.
- [[021-tabela-dados-padrao]] — `renderTable` / `opts.limit`.
- [[018-paginacao-ver-mais-alertas]] — padrão "ver mais".
- [[013-pagina-relatorio-cidade]] — o relatório cujo deep link + botão
  serviram de molde.

---

# Adendo 1 — filtro "Cidade" no `/relatorio-chuva-acumulada`

## Tipo
[x] Melhoria

## Status
[x] implementado

## Resumo
O ranking de chuva acumulada tinha só dois filtros (período em dias +
macrorregião). Adicionado um terceiro filtro opcional **Cidade**, que
restringe o ranking a um único município.

## Requirements (EARS)
- THE `relatorio-chuva-acumulada.html` SHALL ter um `.filter-field` com
  `<select id="filtro-cidade" name="cidade">` contendo a opção sentinela
  `<option value="Todas">Todas</option>`.
- THE `GET /api/v1/relatorio-chuva-acumulada/dados` SHALL aceitar um query
  param opcional `cidade`; quando ausente ou `"Todas"`, sem filtro; senão,
  validar contra a allowlist do seed `locations` (404 se desconhecido) e
  aplicar `AND city_name = @cidade`.
- THE filtro de cidade e o de macrorregião SHALL ser independentes
  (combinados com `AND`).
- THE `relatorio-chuva-acumulada.ts` SHALL popular o select via
  `/api/v1/ref/cidades`, transformá-lo em combobox pesquisável
  (`enhanceCitySelect`, spec 020), incluir `cidade` no deep link
  (`?dias=N&meso=…&cidade=…`) e restaurá-lo ao abrir.
- WHEN há um filtro de cidade ativo, THE mensagem do botão "Compartilhar"
  SHALL usar o nome da cidade como alvo (em vez da macrorregião / "Santa
  Catarina").

## Design
| Decisão | Alternativa | Motivo |
|---|---|---|
| `cidade_filter(city)` novo em `routers/ref.py`, espelho de `meso_filter` | Inline no router | Mesmo contrato (`("", {})` / cláusula + param nomeado), mesma allowlist cacheada (`require_cidade`); reusável pelos outros relatórios. |
| Combobox pesquisável (`enhanceCitySelect`) | `<select>` nativo como o de macrorregião | ~295 municípios — o nativo é inviável de navegar; é o padrão da casa desde a spec 020. O CSS `.filter-field .ts-wrapper` (single) já existia. |
| Filtros macrorregião + cidade independentes (AND) | Cidade sobrepõe/zera macrorregião | Menos código, comportamento previsível. Combinação inconsistente (cidade fora da macro) cai no "Sem dados para o período". |
| Sem paginação especial | — | Com cidade única o ranking tem 1 linha; com "Todas" a paginação de 10 + "Ver mais" (Adendo 3 da spec original) continua valendo. |

### Componentes afetados
- `api/app/routers/ref.py` — `cidade_filter()`.
- `api/app/routers/relatorio_chuva_acumulada.py` — param `cidade`, cláusula
  na query.
- `api/app/templates/relatorio-chuva-acumulada.html` — `.filter-field` de
  cidade.
- `web/src/pages/relatorio-chuva-acumulada.ts` — `popularCidades`,
  `enhanceCitySelect`, `atualizar(dias, meso, cidade)`, deep link
  `?cidade=`, alvo do compartilhamento.

## Casos de borda
- **`?cidade=` inexistente na URL** → ignorado (não está entre as
  `<option>`), filtro cai em "Todas".
- **Cidade + macrorregião que não a contém** → ranking vazio → "Sem dados
  para o período selecionado."
- **`cidade=<desconhecida>` direto na API** → 404 (`require_cidade`).
- **Trocar de cidade depois de expandir "Ver mais"** → `chuvaMax` volta a
  10 (já coberto pelo `atualizar`).

## Fora do escopo
- Filtro de cidade nos outros relatórios (macrorregião/extremos) — mesma
  `cidade_filter` disponível se quiserem depois.
- Multi-seleção de cidades neste ranking.

## Referências de código
- `api/app/routers/ref.py` — `meso_filter` (molde), `require_cidade`,
  `_cidades()` (cache).
- `web/src/citypicker.ts` — `enhanceCitySelect` (modo único).
- `web/src/pages/comparativo.ts` — enhance de `<select>` único + listener
  `change` no nativo (Tom Select sincroniza).
