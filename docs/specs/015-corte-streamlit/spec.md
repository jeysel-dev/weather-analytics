# Corte do Streamlit — remoção do dashboard legado após a migração para FastAPI

## Tipo
[x] Corte / Remoção — spec final da sequência de migração aberta pela
[[006-arquitetura-frontend-fastapi]], que adiou explicitamente este passo
para "uma spec de corte própria, no fim da sequência".

## Status
[x] proposta — nenhum arquivo removido ou editado ainda. Esta spec fixa o
alvo do corte e as invariantes de validação; a execução é um passo
seguinte.

## Resumo
Remoção completa do Streamlit como sistema de serving do dashboard: o
código (`streamlit/`, 17 arquivos versionados), a infraestrutura de
deploy (`deploy/k8s/base/` + os overlays associados), o job de CI que
builda a imagem, e a atualização de toda a documentação que ainda
descreve o Streamlit como sistema ativo. A pré-condição posta pela
[[006-arquitetura-frontend-fastapi]] está cumprida: as 8 rotas do
dashboard (home + 7 páginas) já são servidas pelo FastAPI em produção
(commits `82e4836` — migração 7/7, `2a81817` — home nova, `28863ca` —
reskin visual por cima).

## Contexto
A migração desenhada pela [[006-arquitetura-frontend-fastapi]] foi
incremental de propósito: Streamlit e FastAPI conviveram no ar, uma
página por vez, com o roteamento entre os dois feito por `path` no
Ingress (repo `infra`, spec 090 de lá). Cada página migrada (specs
[[007-pagina-temperatura]] … [[013-pagina-relatorio-cidade]], mais a
camada [[014-camada-referencia]]) foi validada em produção antes da
seguinte.

Com as 8 rotas (`/`, `/temperatura`, `/precipitacao`, `/alertas`,
`/horario`, `/cidades`, `/comparativo`, `/relatorio-cidade`) servidas
pelo FastAPI, o processo Streamlit ficou reduzido a duas coisas:

1. **Fallback para as 7 URLs antigas em maiúscula** (`/Temperatura`,
   `/Precipitacao`, `/Alertas`, `/Cidades`, `/Comparativo`,
   `/Relatorio_por_Cidade`, `/Horario`) — o formato que o Streamlit
   gerava a partir dos nomes de arquivo em `streamlit/pages/`. Nenhum
   link do site atual aponta para elas; só chegam por bookmark ou
   histórico de quem usava o dashboard antigo.
2. **O endpoint `/_stcore/health`**, interno do Streamlit, sem consumidor
   externo conhecido.

Manter o container no ar não entrega mais nada — só duplica custo de
infra (um Deployment, um Service, uma NetworkPolicy, uma imagem publicada
a cada push que toca `streamlit/`, `pipeline/` ou `dbt/`) e a superfície
de manutenção (o Ingress hoje carrega 9 regras explícitas + um catch-all
+ um segundo Ingress de prioridade forçada, só para arbitrar entre os
dois serviços).

## Investigação
Inventário completo levantado nesta sessão (varredura direta do repo).

### `streamlit/` — 17 arquivos versionados
```
streamlit/
├── Dockerfile                     # imagem própria, single-stage python:3.11-slim, EXPOSE 8501
├── .dockerignore
├── .env.example
├── requirements.txt               # streamlit 1.54.0, google-cloud-bigquery, pandas, plotly, …
├── .streamlit/config.toml         # tema dark; server 0.0.0.0:8501 headless; CORS+XSRF on
├── app.py                         # Home: KPIs + linha de temperatura + mapa SC
├── pages/  (1_Temperatura.py … 7_Relatorio_Cidade.py)
├── utils/  (__init__.py, bigquery.py, labels.py)
└── deploy/weather-streamlit.service   # systemd unit LEGADO, já não é o deploy ativo
```
Não versionado (local só): `streamlit/.env`, `streamlit/.venv/`,
`__pycache__/`.

### CI — dois workflows, um deles precisa ser EDITADO, não deletado
- `.github/workflows/build-and-push-api.yml` — imagem da API + web;
  **não toca no Streamlit**, fica intacto.
