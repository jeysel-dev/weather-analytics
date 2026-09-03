# Diagnóstico — Relatório por Cidade não reflete o redesenho em produção

## Tipo
[ ] Nova feature  [ ] Melhoria  [x] Bug fix (diagnóstico)  [ ] Refatoração  [x] Spec retroativa

## Status
[x] implementado — diagnóstico concluído; causa raiz confirmada. A correção
(promoção de imagem) é ação de deploy, **fora do escopo de código** e
pendente de autorização explícita do dono do repo.

## Resumo
O commit `9a7ca2e` (redesenho do Relatório por Cidade: linhas diárias +
subtotal por cidade + total geral) está em `main` e em staging, mas
`https://weather.jeysel.dev/relatorio-cidade` continua servindo a versão
anterior. Causa: **a imagem de produção está pinada num commit anterior a
`9a7ca2e`** — não é bug de código.

## Contexto
Origem: relato do dono do repo — "o comportamento em produção não bate com
o que foi implementado em `9a7ca2e`". Investigação feita em 2026-09-03,
sem alterar código, seguindo os passos do handoff (confirmar o commit da
mudança → conferir a tag de produção → verificar se a imagem contém o
commit → só então comparar respostas HTTP reais).

## Investigação

### 1. Em que commit a mudança entrou
`git log --oneline -- api/app/routers/relatorio_cidade.py
api/app/templates/relatorio-cidade.html web/src/pages/relatorio-cidade.ts`:

```
9a7ca2e feat(api): Relatório por Cidade — linhas diárias + subtotal + total geral
82e4836 feat(api): migra as 6 páginas restantes (007-009, 011-013)
```

`git show --stat 9a7ca2e` — 5 arquivos: `relatorio_cidade.py` (router),
`schemas/relatorio_cidade.py`, `templates/relatorio-cidade.html`,
`web/src/pages/relatorio-cidade.ts`, `web/src/style.css`. A mudança está
inteiramente em `9a7ca2e`.

### 2. Tag da imagem em produção
`deploy/k8s/api/overlays/production/kustomization.yaml`:

```yaml
images:
  - name: ghcr.io/jeysel-dev/weather-analytics/api
    newTag: a9065da
```

### 3. A imagem `a9065da` contém `9a7ca2e`?
Não. `a9065da` é **ancestral** de `9a7ca2e`:

```
$ git merge-base --is-ancestor a9065da 9a7ca2e && echo YES
YES

$ git log --oneline a9065da..9a7ca2e
9a7ca2e feat(api): Relatório por Cidade — linhas diárias + subtotal + total geral
3133691 fix(deploy): re-homeia weather-analytics-config pra api/base/
004d716 deploy(staging): atualiza imagem weather-analytics-api para a9065da [skip ci]
```

Produção roda uma imagem **3 commits atrás** do redesenho. Staging já foi
promovido — `deploy/k8s/api/overlays/staging/kustomization.yaml` tem
`newTag: 9a7ca2e` (commit `41fa306`, feito pelo passo de CI). O workflow
`build-and-push-api.yml` dispara em `api/**` e `web/**` (ambos tocados por
`9a7ca2e`), então a imagem `api:9a7ca2e` foi buildada e publicada no GHCR.

### 4. Confirmação por resposta HTTP real
`curl -s https://weather.jeysel.dev/relatorio-cidade` — trecho do `<thead>`
da tabela servido em produção **hoje**:

```html
<table id="tabela-relatorio" hidden>
  <thead>
    <tr>
      <th>Cidade</th>
      <th>Temp. Máxima (°C)</th>
      <th>Temp. Máxima Média (°C)</th>
      <th>Temp. Mínima (°C)</th>
      <th>Temp. Mínima Média (°C)</th>
      <th>Precip. Acumulada (mm)</th>
      <th>Vento Máximo (km/h)</th>
    </tr>
  </thead>
```

Isso é **byte a byte** o template em `git show a9065da:api/app/templates/relatorio-cidade.html`.
O template em `HEAD` (introduzido por `9a7ca2e`) tem uma coluna `Data` como
1ª e "Precip. (mm)" no lugar de "Precip. Acumulada (mm)":

```html
    <tr>
      <th>Data</th>
      <th>Cidade</th>
      ...
      <th>Precip. (mm)</th>
      <th>Vento Máximo (km/h)</th>
    </tr>
```

Produção não serve a coluna `Data` → produção não tem `9a7ca2e`.

