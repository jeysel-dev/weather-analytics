# Correções de experiência mobile (gráficos, navbar, filtros)

## Tipo
[ ] Nova feature  [x] Melhoria  [x] Bug fix  [ ] Refatoração  [ ] Spec retroativa

## Status
[x] implementado — `web/src/style.css` (`.chart--dynamic`, `.chart--heavy`,
`.chart-mobile-note`, `.site-nav__toggle` 44×44px, breakpoint 480px dos
filtros, fix do submenu "Relatórios" em touch) + classes/nota nos 4
templates afetados.

## Resumo
Parecer de engenharia (sessão 2026-10-06) identificou um bug real de
responsividade e algumas lacunas menores no dashboard em telas ≤720px.
Esta spec corrige: (1) a altura dos gráficos de barra com altura dinâmica
sendo esmagada para 300px fixos no mobile; (2) os três heatmaps densos
(data × macrorregião/cidade), estruturalmente ilegíveis em tela estreita,
passam a ficar ocultos no mobile com uma nota explicativa pedindo acesso
via computador; (3) o alvo de toque do botão hambúrguer, abaixo do mínimo
recomendado; (4) o aperto dos campos de filtro (`select`/`input`) em
telas muito estreitas (≤480px, ex. iPhone SE); (5) — achado em produção
logo após o primeiro deploy desta spec — o submenu "Relatórios" do menu
mobile não abria em toque real (funcionava com clique de mouse, por isso
não foi pego na investigação inicial, que não testou com emulação de
toque).

### Addendum (2026-10-06): bug do submenu "Relatórios" em touch
Usuário reportou em produção: "ao clicar na opção Relatórios, nada é
exibido" no menu mobile. Reproduzido com Playwright + `hasTouch` (clique
de mouse simulado NÃO reproduz — daí não ter aparecido na investigação
original). Causa raiz: `web/src/style.css:201-204` tinha um fallback
`.site-nav__has-sub:focus-within .site-nav__sub { display: block; }` sem
restrição de dispositivo. Em touch, o navegador sintetiza
`touchstart → mousedown → focus → mouseup → click`; o `focus` do
`mousedown` já dispara `:focus-within` **antes do `click` ser
processado**, e como `.site-nav__sub` é `position: static` no mobile
(linha 808-814), isso causa reflow síncrono do drawer rolável
(`.site-nav__links`) entre o `mousedown` e o `mouseup` do mesmo toque. O
`click` sintético faz hit-test nas coordenadas originais do toque
*depois* do reflow e erra o botão — cai no conteúdo da página atrás do
menu, o que aciona o listener de "fechar ao clicar fora"
(`web/src/nav.ts:21-25`) e fecha o drawer inteiro em vez de abrir o
submenu. Corrigido restringindo o fallback `:focus-within` a
`@media (hover: hover) and (pointer: fine)` (dispositivos com mouse) —
no touch, só `aria-expanded` (JS, `initNavSubmenu`, `nav.ts:49`) decide a
visibilidade, sem conflito com o CSS.

### Addendum 2 (2026-10-06): bug persistiu em iPhone/Safari real
Usuário confirmou (purge no Cloudflare + aba anônima, descartando cache)
que o bug **persistia** mesmo com o fix do addendum 1 em produção
(confirmado via `kubectl exec` no pod e via `curl` através do Cloudflare —
o CSS/JS entregue era exatamente o corrigido). Comportamento relatado
mudou de descrição: "o menu continua aberto, mas sem a lista de
Relatórios" — ou seja, o drawer **não** fecha mais (o addendum 1 resolveu
essa parte), mas o submenu ainda não abre.

Nova investigação (Playwright, Chromium + WebKit, `page.tap()` real e
touch com tremor via CDP, usando o build exato de produção) **não
reproduziu** o bug em nenhum engine/emulação disponível. Hipótese mais
provável: WebKit do Playwright é um build desktop, sem a camada
UIKit/WKWebView do Safari iOS real — e Safari iOS tem a particularidade
de **não focar `<button>` em toque** (diferente de Chromium), então o
mecanismo exato do addendum 1 (`:focus-within` disparado por foco
síncrono) provavelmente nem se aplica lá; o fato de a correção do
addendum 1 não ter resolvido sugere uma causa diferente, não isolada com
as ferramentas disponíveis.

