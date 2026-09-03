# Navbar — "Relatório por Cidade" vira submenu "Relatórios"

## Tipo
[ ] Nova feature  [x] Melhoria  [ ] Bug fix  [x] Refatoração  [ ] Spec retroativa

## Status
[x] implementado — `MENU` agrupa filhos por `menu_group`; navbar renderiza
o submenu; `web/src/nav.ts` liga o toggle.

## Resumo
O item de topo "Relatório por Cidade" deixa de ser link direto e passa a
ser um submenu **"Relatórios"** com um filho — "Relatório por Cidade" na
mesma rota `/relatorio-cidade`. Estrutural: deixa pronto adicionar outros
relatórios ao mesmo grupo sem mexer no layout nem no JS.

## Contexto
Handoff de 2026-09-03. A navbar sai da "estrutura central de páginas"
(`PAGES` em `api/app/main.py`, spec 006) — uma tupla plana de `Page`,
renderizada por um `{% for item in menu %}` em `layout.html`. Não havia
conceito de submenu. Não há dropdown pré-existente no projeto para
reaproveitar (nem em `style.css`, nem em `web/`). O `docs/steering/weather-analytics.md`
**não** documenta a lista de itens da navbar — nada a atualizar lá.

## Requirements (EARS)

### Funcionais
- THE `Page` dataclass SHALL ter um campo opcional `menu_group: str | None`
  (default `None`). `None` = item de topo; uma string = rótulo do submenu
  ao qual o item pertence.
- THE página `/relatorio-cidade` SHALL declarar `menu_group="Relatórios"`.
- THE system SHALL construir `MENU` como uma tupla de itens onde cada item
  é uma `Page` (folha de topo) **ou** um `MenuGroup` (`label` + `children`
  não-vazio); itens com o mesmo `menu_group` entram num único `MenuGroup`.
- THE ordenação de `MENU` SHALL ser por `menu_position`; um `MenuGroup`
  SHALL ordenar pela `menu_position` do seu primeiro filho.
- WHEN um item de `MENU` é um `MenuGroup`, THE `layout.html` SHALL
  renderizar um `<button class="site-nav__sub-toggle" aria-haspopup="true"
  aria-expanded="false">` com o `label` + um `<ul class="site-nav__sub">`
  com um `<a>` por filho (mesmo `href`, mesmo `aria-current="page"` quando
  a página atual é aquele filho).
- WHEN o item é uma `Page`, THE `layout.html` SHALL renderizar o `<li><a>`
  como antes (sem regressão nos 7 itens de topo restantes).
- THE `web/src/nav.ts` SHALL expor `initNavSubmenu()` (chamado
  incondicionalmente em `main.ts`, como `initNavbarToggle`) que: alterna
  `aria-expanded` no clique do toggle; fecha no clique fora do
  `.site-nav__has-sub`; fecha no `Escape` e devolve o foco ao toggle.
- THE rota `/relatorio-cidade` e o deep-link `?cidades=&inicio=&fim=`
  SHALL continuar funcionando sem mudança (a URL não muda).

### Não-funcionais
- SHALL seguir o visual "enterprise" existente (slate-gray/azul, sem
  emoji, radius 2px, tokens `--accent`/`--border`/`--text`/`--text-h`).
  Sem biblioteca de dropdown, sem novo sistema de cor.
- O submenu SHALL ser acessível por teclado: `:focus-within` revela a
  lista mesmo sem JS; com JS, `aria-expanded` reflete o estado real.
- No mobile (`max-width: 720px`), dentro do drawer vertical, o submenu
  SHALL virar lista aninhada estática (recolhida até o toggle abrir),
  não um popover posicionado por `position: absolute`.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| `menu_group: str` na `Page` + `_build_menu()` monta os `MenuGroup` | Uma segunda estrutura à parte listando grupos e filhos | Mantém a fonte única da spec 006: continua impossível registrar rota sem item de menu. O agrupamento é derivado, não uma segunda lista pra desincronizar. |