- `.github/workflows/build-and-push.yml` — tem **dois jobs** no mesmo
  arquivo:
  - `build-and-push` — builda `context: streamlit` →
    `ghcr.io/jeysel-dev/weather-analytics:{sha}` + `:latest`, depois
    `kustomize edit set image` em `deploy/k8s/overlays/staging` e commita
    `[skip ci]`. **É o que sai.**
  - `build-and-push-pipeline` — builda `pipeline/Dockerfile` →
    `ghcr.io/jeysel-dev/weather-pipeline`. **Não tem relação com o
    Streamlit e roda o pipeline de ingestão de dado, diário, em produção
    — tem de ser preservado.**
  - Filtro de `paths` do workflow: `streamlit/**`, `pipeline/**`,
    `dbt/**`, o próprio arquivo. `streamlit/**` sai; os outros ficam
    (disparam o job do pipeline).

### `deploy/k8s/` — duas árvores kustomize independentes
```
deploy/k8s/
├── base/                       ← STREAMLIT — serviço "weather-analytics", :8501   [REMOVER inteiro]
│   ├── deployment.yaml         # image …/weather-analytics:latest; readOnlyRootFS; secret weather-analytics-sa-key
│   ├── service.yaml            # ClusterIP :8501
│   ├── configmap.yaml          # weather-analytics-config: BIGQUERY_*
│   ├── networkpolicy.yaml      # weather-analytics-egress-restrict (podSelector app: weather-analytics)
│   └── kustomization.yaml
├── overlays/                   ← overlays do Streamlit                              [REMOVER após migrar o ingress]
│   ├── staging/     kustomization.yaml + ingress.yaml
│   └── production/  kustomization.yaml + ingress.yaml + patch-browser-address.yaml
│                               #  patch injeta STREAMLIT_BROWSER_SERVER_ADDRESS — só faz sentido com Streamlit
└── api/                        ← FASTAPI — serviço "weather-analytics-api", :8000
    ├── base/ (deployment, service, configmap, networkpolicy, kustomization)
    └── overlays/
        ├── staging/     kustomization.yaml   ← SEM ingress.yaml hoje
        └── production/  kustomization.yaml   ← SEM ingress.yaml hoje
```

### Os dois `ingress.yaml` (staging e production idênticos, exceto `host`)
Estrutura atual de cada um:
- **9 regras `pathType: Prefix`** → `weather-analytics-api:8000`:
  `/horario`, `/api/v1`, `/static/api`, `/temperatura`, `/precipitacao`,
  `/alertas`, `/cidades`, `/comparativo`, `/relatorio-cidade`.
- **1 regra catch-all** `path: /` `Prefix` → **`weather-analytics:8501`**
  (Streamlit — pega tudo que sobra, inclusive as rotas antigas em
  maiúscula).
- **Um segundo `Ingress`** no mesmo arquivo (`weather-analytics-home-{env}`),
  com `traefik.ingress.kubernetes.io/router.priority: "100000"` e
  `path: /` `pathType: Exact` → `weather-analytics-api:8000` — a home
  nova; a prioridade forçada existe só para `Path(/)` vencer o
  `PathPrefix(/)` do catch-all no ranking do Traefik.

Tudo isso — as 9 regras, o catch-all e o Ingress de prioridade — só
existe para **arbitrar entre dois serviços concorrentes na mesma URL**.
Sem o Streamlit, não há concorrência: colapsa em uma regra
`Prefix "/"` → `weather-analytics-api:8000`.