### 5. Frontend (Vite) desatualizado na imagem?
Não é um vetor separado. O `Dockerfile` é multi-stage: o stage
`frontend-build` roda `npm run build` (Vite → `api/app/static`) e o stage
final copia `--from=frontend-build /api/app/static/`. Frontend e backend
viajam na **mesma imagem**, buildados do mesmo commit. Não existe deploy de
frontend isolado. A imagem `a9065da` tem o frontend de `a9065da`; a imagem
`9a7ca2e` tem o frontend de `9a7ca2e`. Promover a imagem carrega os dois
juntos.

## Causa raiz
**Promoção de imagem pendente.** Produção está em `a9065da`; o redesenho
está em `9a7ca2e` (3 commits à frente). Mesmo padrão do `e1f5334`
(promoção de `2620c14` → `a9065da` que corrigiu uma regressão de
"produção uma versão atrás"). Nenhum defeito no código de `9a7ca2e`.

## Requirements (EARS)
- WHEN o diagnóstico aponta "imagem de produção anterior ao commit da
  feature", the system SHALL registrar isso como causa de deploy (não de
  código) e **não** alterar código de aplicação.
- IF a correção for autorizada, the operador SHALL promover
  `deploy/k8s/api/overlays/production/kustomization.yaml` para uma tag que
  contenha `9a7ca2e` (a mais recente de `main` no momento da promoção),
  seguindo o mesmo procedimento do `e1f5334` — bump do `newTag` + commit
  `deploy(production): ...`, com nota no comentário do arquivo.
- THE promoção SHALL NÃO ser feita sem autorização explícita do dono do
  repo (registrado no handoff).

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Tratar como pendência de deploy, sem tocar código | Procurar bug em `relatorio_cidade.py` / `.ts` | A imagem de produção comprovadamente não contém o commit — não há o que corrigir no código. |
| Não promover a imagem nesta rodada | Bump imediato de `newTag` | Handoff proíbe push/promoção sem autorização explícita, mesmo com causa óbvia. |
| Promover para a tag mais recente de `main` (não fixar em `9a7ca2e`) | Fixar exatamente `9a7ca2e` | `9a7ca2e` pode não ser mais o HEAD quando a promoção acontecer; o que importa é que a tag **contenha** `9a7ca2e`. |

### Componentes afetados
- Nenhum arquivo de aplicação. A correção, quando autorizada, toca só
  `deploy/k8s/api/overlays/production/kustomization.yaml` (`newTag` +
  comentário) — e isso é uma ação de deploy separada desta spec.

## Casos de borda
- **Promoção acontece depois de mais commits em `main`** → promover para o
  SHA de topo de `main`; verificar antes com
  `git merge-base --is-ancestor 9a7ca2e <novo_sha>`.
- **CI não publicou `api:9a7ca2e` no GHCR** (workflow falho) → conferir a
  aba Actions / `docker manifest inspect ghcr.io/.../api:9a7ca2e` antes de
  promover; se faltar, um novo push em `main` re-dispara o build.
- **Time travel do BigQuery** — não se aplica: esta mudança é só de
  serving (router + template + TS), não toca dbt nem `weather_raw`.

## Fora do escopo
- Fazer a promoção da imagem de produção (ação de deploy, pendente de
  autorização).
- Automatizar a promoção staging → produção (segue manual e deliberada,
  ver comentário no `kustomization.yaml` de produção).
- Qualquer alteração no código de `9a7ca2e` — ele está correto.

## Referências de código
- `deploy/k8s/api/overlays/production/kustomization.yaml` — `newTag: a9065da`
  (a tag defasada) e o histórico de promoções manuais no comentário.
- `deploy/k8s/api/overlays/staging/kustomization.yaml` — `newTag: 9a7ca2e`
  (staging já promovido pelo CI).
- `.github/workflows/build-and-push-api.yml` — build da imagem em `api/**` /
  `web/**`, publicação no GHCR, bump automático só do overlay de staging.
- `Dockerfile` — multi-stage; frontend Vite embutido na mesma imagem da API.
- Commit `e1f5334` — precedente do mesmo tipo de correção (promoção
  pendente).

## Ver também
- [[013-pagina-relatorio-cidade]] — a página redesenhada por `9a7ca2e`.
- [[015-corte-streamlit]] — `a9065da`, a tag hoje em produção.
- [[017-navbar-submenu-relatorios]] / [[018-paginacao-ver-mais-alertas]] /
  [[019-footer-tres-colunas]] — as outras mudanças desta rodada de handoff.