**Correção aplicada sem causa raiz 100% confirmada** (decisão deliberada
dado o custo de mais um ciclo especulativo): trocado o mecanismo de
abertura de seletor CSS de atributo+irmão
(`.site-nav__sub-toggle[aria-expanded="true"] + .site-nav__sub`) para o
mesmo padrão já usado — e comprovadamente funcional em produção — pelo
próprio drawer mobile: uma classe `.open` setada diretamente no elemento
via JS (`sub.classList.toggle("open", next)` em `nav.ts`, em vez de só
`aria-expanded` no botão). Isso elimina qualquer dependência de
combinador de irmão/seletor de atributo dinâmico — que pode ter
comportamento de reflow/recálculo de estilo inconsistente entre engines —
substituindo por exatamente o mecanismo que já funciona para
`.site-nav__links.open`. O `aria-expanded` continua sendo setado (a11y),
só deixou de ser a fonte de verdade do CSS. **Se o bug persistir mesmo
após este fix, o próximo passo é debug remoto via Safari Web Inspector
(cabo + Mac) — ver `web/src/nav.ts` e `web/src/style.css:185-222`.**

## Contexto
Investigação de código (sem alteração) cobriu CSS, os 14 gráficos ECharts,
tabelas, navegação e filtros em todas as páginas do dashboard
(`api/app/templates/*.html` + `web/src/pages/*.ts` + `web/src/style.css`).
Achados completos no parecer da sessão; resumo do que motiva cada item:

- `web/src/style.css:804` tem `.chart { height: 300px !important; }` dentro
  do único breakpoint do site (`@media (max-width: 720px)`). Esse
  `!important` vence a altura inline que três gráficos calculam em JS
  proporcionalmente à quantidade de linhas de dado — no mobile, qualquer
  lista longa (ranking de cidades, municípios afetados, heatmap de chuva)
  é espremida para 300px, resultando em barras/linhas sobrepostas.
- Dois desses três gráficos, além disso, são heatmaps de matriz densa
  (`chart-heatmap`, `chart-chuva`) — mesmo corrigindo a altura, uma matriz
  com muitas colunas (dias) não cabe de forma legível na largura de um
  celular. Um terceiro heatmap (`chart-anomalia`) tem o mesmo problema de
  largura mas altura fixa (não afetado pelo bug de altura).
- `.site-nav__toggle` (botão hambúrguer) é 36×36px
  (`web/src/style.css:95-105`) — abaixo do mínimo de 44×44px recomendado
  por WCAG 2.5.5 / Apple HIG para alvo de toque.
- `.filter-field select/input` tem `min-width: 200px` e
  `select[multiple]`/Tom Select tem `min-width: 240px`
  (`web/src/style.css:354-377`), sem ajuste para telas muito estreitas —
  em 320-360px de largura (menos o padding de `main`), o campo ocupa quase
  toda a tela.

Fora de escopo desta spec (avaliados no parecer, sem ação necessária):
tabelas (`.data-table`, já resolvida pela [[021-tabela-dados-padrao]]),
scroll horizontal de página (não existe — já verificado), largura dos
gráficos (já responsiva via `chartFor()` em `web/src/ui.ts:30-40`).

## Requirements (EARS)

### Altura dos gráficos de barra com altura dinâmica
- THE `chart-ranking` (precipitação, ranking de cidades) e `chart-municipios`
  (alertas, municípios afetados) SHALL manter a altura calculada em JS
  (`Math.max(...)` proporcional ao número de linhas) em qualquer largura
  de tela, incluindo ≤720px.
- THE regra `.chart { height: 300px !important; }` SHALL deixar de se
  aplicar a esses dois gráficos; os demais gráficos de altura fixa (que
  não dependem da quantidade de dados) SHALL continuar recebendo a altura
  reduzida de 300px no mobile, como hoje.

### Heatmaps ocultos no mobile com nota explicativa
- WHEN a viewport é ≤720px, THE gráficos `chart-anomalia` (temperatura),
  `chart-heatmap` (precipitação) e `chart-chuva` (comparativo) SHALL ficar
  ocultos (não renderizados visualmente; a instância ECharts pode
  continuar existindo em memória — só a exibição é afetada).