### Documentação que descreve o Streamlit como sistema ativo
| Arquivo | Pontos |
|---|---|
| `README.md` | linha 3 (diagrama de topo), linha 12 (tabela de camadas), linha 23 (árvore de estrutura), linha 77 (tabela de credenciais), **linhas 84-198** (seção inteira "🎯 Streamlit — Dashboard em Produção"), linhas 201-208 (seção "CI/CD"). Bônus já quebrado: linhas 107 e 183-184 citam `streamlit/deploy/nginx-weather.conf`, arquivo que não existe mais. |
| `CLAUDE.md` | linha 11 (arquitetura em uma frase), linhas 131-148 (seção "Streamlit — filtros de data ancoram no dado real"), linhas 150-153 (bullet de deploy do Streamlit). A "regra de ouro" sobre `weather_raw`/marts **não** menciona Streamlit e permanece válida. |
| `docs/steering/weather-analytics.md` | linhas 52-57 (diagrama ASCII + `@st.cache_data`), linha 136 (lista de serviços), linha 138 (filtro de paths do CI), linha 153 (bullet de credenciais do dashboard), linhas 162-172 (seção "Cache do Streamlit"). |
| `docs/specs/007…014` | status `[x] proposta` apesar de concluídas e em produção. |
| `docs/archive/` (FEATURES.md, EPIC.md, USER-STORIES.md) | ~15 menções — **não tocar**, é arquivo histórico por definição. |

## Requirements (EARS)

### Funcionais — redirecionamento das URLs antigas
- THE system SHALL redirecionar cada uma das 7 URLs antigas do Streamlit
  para a rota FastAPI equivalente, com o mapeamento exato:

  | URL antiga | Rota nova |
  |---|---|
  | `/Temperatura` | `/temperatura` |
  | `/Precipitacao` | `/precipitacao` |
  | `/Alertas` | `/alertas` |
  | `/Cidades` | `/cidades` |
  | `/Comparativo` | `/comparativo` |
  | `/Relatorio_por_Cidade` | `/relatorio-cidade` |
  | `/Horario` | `/horario` |

- THE redirect SHALL ser um `RedirectResponse` do FastAPI com status
  **308 (Permanent Redirect)** — preserva o método HTTP e sinaliza
  permanência, o comportamento correto para links e bookmarks antigos.
- THE 7 redirects SHALL ser registrados em `api/app/main.py` (onde as
  rotas de página já são montadas), não em middleware do Traefik nem em
  config do repo `infra`.
- WHEN uma URL antiga chega com query string (ex.:
  `/Relatorio_por_Cidade?cidades=Florianopolis`), THE redirect SHALL
  preservar a query string intacta no `Location` header, anexada ao path
  novo.

### Funcionais — remoção de código e CI
- THE system SHALL remover por completo o diretório `streamlit/` (os 17
  arquivos versionados).
- THE system SHALL **editar** (não remover)
  `.github/workflows/build-and-push.yml`: remover o job `build-and-push`
  e retirar `streamlit/**` do filtro de `paths`.
- THE system SHALL preservar integralmente o job `build-and-push-pipeline`
  no mesmo arquivo — `streamlit/Dockerfile` deixa de existir, mas
  `pipeline/Dockerfile` continua sendo o contexto desse job, que é
  independente do corte.

### Funcionais — remoção de infraestrutura k8s
- THE system SHALL remover `deploy/k8s/base/` inteiro: `deployment.yaml`,
  `service.yaml`, `configmap.yaml` (`weather-analytics-config`),
  `networkpolicy.yaml` (`weather-analytics-egress-restrict`) e
  `kustomization.yaml` do Streamlit.
- THE system SHALL simplificar os dois
  `deploy/k8s/overlays/{staging,production}/ingress.yaml` para uma única
  regra: `pathType: Prefix`, `path: /` → `weather-analytics-api:8000`.
  Isso elimina o catch-all do Streamlit **e** o `Ingress`
  `weather-analytics-home-{env}` de prioridade forçada (spec 090 do
  `infra`), ambos existentes só para arbitrar entre dois serviços
  concorrentes. O redirect das URLs antigas (acima) já cobre o caso que o
  catch-all resolvia.
- THE `ingress.yaml` simplificado SHALL passar a viver em
  `deploy/k8s/api/overlays/{staging,production}/` (que hoje não têm
  `ingress.yaml`). A partir deste corte, o Ingress é responsabilidade
  exclusiva da árvore da API — não mais compartilhado com uma árvore de
  serviço que deixou de existir.
- THE system SHALL remover `deploy/k8s/overlays/` (a raiz, fora de
  `api/`) por completo depois de migrar o `ingress.yaml` — incluindo
  `patch-browser-address.yaml`, que só faz sentido com o Streamlit no ar.