| `MenuGroup` herda `menu_position` do 1º filho | Campo `menu_position` próprio no grupo | Menos um número pra manter coerente; o grupo naturalmente cai onde seus filhos cairiam. |
| Toggle em `nav.ts` (JS), não dropdown CSS-only | `:hover`/`:focus-within` puro | CSS-only não mantém `aria-expanded` honesto e não abre no toque (mobile). O `:focus-within` fica como reforço de teclado, o JS cuida do resto. |
| Estender `nav.ts` (já dono do comportamento da navbar) | Novo módulo `submenu.ts` | `nav.ts` já é o lugar do toggle do hambúrguer, click-outside e Escape — o submenu é o mesmo tipo de comportamento. |
| `{% if item.children is defined %}` pra discriminar no template | Campo `is_group` / tipo string no contexto | Jinja resolve atributo ausente como `Undefined` → `is defined` é falso pra `Page`. Idiomático e sem campo extra. |
| Submenu = lista aninhada estática no mobile | Popover absoluto também no mobile | O drawer mobile já é uma coluna vertical rolável; um popover absoluto dentro dele brigaria com o scroll. |

### Componentes afetados
- `api/app/main.py` — campo `Page.menu_group`; nova dataclass `MenuGroup`;
  `_build_menu()` no lugar do `sorted(PAGES, ...)`; `MENU` agora é
  `tuple[Page | MenuGroup, ...]`.
- `api/app/templates/layout.html` — `{% for item in menu %}` ganha o ramo
  `{% if item.children is defined %}` com o markup do submenu.
- `web/src/nav.ts` — `initNavSubmenu()`.
- `web/src/main.ts` — importa e chama `initNavSubmenu()`.
- `web/src/style.css` — bloco "Navbar: submenu" (`.site-nav__has-sub`,
  `.site-nav__sub-toggle`, `.site-nav__sub-caret`, `.site-nav__sub`) +
  ajustes no `@media (max-width: 720px)`.

## Casos de borda
- **Grupo com um só filho** (situação atual) → renderiza normal; o toggle
  abre uma lista de um item. É o estado esperado até chegar o 2º relatório.
- **Página atual é um filho do submenu** → `aria-current="page"` vai no
  `<a>` do filho; o toggle não recebe `aria-current` (não é um link).
- **JS desabilitado** → `:focus-within` ainda abre o submenu ao tabular
  até o toggle/itens; sem foco, fica fechado (aceitável — degradação
  graciosa, a rota continua acessível via `/relatorio-cidade` direto e
  pelo link do footer, ver [[019-footer-tres-colunas]]).
- **Resize desktop↔mobile com submenu aberto** → o CSS de cada breakpoint
  cuida da apresentação; `aria-expanded` persiste e continua coerente.
- **Escape com submenu fechado** → no-op (guardado por `isOpen()`).

## Fora do escopo
- Adicionar qualquer relatório novo ao submenu (só a estrutura).
- Mudar a URL de `/relatorio-cidade`.
- Submenu em qualquer outro item da navbar.
- Reordenar os itens de topo.
- Remover os campos `menu_icon` (não usados na navbar desde "navbar sem
  emoji", mas fora do escopo desta mudança).

## Referências de código
- `api/app/main.py` — `Page`, `PAGES`, `MENU`, `_build_menu`; comentário
  "Estrutura central de páginas (spec 006)".
- `api/app/templates/layout.html` — `<nav class="site-nav">` e o loop do
  menu.
- `web/src/nav.ts` — `initNavbarToggle` (padrão de click-outside/Escape
  reaproveitado) e `initNavSubmenu`.
- `web/src/style.css` — bloco "Navbar" e o `@media (max-width: 720px)`.

## Ver também
- [[006-arquitetura-frontend-fastapi]] — a "estrutura central de páginas"
  que esta spec estende.
- [[013-pagina-relatorio-cidade]] — a página que passou a viver sob o
  submenu.
- [[019-footer-tres-colunas]] — o footer, que linka `/relatorio-cidade`
  direto (sem dropdown).
- [[016-diagnostico-relatorio-cidade-producao]] — mesma rodada de handoff.