- WHEN esses gráficos estão ocultos, THE página SHALL exibir, no lugar,
  uma nota com o texto "Este gráfico tem melhor visualização em uma tela
  maior. Acesse por um computador para ver o mapa de calor completo."
- WHEN a viewport é >720px, THE nota SHALL ficar oculta e o gráfico
  SHALL renderizar normalmente (comportamento atual, sem mudança).
- THE legenda explicativa de cores já existente abaixo de
  `chart-anomalia` e `chart-chuva` (`.page-caption`) SHALL continuar
  visível só junto do gráfico (oculta quando o gráfico está oculto, já
  que se refere a cores que não estão sendo exibidas).

### Alvo de toque do menu mobile
- THE `.site-nav__toggle` SHALL ter no mínimo 44×44px de área clicável.

### Campos de filtro em telas muito estreitas
- WHEN a viewport é ≤480px, THE `.filter-field select/input[type=number|date|month]`
  SHALL reduzir `min-width` para no máximo 160px e o wrapper do Tom
  Select (`select[multiple]`) para no máximo 200px, mantendo a quebra de
  linha (`flex-wrap`) já existente em `.filter-bar`.

### Não-funcionais
- THE mudanças SHALL usar apenas CSS/classes (sem JavaScript novo) para
  mostrar/ocultar gráfico vs. nota — a instância ECharts não precisa saber
  que está oculta.
- THE CSS SHALL usar só tokens existentes (`--text`, `--border`,
  `--bg-card` etc.) — tema escuro continua funcionando sem ajuste
  adicional.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Excluir os 2 gráficos de altura dinâmica da regra `!important` via uma classe `.chart--dynamic` nova | Remover o `!important` geral e recalcular a altura mobile de todos os gráficos em JS | A troca por classe é uma mudança de 1 linha de CSS + 1 atributo de template por gráfico; recalcular em JS para todos os 14 gráficos é um escopo muito maior sem ganho adicional — os gráficos de altura fixa já ficam bem em 300px no mobile. |
| Ocultar heatmap + nota via CSS puro (classe `.chart--heavy` no container do gráfico + `.chart-mobile-note` no parágrafo, ambos resolvidos no `@media` existente) | Checar a largura da tela em JS e decidir render vs. mensagem | CSS puro não precisa de lógica nova em `web/src/pages/*.ts`, funciona mesmo se o JS falhar/atrasar, e segue o padrão já usado no projeto para mostrar/ocultar elementos por breakpoint (`.site-nav__toggle`, grids). |
| Nota explicativa como `<p class="chart-mobile-note">` sempre presente no HTML, oculta por padrão (`display:none`) e exibida só no `@media` mobile | `hidden` attribute + JS para alternar | `hidden` é removido/adicionado por JS normalmente no projeto (ex. `toggle()` em `ui.ts`) para estados de dados (vazio/erro) — aqui o estado é só de breakpoint, puramente visual, então CSS resolve sem tocar no JS existente. |
| Esconder `.page-caption` de cores junto com o gráfico (mesmo contêiner `display:none` quando aplicável) | Manter a legenda de cores visível mesmo com o gráfico oculto | A legenda ("vermelho = mais quente") não faz sentido sem o gráfico correspondente visível. |
| Botão hambúrguer: aumentar para 44×44px mantendo o ícone (20px) centralizado | Adicionar padding/área de toque invisível maior que o botão visual | Aumentar a própria caixa é mais simples e não precisa de truque de pseudo-elemento para a área de toque. |
| Breakpoint novo em 480px só para `.filter-field`/Tom Select, dentro do arquivo existente | Reusar o breakpoint único de 720px para isso também | 200/240px cabe razoavelmente até 720px (telas de tablet/phablet); só abaixo de ~480px (iPhone SE e afins) o aperto é realmente visível. Criar um segundo breakpoint pontual é mais simples que forçar todo o site a reavaliar o breakpoint único. |

### Componentes afetados
- `web/src/style.css` — bloco `/* ── Responsivo ── */`: nova classe
  `.chart--dynamic` excluída da regra de altura; novas classes
  `.chart--heavy`/`.chart-mobile-note` (oculta/exibe conforme breakpoint);
  `.site-nav__toggle` para 44×44px; novo `@media (max-width: 480px)` para
  `.filter-field`/Tom Select.
