# Seletor de município com busca (Tom Select)

## Tipo
[ ] Nova feature  [x] Melhoria  [ ] Bug fix  [ ] Refatoração  [ ] Spec retroativa

## Status
[x] implementado — os 6 `<select>` de cidade das páginas `/cidades`,
`/relatorio-cidade` e `/comparativo` viram comboboxes pesquisáveis;
`web/src/citypicker.ts` (`enhanceCitySelect`) instancia o Tom Select sobre
o `<select>` nativo já populado.

## Resumo
Escolher entre ~295 municípios num `<select>` nativo (sem busca) é o único
ponto de fricção real da UI. Cada `<select>` cujas `<option>` são nomes de
cidade passa a ser envolvido pelo [Tom Select](https://tom-select.js.org/)
— combobox vanilla, ~16 KB gz, com busca por digitação, e tags + botão de
remover no caso múltiplo. Nenhuma mudança de backend, de contrato de API
ou de estrutura de dados.

## Contexto
Pedido do usuário (2026-09-03). Antes disso foi avaliada a hipótese de
usar **Tailwind via CDN** para trazer componentes de combobox/data:
descartada (ver "Decisões de arquitetura") — o parecer é que Tailwind CSS
não traz componente JS nenhum (combobox/date picker vêm de Headless UI,
que exige React/Vue; ou do Tailwind Plus, pago), e a forma "Play CDN" é
marcada pela própria doc como imprópria para produção
("The Play CDN is designed for development purposes only, and is not
intended for production"). A necessidade real era só o seletor de cidade,
então a solução é uma lib de componente pontual, sem Tailwind.

Selects de cidade no app (todos populados via `/api/v1/ref/cidades` ou
`/api/v1/cidades/lista`, ambos `ORDER BY city_name`, e todos com um
listener de `change` que dispara o fetch da página):

| Página | `id` | Tipo | Origem das options |
|---|---|---|---|
| `/cidades` | `#filtro-municipio` | único | `/api/v1/cidades/lista` |
| `/relatorio-cidade` | `#filtro-cidades` | **múltiplo** (+ estado na URL) | `/api/v1/ref/cidades` |
| `/comparativo` | `#cmp-cidade-a` / `-b` / `-c` | único (×3) | `/api/v1/ref/cidades` |
| `/comparativo` | `#cmp-hist-cidade` | único | `/api/v1/ref/cidades` |

`#cmp-cidade-c` tem uma `<option value="—">` sentinela ("opcional"):
`comparativo.ts` só inclui a cidade C no fetch quando `c.value !== "—"`.

## Requirements (EARS)

### Funcionais
- THE `web/src/citypicker.ts` SHALL exportar
  `enhanceCitySelect(select: HTMLSelectElement, opts?): TomSelect`, que
  instancia o Tom Select sobre `select` e devolve a instância.
- THE `enhanceCitySelect` SHALL derivar único vs. múltiplo de
  `select.multiple` (`maxItems: 1` vs. `null`), e no caso múltiplo carregar
  o plugin `remove_button`.
- THE `enhanceCitySelect` SHALL usar `maxOptions: null` (listar os ~295
  municípios sem corte) e `create: false` (lista fechada — o backend já
  valida contra o seed `locations`).
- THE `enhanceCitySelect` SHALL NÃO definir `sortField` — as options já
  chegam em ordem alfabética do backend, e preservar a ordem do DOM mantém
  sentinelas (o `—` do `#cmp-cidade-c`) na posição original.
- WHEN uma página instancia o Tom Select, ela SHALL fazê-lo **depois** de
  inserir todas as `<option>` e de aplicar a seleção inicial no `<select>`
  nativo, para o widget herdar o estado correto.
- WHERE a seleção precisa ser mudada programaticamente após a instância
  (estado da URL em `/relatorio-cidade`), o código SHALL usar
  `picker.setValue(valor, true)` (silencioso) em vez de mexer em
  `option.selected`.
- THE listeners de `change` já existentes nos `<select>` SHALL continuar
  funcionando sem alteração — o Tom Select dispara `change` no elemento
  original a cada mudança de seleção.
- THE `#cmp-meso` (mesorregiões, ~6 itens) SHALL permanecer `<select>`
  nativo — não é lista de cidade e não tem fricção.

### Não-funcionais
- Dependência via `npm` (`tom-select`), entrando no bundle único do Vite
  como qualquer outro import — **sem** `<script>`/CSS de CDN.
- O CSS base do Tom Select SHALL ser importado em `web/src/main.ts`
  **antes** de `./style.css`; a re-tematização (tokens `--bg-card`,
  `--border`, `--accent`, `--text`, `--text-h`) SHALL viver em
  `style.css`, cobrindo tema claro e escuro sem regra de cor nova (só
  reuso dos tokens que já invertem no `@media (prefers-color-scheme:
  dark)`).
- Degradação graciosa: os atributos nativos (`multiple`, `size`) SHALL ser
  preservados no HTML — se o JS falhar, o `<select>` nativo ainda serve.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Tom Select (lib vanilla pontual) | Tailwind (CDN) + Headless UI / Flowbite / Preline | Tailwind CSS não tem componente JS; Headless UI exige React/Vue (o front é TS puro); Play CDN é "development only". O incômodo é só o seletor de cidade — não justifica um framework de CSS inteiro nem um 2º sistema de estilo. |
| `npm i` + import no bundle | `<script src="cdn…">` | Passa pelo Vite/manifest que já existe (spec 006), servido de `/static/api/`, sem origem externa nova (supply-chain/privacidade). |
| Envolver o `<select>` nativo já populado | Componente próprio que busca a lista sozinho | Zero mudança no fluxo de dados das páginas; o Tom Select mantém o `<select>` no DOM e sincroniza `option.selected` + evento `change`. |
| Build `tom-select/popular` (não `complete`) | `complete` (default do pacote) | `popular` traz `remove_button` sem `drag_drop`/`virtual_scroll`/`clear_button`, que não têm uso aqui (lista local de 295, sem async). |
| CSS base importado em `main.ts` antes de `style.css` | `@import` no topo de `style.css` | Ordem de cascata garantida (overrides depois da base) e resolução de path garantida (import JS via entry `./dist/*` do pacote). |
| Sem `sortField` | `sortField: {field:'text'}` | Backend já ordena; e ordenar por texto jogaria a `<option value="—">` do `#cmp-cidade-c` para o fim (code point do `—` > letras). |
| `#cmp-meso` fica nativo | Envolver também, por consistência | ~6 itens, cabem na tela; busca não agrega. |

### Componentes afetados
- `web/package.json` / `package-lock.json` — nova dep `tom-select`.
- `web/src/citypicker.ts` — **novo**: `enhanceCitySelect`.
- `web/src/main.ts` — `import "tom-select/dist/css/tom-select.css"` antes de
  `import "./style.css"`.
- `web/src/style.css` — bloco de re-tematização (`.ts-wrapper`,
  `.ts-control`, `.ts-dropdown`, `.option`, tags do modo múltiplo,
  `remove_button`, caret), usando os tokens existentes; `min-width` do
  `.ts-wrapper` dentro de `.filter-field` (200px / 240px no múltiplo,
  paridade com os selects nativos).
- `web/src/pages/cidades.ts` — `enhanceCitySelect(select)` logo após o
  loop que popula `#filtro-municipio`, antes do primeiro `carregar()`.
- `web/src/pages/relatorio-cidade.ts` — `enhanceCitySelect` (múltiplo)
  após popular `#filtro-cidades`; troca o loop `opt.selected = …` por
  `picker.setValue(urlState.cidades, true)`; `cidadesSelecionadas()`
  continua lendo `select.selectedOptions` (o Tom Select sincroniza).
- `web/src/pages/comparativo.ts` — `enhanceCitySelect` nos 4 selects de
  cidade, **depois** de `preencher()` + `selecionarSePresente()`, antes de
  registrar os listeners e do primeiro `carregarCidades()`.

## Casos de borda
- **JS falha / bundle não carrega** → `<select>` nativo (com `multiple`/
  `size`) continua utilizável.
- **`/relatorio-cidade` com `?cidades=` inválido** → já filtrado contra
  `CIDADES_VALIDAS` antes do `setValue`; valores desconhecidos que
  escapassem são ignorados pelo Tom Select.
- **`#cmp-cidade-c` = "—"** → opção normal na lista; `carregarCidades()`
  segue checando `c.value !== "—"`.
- **Busca sem resultado** → mensagem "Nenhum município encontrado" (via
  `render.no_results`), estilizada com `var(--text)`.
- **Tema escuro** → nenhuma cor literal nos overrides; todos os tokens já
  têm valor no bloco `@media (prefers-color-scheme: dark)` de `style.css`.
- **Container oculto** (filtros do Comparativo estão dentro de abas; a aba
  1 nasce visível, as outras `hidden`) → o Tom Select mede no primeiro
  foco/abertura, não na init; instanciar em painel oculto é ok.
- **Trocar de aba no Comparativo e voltar** → sem refetch nas trocas de
  aba (comportamento atual); o widget mantém a seleção.

## Fora do escopo
- Date pickers / seletor de datas (o `<input type="date">` nativo do
  `/relatorio-cidade` continua como está).
- `#cmp-meso` e qualquer `<select>` que não seja de cidade.
- Multi-seleção em páginas onde hoje é seleção única (ex.: transformar
  `#cmp-cidade-a/b/c` num único campo múltiplo).
- Busca server-side / carregamento assíncrono de options (a lista de 295
  cabe inteira no cliente).
- Persistir seleção entre reloads onde já não persiste (só
  `/relatorio-cidade` tem estado na URL, e isso não muda).
- Adotar Tailwind em qualquer forma.

## Referências de código
- `web/src/citypicker.ts` — `enhanceCitySelect`.
- `web/src/pages/cidades.ts` — `initCidades`, populamento de
  `#filtro-municipio`.
- `web/src/pages/relatorio-cidade.ts` — `initRelatorioCidade`,
  `cidadesSelecionadas`, `lerURL`/`escreverURL`.
- `web/src/pages/comparativo.ts` — `initComparativo`, `preencher`,
  `selecionarSePresente`.
- `web/src/style.css` — `.filter-field select` (padrão visual a espelhar)
  e o novo bloco `.ts-*`.
- `api/app/routers/ref.py` — `/api/v1/ref/cidades` (`ORDER BY city_name`).
- `api/app/main.py` — `_load_main_entry` (o CSS do Tom Select entra no
  `manifest.json` como parte do bundle e é servido via `main_css`).

## Ver também
- [[006-arquitetura-frontend-fastapi]] — bundle único Vite + manifest;
  por que a dep entra no build e não via CDN.
- [[013-pagina-relatorio-cidade]] — a página com estado na URL, o
  ajuste mais delicado.
- [[012-pagina-comparativo]] — 4 selects de cidade + a sentinela `—`.
- [[014-camada-referencia]] — `/api/v1/ref/cidades`, origem das options.