- THE `deploy/k8s/api/overlays/{staging,production}/kustomization.yaml`
  SHALL passar a listar `ingress.yaml` em `resources`.

### Funcionais — documentação
- THE system SHALL atualizar `README.md`, `CLAUDE.md` e
  `docs/steering/weather-analytics.md` removendo toda referência ao
  Streamlit como sistema ativo (pontos listados na Investigação).
- WHERE um trecho descreve uma regra que continua válida sob a
  arquitetura FastAPI mas com o rótulo "Streamlit" (ex.: a ancoragem de
  filtros de data em `max_date()` em vez de `CURRENT_DATE()`, que migrou
  para a API mas continua sendo verdade), THE atualização SHALL preservar
  o conteúdo e corrigir só o rótulo / o local.
- THE system SHALL marcar as specs `006`–`014` com status
  **`implementado`** (estão como `proposta` apesar de concluídas e em
  produção).
- THE corpo desta spec SHALL declarar que ela **supersede parcialmente**
  as specs [[004-reescrever-readme]] e [[005-corrigir-secao-deploy-readme]]
  nos trechos de `README.md` que ambas fixaram sobre o Streamlit
  (estrutura de `streamlit/`, seção de deploy do dashboard, nota sobre
  `streamlit/deploy/*`).

### Não-funcionais
- THE remoção de infraestrutura (`deploy/k8s/base/`, o job de CI, os
  overlays) SHALL ser feita **de uma vez** — abordagem direta, sem fase
  intermediária de `replicas: 0` + validação + remoção. Decisão
  explícita: a pré-condição da [[006-arquitetura-frontend-fastapi]] (8
  rotas validadas em produção) já está cumprida com evidência real
  (commits + a validação registrada em cada uma das specs 007–014).
- THE corte NÃO SHALL incluir nenhuma ação sobre a service account GCP
  `weather-dashboard-sa` (`BigQuery Data Viewer`). **Bloqueio
  explícito:** a `weather-analytics-api` roda hoje (Opção B da pendência
  aberta desde a spec 090 do `infra`) com uma **cópia byte-a-byte** da
  chave dessa SA; desativá-la ou revogá-la quebraria a API em produção,
  sem nenhuma relação com o Streamlit ser desligado. Essa ação só fica
  segura depois que a SA dedicada `weather-analytics-api-sa` existir de
  fato — pendência separada, documentada em
  `infra:docs/steering/pendencias.md` e na spec 090 de lá.
- Validação pós-corte SHALL confirmar, com evidência real (não
  presumida):
  - as 8 rotas migradas (`/`, `/temperatura`, `/precipitacao`,
    `/alertas`, `/horario`, `/cidades`, `/comparativo`,
    `/relatorio-cidade`) continuam respondendo normalmente;
  - os 7 redirects respondem `308` com o `Location` header apontando para
    o path novo (e preservando query string quando houver);
  - nenhuma referência a `weather-analytics:8501` sobra em nenhum
    manifest aplicado (`kustomize build` dos overlays da API +
    `kubectl get` no cluster);
  - o pod e o Service `weather-analytics` (Streamlit) deixaram de existir
    no cluster, nos dois namespaces.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Redirect das URLs antigas no FastAPI (`api/app/main.py`) | Middleware / regra de redirect no Ingress (repo `infra`) | Mantém a lógica de rota versionada neste repo, sob a mesma disciplina de revisão já aplicada às 7 páginas migradas — não em config de infra revisada com outro rigor e em outro ciclo. |
