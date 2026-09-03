# Paginação "Ver mais" na tabela de Alertas (página Cidades)

## Tipo
[ ] Nova feature  [x] Melhoria  [ ] Bug fix  [ ] Refatoração  [ ] Spec retroativa

## Status
[x] implementado — `renderAlertas()` mostra 10 linhas por vez; botão
"Ver mais alertas (N restantes)" revela +10 por clique.

## Resumo
Na aba Alertas da página `/cidades`, a tabela passa a renderizar só as
primeiras 10 linhas. Um botão abaixo da tabela — "Ver mais alertas
(N restantes)" — revela mais 10 a cada clique, sem refazer a busca, e some
quando não sobra nenhuma.

## Contexto
Handoff de 2026-09-03. `web/src/pages/cidades.ts`, `renderAlertas(rows,
city, days)` hoje renderiza `rows` inteiro (o endpoint
`/api/v1/cidades/alertas` já limita a ≤100). Com janelas longas (até 365
dias) a tabela fica com dezenas de linhas empurrando o resto da página.
Esqueleto da aba em `api/app/templates/cidades.html`: `#msg-sem-alertas`
(antes da tabela no DOM), `.table-scroll > table#tabela-alertas`.

## Requirements (EARS)

### Funcionais
- THE `renderAlertas` SHALL aceitar um 4º parâmetro `maxDisplayed`
  (default `ALERTAS_PAGE = 10`) e renderizar apenas `rows.slice(0,
  maxDisplayed)`.
- THE módulo `cidades.ts` SHALL manter `let alertasMax` (estado local do
  módulo, inicial `ALERTAS_PAGE`) e `ultimoAlertas` (a última resposta de
  `/alertas` — `rows`, `city`, `days`) para re-render sem novo fetch.
- THE `cidades.html` SHALL ter um `<button id="btn-mais-alertas"
  class="btn-mais-alertas" hidden>` logo após o `.table-scroll` da aba
  Alertas.
- WHEN há mais linhas do que `maxDisplayed`, THE botão SHALL ficar visível
  com texto `Ver mais alertas (${restantes} restantes)`, onde
  `restantes = rows.length - maxDisplayed`.
- WHEN `restantes <= 0`, THE botão SHALL ficar `hidden`.
- WHEN o botão é clicado, THE system SHALL fazer `alertasMax += ALERTAS_PAGE`
  e chamar `renderAlertas(ultimoAlertas.rows, …, alertasMax)` — re-render
  in-place, sem refetch.
- WHEN não há alertas (`rows.length === 0`), THE system SHALL esconder
  tabela e botão e mostrar a mensagem "Nenhum alerta registrado…".
- WHEN o usuário troca de **município**, THE system SHALL resetar
  `alertasMax` para `ALERTAS_PAGE` (lista nova).
- WHEN o usuário muda só o **nº de dias**, THE system SHALL **preservar**
  `alertasMax` (mesma cidade, o usuário já revelou N linhas).
- THE texto do botão SHALL ser atualizado a cada render com a contagem
  `restantes` corrente (acessibilidade — o texto é a única indicação de
  quanto falta).

### Não-funcionais
- Estado apenas em `let` de módulo — sem estado global, sem estado na URL.
- Nenhuma chamada de rede no clique de "Ver mais".
- A posição de scroll SHALL ser preservada ao clicar "Ver mais": o handler
  só muta `<tbody>` (append de linhas) e o texto/`hidden` do botão, sem
  recolher/reexibir a seção nem reposicionar o layout acima da tabela.
- CSS SHALL usar os tokens existentes (`--accent`) e o mesmo `color-mix`
  já usado em `style.css`.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Reset de `alertasMax` só na troca de **município**, não na de **dias** | Resetar em qualquer mudança de filtro; ou nunca resetar | Ambos os filtros regeneram a lista, mas trocar de cidade é "lista nova, começa do topo"; ajustar a janela de dias é refinar a mesma lista — resetar aí perderia o que o usuário já expandiu. O handoff pede "não resetar toda vez que mexe em outro filtro" — o município é *o* filtro que define a lista. |
