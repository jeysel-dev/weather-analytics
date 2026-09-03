# Footer de 3 colunas em todas as páginas

## Tipo
[ ] Nova feature  [x] Melhoria  [ ] Bug fix  [ ] Refatoração  [ ] Spec retroativa

## Status
[x] implementado — `layout.html` e `web/src/style.css` com o footer de
3 colunas + linha de rodapé. Ver **Adendo (2026-09-03)** para a licença
(MIT, `LICENSE` na raiz) e a remoção dos links `Privacidade` / `Termos de
Uso`.

## Resumo
O footer compartilhado (`layout.html`) troca a linha única (uma frase +
link Open-Meteo) por um footer de 3 colunas — Sobre / Navegação / Contato
— seguido de uma linha de rodapé com copyright e links de Privacidade /
Termos de Uso.

## Contexto
Handoff de 2026-09-03. O footer atual (`5923d72`, "navbar sem emoji +
footer compartilhado") é um `<footer class="site-footer"><p>…</p></footer>`
centralizado, `font-size: 12px`. Vive em `layout.html`, então já aparece
em todas as páginas. Markup e CSS vieram prontos no handoff; esta spec
registra a decisão sobre a lista de "Navegação".

## Requirements (EARS)

### Funcionais
- THE `layout.html` SHALL renderizar `<footer class="site-footer">` com:
  - `.site-footer__grid` com 3 blocos:
    1. `.site-footer__title` "Weather Analytics" + `.site-footer__desc`
       ("Painel de análise climática para Santa Catarina. Dados de 295
       municípios com insights em tempo real.");
    2. `.site-footer__title--caps` "Navegação" + `.site-footer__links`;
    3. `.site-footer__title--caps` "Contato" + `.site-footer__links`
       (`mailto:contato@jeysel.dev`, `https://jeysel.dev`).
  - `.site-footer__bottom` com `© 2026 Weather Analytics. Todos os
    direitos reservados.` e os links `Privacidade` / `Termos de Uso`
    (ambos `href="#"` — páginas ainda não existem).
- THE lista "Navegação" SHALL conter: Temperatura, Precipitação, Alertas,
  Cidades e **Relatório por Cidade** (link direto para `/relatorio-cidade`).
- THE footer SHALL aparecer em todas as páginas (consequência de estar em
  `layout.html` — nenhuma página tem footer próprio).

### Não-funcionais
- THE `.site-footer` e filhos SHALL usar só os tokens de `:root`
  (`--border`, `--bg`, `--text`, `--text-h`, `--accent`), de modo que o
  dark mode via `@media (prefers-color-scheme: dark)` funcione sem regra
  extra.
- THE `.site-footer__grid` SHALL ser `repeat(auto-fit, minmax(280px,
  1fr))` — colapsa para 1 coluna em telas estreitas sem media query
  dedicada.
- THE `.site-footer__grid` e `.site-footer__bottom` SHALL alinhar com o
  conteúdo (`max-width: 1126px; margin: 0 auto`), o mesmo do
  `.site-nav__inner`.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| "Navegação" = subconjunto fixo (4 páginas do handoff + Relatório por Cidade) | Gerar do `menu` de `layout.html` | O footer é uma lista curada, não um espelho da navbar; Início/Horário/Comparativo ficam de fora de propósito, pra manter a coluna curta. Markup estático = o footer bate exatamente com o handoff. |
| "Relatório por Cidade" como link direto `/relatorio-cidade` | Replicar o submenu "Relatórios" no footer | O footer não precisa de dropdown; a rota não mudou com a [[017-navbar-submenu-relatorios]]. Link direto é o comportamento certo aqui. |
| `Privacidade` / `Termos` como `href="#"` | Omitir até as páginas existirem | Vieram no markup do handoff; ficam como placeholder visível. Criar as páginas é fora do escopo. |
| Sem bloco `@media (prefers-color-scheme: dark)` novo | Redefinir cores do footer no dark | Todos os valores saem de tokens que já têm variante dark em `:root` (`--bg #0F172A`, `--border #334155`, `--text #CBD5E1`, `--text-h #F1F5F9`, `--accent #60A5FA`) — conferido por inspeção; o footer herda automático. |
| Remove o link Open-Meteo do footer | Manter em algum canto | A atribuição de dados não é requisito do novo layout; se necessário, entra depois na coluna "Sobre". |

### Componentes afetados
- `api/app/templates/layout.html` — bloco `<footer class="site-footer">`
  inteiro substituído.
- `web/src/style.css` — regra `.site-footer` (e `.site-footer a` /
  `:hover`) substituída pelo conjunto `.site-footer` +
  `.site-footer__grid` / `__title` / `__title--caps` / `__desc` /
  `__links` / `__bottom`.

## Casos de borda
- **Tela < ~600px** → `auto-fit` + `minmax(280px, 1fr)` colapsa as 3
  colunas em 1; `.site-footer__bottom` já é `text-align: center`.
- **Dark mode** → sem regra própria; validado por inspeção dos tokens
  (contraste ok: `--accent #60A5FA` sobre `--bg #0F172A`).
- **Páginas sem `data-page`** (nenhuma hoje) → o footer não depende de
  `page`, renderiza igual.
- **`Privacidade` / `Termos`** → `href="#"`; clicar só rola pro topo. É o
  placeholder esperado até as páginas existirem.

## Fora do escopo
- Criar as páginas de Privacidade e Termos de Uso.
- Gerar a coluna "Navegação" a partir da estrutura central de `PAGES`.
- Incluir Início / Horário / Comparativo na coluna "Navegação".
- Reintroduzir a atribuição Open-Meteo (pode entrar depois na coluna
  "Sobre").
- Qualquer mudança de conteúdo da `.site-footer__desc` além do texto do
  handoff.

## Referências de código
- `api/app/templates/layout.html` — `<footer class="site-footer">`.
- `web/src/style.css` — bloco "Footer (compartilhado em layout.html)";
  tokens em `:root` e no `@media (prefers-color-scheme: dark)` (linhas
  ~1–29).
- `web/src/style.css` — `.site-nav__inner` (`max-width: 1126px` — mesmo
  alinhamento reaproveitado no footer).

## Adendo — 2026-09-03 (licença MIT + remoção de Privacidade/Termos)

Replica o que o projeto irmão `compras-publicas-sc` fez no adendo da spec
035 de lá (que por sua vez portou o footer desta spec 019). Dois pontos que
a versão original deixou como placeholder/fora de escopo, resolvidos agora:

1. **Licença escolhida: MIT.** Adicionado `LICENSE` na raiz
   (`Copyright (c) 2026 Jeysel Pacheco Bastos` — de `git config user.name`)
   e seção "## Licença" no `README.md`. Motivo: MIT é a permissiva mais
   curta e reconhecida, sem copyleft (zero fricção pra quem baixa e estuda),
   e o GitHub passa a exibir o badge de licença. Escolha de licença é
   decisão à parte do layout — por isso ficou fora da spec original.

2. **Nuance do dado climático.** Os dados vêm do Open-Meteo, servidos pela
   API sob **CC BY 4.0** (`open-meteo.com/en/licence`, conferido 2026-09-03).
   Este repo só consome a API e **não relicencia** o dado — o `README`
   deixa explícito. O footer **não** reintroduz a atribuição Open-Meteo
   (isso continua fora de escopo, ver lista abaixo); a nota de licença dele
   é genérica ("Código e dados sob licença aberta") e a procedência
   detalhada vive no `README`.

3. **Links `Privacidade` / `Termos de Uso` removidos** do
   `.site-footer__bottom`. Eram `href="#"` (placeholder). O app não tem
   auth, formulário, sessão nem coleta de dado do visitante — uma política
   de privacidade seria vazia e "Termos de Uso" não se aplica a um painel
   de leitura de dado público. É **decisão, não pendência**: as páginas não
   serão criadas. A barra inferior fica só com a linha de copyright +
   licença.

4. No `.site-footer__bottom`, `© 2026 Weather Analytics. Todos os direitos
   reservados.` vira `© 2026 Weather Analytics · <a>Código e dados sob
   licença aberta</a>.`, onde o link aponta para
   `github.com/jeysel-dev/weather-analytics/blob/main/LICENSE`.

**CSS** (`web/src/style.css`, bloco `.site-footer__bottom`): removidas as
regras que só faziam sentido com dois `<p>` e vários links lado a lado —
`.site-footer__bottom a { margin-right: 16px }`,
`.site-footer__bottom a:last-child`, `.site-footer__bottom p:last-child
{ margin-top: 8px }`. Mantido/ajustado: `.site-footer__bottom a`
(`color: var(--accent); text-decoration: none`) + `a:hover`
(`text-decoration: underline`).

O item "Reintroduzir a atribuição Open-Meteo" em **Fora do escopo**
continua valendo — o dado é creditado no `README`, não no footer.

**Status:** implementado. Sem toque em dbt/dados. Deploy pelo fluxo normal
da API (CI → staging automático → promoção manual de produção).

## Ver também
- [[006-arquitetura-frontend-fastapi]] — `layout.html` compartilhado.
- [[017-navbar-submenu-relatorios]] — o submenu "Relatórios"; o footer
  linka `/relatorio-cidade` direto, sem dropdown.
- [[016-diagnostico-relatorio-cidade-producao]] /
  [[018-paginacao-ver-mais-alertas]] — mesma rodada de handoff.
- `compras-publicas-sc` `docs/specs/035-footer-tres-colunas/spec.md` —
  o adendo irmão (mesmas duas decisões; lá o dado é do Portal de
  Transparência SC em vez do Open-Meteo).