| `308 Permanent Redirect` | `301` (também permanente) / `302` / `307` | `301` reescreve `POST`→`GET` em alguns clientes; `308` preserva o método e ainda sinaliza permanência. As URLs antigas eram `GET` de navegação, mas `308` é o mais correto e não custa nada. |
| Ingress colapsado numa regra `Prefix "/"` | Manter as 9 regras explícitas por página | Sem o Streamlit disputando o catch-all, não há mais motivo para rotear path a path — tudo vai para o mesmo serviço. Elimina a manutenção de "+1 linha por página nova" e o `Ingress`-home de prioridade forçada. |
| Ingress movido para `deploy/k8s/api/overlays/` | Deixar em `deploy/k8s/overlays/` e só editar o conteúdo | O diretório `deploy/k8s/overlays/` (raiz) é o overlay do *Streamlit*; mantê-lo só pelo Ingress deixaria uma árvore kustomize órfã de base. O Ingress agora é da API. |
| Corte direto, sem fase de scale-down | Faseado: `replicas: 0` primeiro, validar dias, remover depois | Pré-condição da [[006-arquitetura-frontend-fastapi]] já cumprida com evidência real; decisão explícita, dado o histórico de validação rigorosa em cada etapa anterior desta migração. Um scale-down intermediário só adiaria o mesmo risco. |
| `build-and-push.yml` editado, não deletado | Criar um workflow novo só para o pipeline e apagar o antigo | O job `build-and-push-pipeline` (imagem de ingestão) não tem relação com o corte; preservá-lo no lugar minimiza o diff e o risco de regressão no pipeline de dado, que roda diariamente em produção. |

### Componentes afetados
- `api/app/main.py` — **editado**. Registro dos 7 redirects `308` das
  URLs antigas (com preservação de query string).
- `streamlit/` — **removido** (17 arquivos).
- `.github/workflows/build-and-push.yml` — **editado**. Sai o job
  `build-and-push` e `streamlit/**` do filtro; fica o job
  `build-and-push-pipeline`.
- `deploy/k8s/base/` — **removido** (5 arquivos).
- `deploy/k8s/overlays/` — **removido** após migrar o `ingress.yaml` (6
  itens: 2× `kustomization.yaml`, 2× `ingress.yaml`,
  `patch-browser-address.yaml`, e os diretórios).
- `deploy/k8s/api/overlays/staging/` e `.../production/` — **editados**.
  Ganham `ingress.yaml` (versão colapsada) e a linha em `resources` do
  `kustomization.yaml`.
- `README.md`, `CLAUDE.md`, `docs/steering/weather-analytics.md` —
  **editados** (pontos na Investigação).
- `docs/specs/006` … `docs/specs/014` — **editados**. Status →
  `implementado`.
- [[006-arquitetura-frontend-fastapi]] — ganha um ponteiro para esta
  spec e a marca de "corte concluído" no lugar do "fora do escopo".

### Supersessão declarada
Esta spec supersede parcialmente:
- **[[004-reescrever-readme]]** — nos trechos do `README.md` que
  descrevem `streamlit/` na árvore de estrutura e o Streamlit na tabela
  de camadas.
- **[[005-corrigir-secao-deploy-readme]]** — na seção inteira "Streamlit
  — Dashboard em Produção" do `README.md`, incluindo a nota sobre
  `streamlit/deploy/*` como referência histórica. Depois deste corte,
  `streamlit/deploy/` deixa de existir e a nota perde objeto.

## Casos de borda
- **URL antiga com query string**
  (`/Relatorio_por_Cidade?cidades=X&inicio=Y`) → o redirect preserva a
  query string no `Location`, anexada ao path novo
  (`/relatorio-cidade?cidades=X&inicio=Y`).
- **`/_stcore/health`** (health check interno do Streamlit) → passa a
  responder `404`, sem redirect. Não tem consumidor externo conhecido; se
  algum monitor do `infra` apontar para ele, é ajuste do lado de lá
  (handoff).
- **URL antiga com capitalização diferente** (`/temperatura` já é a rota
  nova; `/TEMPERATURA` nunca existiu) → só os 7 paths exatos da tabela
  são redirecionados; qualquer outra coisa cai no `404` normal da API.
- **Referência externa à imagem `ghcr.io/jeysel-dev/weather-analytics`**
  (imagem antiga do Streamlit) em algum script / serviço fora deste repo
  → fora do escopo, mas SHALL ser sinalizado ao `infra` explicitamente no
  handoff.
- **`kustomize build` dos overlays da API depois do corte** → tem de
  resolver sem o `deploy/k8s/base/` do Streamlit; conferir que nenhum
  `kustomization.yaml` da árvore `api/` referencia a base errada.

## Fora do escopo
- **Qualquer ação sobre a service account `weather-dashboard-sa`** (ver
  bloqueio nos requisitos não-funcionais).