- `api/app/templates/precipitacao.html` — `chart-ranking` recebe
  `chart--dynamic`; `chart-heatmap` recebe `chart--heavy` + nota.
- `api/app/templates/alertas.html` — `chart-municipios` recebe
  `chart--dynamic`.
- `api/app/templates/temperatura.html` — `chart-anomalia` recebe
  `chart--heavy` + nota; `.page-caption` existente passa a ficar dentro do
  mesmo wrapper ocultável.
- `api/app/templates/comparativo.html` — `chart-chuva` recebe
  `chart--heavy` + nota; mesma mudança na `.page-caption`.
- Nenhum arquivo `.ts` precisa mudar — `chartFor()`/cálculo de altura
  dinâmica continuam idênticos; CSS é quem decide o que fica visível.

## Casos de borda
- **Gráfico oculto (`chart--heavy`) ainda recebe dados via `chartFor()`
  normalmente** → sem problema; ECharts só não é visível, não há custo
  relevante de renderizar fora da tela numa página que já carrega 3-4
  gráficos.
- **Rotacionar o celular para paisagem (largura &gt;720px em modo
  paisagem)** → sai do breakpoint mobile, heatmap volta a aparecer e a
  nota some — comportamento esperado (paisagem já dá espaço horizontal
  suficiente).
- **Tablet em retrato (~768px, &gt;720px)** → fora do breakpoint mobile;
  heatmap continua visível como hoje (esta spec não introduz breakpoint de
  tablet — ver "Fora do escopo").
- **`chart-ranking`/`chart-municipios` com poucas linhas (ex. 1 cidade)**
  → `Math.max(520/320, n*22)` já garante um mínimo generoso; sem mudança
  de comportamento, só deixa de ser sobrescrito no mobile.
- **Tema escuro (`prefers-color-scheme: dark`)** → `.chart-mobile-note`
  usa tokens de cor existentes, sem cor literal nova.

## Fora do escopo
- Breakpoint intermediário para tablet (768-1024px) — lacuna identificada
  no parecer, mas sem bug concreto associado; fica como melhoria futura
  separada.
- Reconfigurar `axisLabel`/rotação de categorias dentro dos heatmaps — com
  os três heatmaps ocultos no mobile, o problema de densidade de rótulos
  deixa de se manifestar nessa largura; manter como está no desktop.
- Área de toque do "×" de remover tag no Tom Select multi-select
  (achado menor, sem relato de uso real afetado).
- Qualquer mudança em tabelas, navegação (fora do tamanho do botão) ou
  estrutura de página — já cobertas/corretas conforme o parecer.

## Referências de código
- `web/src/style.css:95-105` — `.site-nav__toggle` (tamanho do botão).
- `web/src/style.css:354-377` — `.filter-field`/Tom Select (`min-width`).
- `web/src/style.css:444-450` — `.chart` (regra base, sem altura).
- `web/src/style.css:752-805` — `@media (max-width: 720px)` (bloco a
  editar; linha 804 é o bug da altura).
- `web/src/pages/precipitacao.ts:86` — altura dinâmica de `chart-ranking`.
- `web/src/pages/alertas.ts:150` — altura dinâmica de `chart-municipios`.
- `web/src/pages/comparativo.ts:165` — altura dinâmica de `chart-chuva`.
- `web/src/pages/temperatura.ts:155-194` — `chart-anomalia` (heatmap).
- `web/src/pages/precipitacao.ts:152-193` — `chart-heatmap` (heatmap).
- `web/src/pages/comparativo.ts:148-194` — `chart-chuva` (heatmap).
- `web/src/ui.ts:30-40` — `chartFor()` (resize por largura, inalterado).

## Ver também
- [[021-tabela-dados-padrao]] — padrão de breakpoint único (720px) e
  conversão de tabela em cartão mobile, referência de estilo para esta
  spec.
- [[009-pagina-alertas]] / [[008-pagina-precipitacao]] /
  [[007-pagina-temperatura]] / [[012-pagina-comparativo]] — páginas com os
  gráficos afetados.