| Botão no HTML (esqueleto), `hidden` por default | Criar o `<button>` via JS | Consistente com o resto da página, que é esqueleto no template + preenchido pelo TS. |
| Botão depois do `.table-scroll` | "Antes da mensagem de nenhum alerta" (como no handoff) | No DOM real desta página `#msg-sem-alertas` vem **antes** da tabela; "depois da tabela" é a posição equivalente. Quando há 0 alertas, tabela e botão ficam escondidos e só a mensagem aparece. |
| Guardar `ultimoAlertas` no módulo | Reler do endpoint no clique | O endpoint já devolveu ≤100 linhas; paginar no cliente é instantâneo e não gasta request. |
| `maxDisplayed` como parâmetro com default | Ler `alertasMax` direto dentro de `renderAlertas` | O handoff pede o parâmetro explícito; e deixa `renderAlertas` testável/previsível sem depender do estado de módulo. |

### Componentes afetados
- `web/src/pages/cidades.ts` — constantes/estado `ALERTAS_PAGE`,
  `alertasMax`, `ultimoAlertas`; assinatura e corpo de `renderAlertas`;
  `carregar()` guarda `ultimoAlertas` e passa `alertasMax`; `initCidades()`
  separa o handler de `select` (reseta) do de `diasInput` (não reseta) e
  liga o clique de `#btn-mais-alertas`.
- `api/app/templates/cidades.html` — `<button id="btn-mais-alertas">` na
  aba Alertas.
- `web/src/style.css` — bloco `.btn-mais-alertas` (+ `:hover`, `[hidden]`).

## Casos de borda
- **≤10 alertas** → botão nasce `hidden`, nunca aparece.
- **Exatamente 10** → `restantes = 0` → `hidden`.
- **100 alertas** (teto do endpoint) → 10 cliques revelam tudo; no último,
  `restantes` chega a 0 e o botão some.
- **Trocar de aba e voltar** → não há refetch nas trocas de aba; a tabela
  mantém quantas linhas estavam visíveis (`alertasMax` intacto).
- **Trocar de município depois de expandir** → volta a 10 linhas para a
  cidade nova.
- **Mudar dias depois de expandir** → mantém as linhas já reveladas; se a
  lista nova for menor que `alertasMax`, `renderAlertas` mostra todas e
  esconde o botão (`Math.max(0, …)` evita "-3 restantes").
- **Clique em "Ver mais" sem `ultimoAlertas`** (nunca deve ocorrer — o
  botão só fica visível depois de um render com dados) → guardado por
  `if (ultimoAlertas !== null)`.

## Fora do escopo
- Paginação/"ver mais" em qualquer outra tabela (Relatório por Cidade,
  Alertas global).
- Paginação server-side ou aumento do teto de 100 linhas do endpoint.
- Persistir `alertasMax` entre reloads (URL/localStorage).
- Ordenação/filtro de colunas da tabela de alertas.
- "Ver menos" / recolher de volta.

## Referências de código
- `web/src/pages/cidades.ts` — `renderAlertas`, `carregar`, `initCidades`.
- `api/app/templates/cidades.html` — aba `#tab-alertas` (`#msg-sem-alertas`,
  `#tabela-alertas`, `#btn-mais-alertas`).
- `api/app/routers/cidades.py` — endpoint `/api/v1/cidades/alertas`
  (limite ≤100).
- `web/src/style.css` — `.share-button` (padrão de botão existente) e o
  novo `.btn-mais-alertas`.

## Ver também
- [[011-pagina-cidades]] — a página que recebe a paginação.
- [[009-pagina-alertas]] — a página de alertas global (não afetada).
- [[014-camada-referencia]] — `labels.ts` / `labels.py` (tradução de
  severidade usada nas linhas da tabela).
- [[016-diagnostico-relatorio-cidade-producao]] /
  [[017-navbar-submenu-relatorios]] / [[019-footer-tres-colunas]] — mesma
  rodada de handoff.