- **Criação da SA dedicada `weather-analytics-api-sa`** — pendência
  separada, já registrada em `infra:docs/steering/pendencias.md` e na
  spec 090 de lá.
- **Recursos que vivem só no repo `infra`** — ArgoCD `Application` do
  Streamlit, `deploy-streamlit-weather.sh`, entradas de cron,
  `Secret`/`ConfigMap` específicos, DNS. Listados no handoff, executados
  lá.
- **Qualquer mudança no pipeline de ingestão** (`pipeline/`, `dbt/`,
  `weather_raw`, marts) — não afetado por este corte.
- **`docs/archive/`** — arquivo histórico; menções ao Streamlit lá
  permanecem como registro.
- **Remoção do `airflow/` e `postgresql/`** (arquitetura anterior, já
  pausada) — não faz parte deste corte.

## Referências de código
- `streamlit/` — diretório inteiro a remover; 17 arquivos versionados
  (`Dockerfile`, `.dockerignore`, `.env.example`, `requirements.txt`,
  `.streamlit/config.toml`, `app.py`, `pages/1_Temperatura.py` …
  `7_Relatorio_Cidade.py`, `utils/__init__.py`, `utils/bigquery.py`,
  `utils/labels.py`, `deploy/weather-streamlit.service`).
- `.github/workflows/build-and-push.yml` — job `build-and-push`
  (Streamlit) sai; job `build-and-push-pipeline` fica; `streamlit/**` sai
  do filtro de `paths`.
- `deploy/k8s/base/` — `deployment.yaml`, `service.yaml`,
  `configmap.yaml`, `networkpolicy.yaml`, `kustomization.yaml` do
  Streamlit (serviço `weather-analytics`, `:8501`) — remover.
- `deploy/k8s/overlays/staging/ingress.yaml`,
  `deploy/k8s/overlays/production/ingress.yaml` — 9 regras `Prefix` +
  catch-all Streamlit + `Ingress` `weather-analytics-home-{env}` de
  `router.priority: 100000`; colapsar em 1 regra e mover para
  `deploy/k8s/api/overlays/`.
- `deploy/k8s/overlays/production/patch-browser-address.yaml` —
  `STREAMLIT_BROWSER_SERVER_ADDRESS`; remover.
- `deploy/k8s/api/overlays/staging/kustomization.yaml`,
  `.../production/kustomization.yaml` — hoje sem `ingress.yaml`; passam a
  incluí-lo.
- `api/app/main.py` — monta as rotas de página; ponto de registro dos 7
  redirects.
- `README.md` — linhas 3, 12, 23, 77, 84-198, 201-208 (e 107 / 183-184,
  referência quebrada a `nginx-weather.conf`).
- `CLAUDE.md` — linha 11, linhas 131-148, linhas 150-153.
- `docs/steering/weather-analytics.md` — linhas 52-57, 136, 138, 153,
  162-172.

## Ver também
- [[006-arquitetura-frontend-fastapi]] — spec-mãe da migração; adiou este
  corte explicitamente para "uma spec de corte própria, no fim da
  sequência". Esta é essa spec.
- [[007-pagina-temperatura]], [[008-pagina-precipitacao]],
  [[009-pagina-alertas]], [[010-pagina-horario]], [[011-pagina-cidades]],
  [[012-pagina-comparativo]], [[013-pagina-relatorio-cidade]] — as 7
  páginas migradas cujo estado em produção é a pré-condição deste corte;
  status a atualizar para `implementado`.
- [[014-camada-referencia]] — camada `/api/v1/ref/*` compartilhada; parte
  da mesma árvore `api/` que passa a ser a única.
- [[004-reescrever-readme]], [[005-corrigir-secao-deploy-readme]] —
  parcialmente superseditadas por esta spec nos trechos de `README.md`
  sobre o Streamlit.
- `infra` repo, spec **090**
  (`090-weather-analytics-api-roteamento-coexistencia`) — desenhou o
  roteamento por path Streamlit↔FastAPI durante a coexistência (o
  catch-all + `Ingress`-home de prioridade). Este corte substitui esse
  roteamento por uma regra única. Referência externa — outro
  repositório, sem wikilink.
