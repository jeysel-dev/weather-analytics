# Arquitetura frontend — migração Streamlit → FastAPI + Jinja2 + Vite + ECharts

## Tipo
[x] Arquitetura (spec fundacional) — decisão estrutural que precede e
enquadra as 7 specs de página que virão depois.

## Status
[x] proposta — nenhum código de `api/` ou `web/` escrito ainda; esta spec
só fixa o alvo arquitetural e as invariantes que cada spec de página deve
respeitar.

## Resumo
Migração do dashboard `streamlit-weather` (Streamlit) para uma arquitetura
FastAPI + Jinja2 + Vite + TypeScript + ECharts, seguindo o padrão já
validado em produção no projeto irmão `compras-publicas-sc`. Migração
incremental, uma página por vez, dentro do mesmo repositório — o código
novo (`api/`, `web/`) convive com o código antigo (`streamlit/`) até o
corte final, que só acontece quando todas as 7 páginas estiverem migradas
e validadas em produção.

## Contexto
O dashboard Streamlit atual funciona e está em produção. A decisão de
migrar **não** partiu de um bug nem de um incidente — partiu de uma
avaliação de usabilidade, que identificou três limitações estruturais do
Streamlit para este caso de uso:

- **Responsividade mobile fraca.** O layout `layout="wide"` + sidebar de
  filtros do Streamlit não degrada bem em tela pequena; ajustar isso exige
  CSS customizado que o Streamlit não foi feito para acomodar.
- **Fragilidade do CSS customizado.** Qualquer ajuste visual além do que o
  tema do Streamlit oferece depende de injetar CSS por cima de classes
  internas não versionadas — quebra a cada atualização da lib.
- **Modelo de rerun de página inteira.** Cada interação (mudar um filtro,
  mover um slider) re-executa o script inteiro da página no servidor,
  refazendo todas as queries BigQuery mesmo quando só um gráfico mudou. O
  `@st.cache_data` mitiga, mas o modelo mental continua sendo "recarrega
  tudo".

Nenhuma dessas limitações é regressão — são propriedades do Streamlit que
deixaram de ser aceitáveis para onde o dashboard precisa ir.

## Investigação
Investigação conduzida sobre `compras-publicas-sc` (repo irmão, mesmo
autor, mesma infra), que já roda essa arquitetura em produção. Achados que
embasam esta spec:

- **Estrutura `api/` + `web/` no mesmo repo.** Backend Python em `api/`,
  frontend TypeScript em `web/`. Um repositório, dois toolchains.
- **`main.py` lê o manifest do Vite em nível de módulo, fail-fast.** No
  import do módulo da app, o backend abre o `manifest.json` gerado pelo
  build do Vite e resolve os nomes dos assets com hash. Se o manifest não
  existe ou está malformado, o import levanta `RuntimeError` e a app não
  sobe — não há fallback silencioso para assets sem hash.
- **Rotas de página geradas a partir de uma tupla central.** As rotas das
  páginas do dashboard não são escritas à mão uma a uma — há uma estrutura
  de dados única (tupla de páginas) e um laço que registra a rota de cada
  página no FastAPI. Adicionar uma página é adicionar uma entrada nessa
  estrutura.
- **Páginas SSR só do esqueleto.** O template Jinja2 de cada página
  renderiza só o HTML estrutural (containers, títulos, elementos-alvo de
  gráfico vazios). Nenhum dado do BigQuery entra no HTML no server.
- **Dado vem via `fetch()` do JS.** O módulo TypeScript da página faz
  `fetch()` contra endpoints `/api/v1/*` que devolvem JSON, e popula os
  elementos-alvo no cliente.
- **ECharts como lib de gráfico.** Única dependência de runtime do
  frontend.
- **CSS customizado único, sem framework.** Um arquivo de estilo próprio,
  sem Tailwind/Bootstrap.
- **Deploy via Dockerfile multi-stage.** Stage Node builda o frontend;
  imagem final só tem Python + os assets já buildados. GHCR + kustomize +
  Argo CD.
- **Métricas de escala do projeto de referência:** 13 páginas, ~1636
  linhas de TypeScript escritas à mão, 1 dependência de runtime no
  frontend (`echarts`), 5 dependências no backend.
- **Ponto onde esta spec diverge de propósito do projeto de referência:**
  em `compras-publicas-sc` o menu de navegação é hardcoded separado das
  rotas, o que já causou páginas "órfãs" de menu (rota existe, item de
  menu não). Aqui o menu deve sair da mesma estrutura que define as rotas.
- **Volume de dado é menor aqui.** `compras-publicas-sc` usa cursor
  server-side em streaming para endpoints de 76–95 mil linhas. O
  weather-analytics opera sobre 295 municípios e agregados diários —
  ordens de grandeza menos linhas por resposta.

## Requirements (EARS)

### Funcionais
- THE system SHALL servir cada página do dashboard atual (Temperatura,
  Precipitação, Alertas, Horário, Cidades, Comparativo, Relatório por
  Cidade) como uma rota FastAPI própria, renderizando um template Jinja2
  com o esqueleto HTML e os elementos-alvo de gráfico vazios — sem dado no
  HTML renderizado no servidor.
- THE system SHALL buscar dado do BigQuery via endpoints JSON próprios sob
  `/api/v1/*`, consumidos pelo JavaScript do lado cliente via `fetch()`.
  IF uma página precisa de dado para renderizar um gráfico, THE system
  SHALL obtê-lo por `fetch()` contra um endpoint `/api/v1/*`, nunca por
  server-side rendering do dado no template.
- THE system SHALL gerar o menu de navegação a partir da mesma estrutura
  de dados que define as rotas das páginas. WHEN uma rota de página é
  adicionada a essa estrutura, THE system SHALL exigir que a entrada
  carregue o rótulo/ícone de menu correspondente — ou uma marcação
  explícita de "sem item de menu". Não deve ser possível adicionar uma
  rota e esquecer o menu por omissão (o modo de falha observado em
  `compras-publicas-sc`).
- FOR cada página migrada, THE system SHALL preservar a paridade de
  filtros e de métricas já existente na versão Streamlit equivalente. O
  detalhamento dessa paridade (quais filtros, quais métricas, quais
  queries) é responsabilidade da spec individual de cada página, não
  desta.

### Não-funcionais
- THE build do frontend (Vite) SHALL gerar um `manifest.json` que o
  backend lê em nível de módulo. IF o manifest estiver ausente ou
  malformado no momento do import do módulo da app, THE system SHALL
  falhar explicitamente (`RuntimeError`), não recorrer a um fallback
  silencioso — mesmo padrão fail-fast de `compras-publicas-sc`.
- THE acesso ao BigQuery SHALL reutilizar o cliente síncrono já existente
  (`google-cloud-bigquery`, via um `utils/bigquery.py` adaptado do atual
  `streamlit/utils/bigquery.py`). As rotas FastAPI que consultam BigQuery
  SHALL ser síncronas (`def`, não `async def`), para rodarem no threadpool
  do Starlette sem bloquear o event loop. THE system SHALL NOT introduzir
  um cliente BigQuery assíncrono novo sem necessidade demonstrada por um
  endpoint concreto.
- THE system SHALL NOT usar cursor server-side em streaming (o padrão de
  `compras-publicas-sc` para volumes de 76–95 mil linhas) a menos que um
  endpoint específico demonstre necessidade real medida — o volume do
  weather-analytics (295 municípios, agregados diários) é
  significativamente menor.
- THE suíte de testes de API SHALL conseguir importar o módulo da app sem
  exigir um build real do frontend, via um stub de `manifest.json` criado
  em `conftest.py` (mesmo padrão de `compras-publicas-sc`, spec 033 de
  lá). O stub SHALL NOT sobrescrever um `manifest.json` real já presente
  no diretório de build.
- THE deploy SHALL seguir o pipeline já existente do weather-analytics
  (GHCR + kustomize + Argo CD), adaptando o `Dockerfile` para o padrão
  multi-stage: stage Node builda `web/`, imagem final só com Python + os
  assets buildados.
- THE filtragem por data em qualquer endpoint novo SHALL ancorar no dado
  real (`MAX(date)` da tabela consultada, via `max_date()`), não em
  `CURRENT_DATE()` — mesma regra que já vale em `streamlit/` (ver
  `CLAUDE.md`, seção "filtros de data ancoram no dado real").

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Lib de gráfico: **ECharts** | Manter Plotly (usado hoje no Streamlit); Recharts/D3 | Consistência com o padrão já validado em `compras-publicas-sc` — um só vocabulário de gráfico entre os dois dashboards irmãos, menos custo de contexto ao alternar entre repos. |
| Execução das rotas de API: **síncrona (`def`) em threadpool** | Reescrever o acesso a dado como `async` com um cliente BigQuery assíncrono | O cliente `google-cloud-bigquery` é síncrono e já está pronto/testado. Rotas `def` no FastAPI rodam em threadpool sem travar o event loop. Introduzir `async` aqui seria reescrever acesso a dado sem ganho demonstrado. |
| Streaming de resultado: **não, por padrão** | Cursor server-side em streaming, como em `compras-publicas-sc` | Aquele projeto precisou disso para respostas de 76–95 mil linhas. Aqui o volume (295 municípios, agregados diários) não justifica a complexidade. Reavaliar só se um endpoint concreto medir necessidade. |
| Menu de navegação: **gerado da mesma estrutura das rotas** | Menu hardcoded separado das rotas, como em `compras-publicas-sc` | Naquele projeto o menu separado das rotas produziu páginas órfãs de menu. Derivar menu e rota da mesma fonte torna esse modo de falha impossível por construção. |
| Localização do código novo: **`api/` e `web/` no mesmo repo, ao lado de `streamlit/`** | Repositório novo separado; branch de longa duração | Migração incremental página a página exige os dois códigos convivendo e sendo deployáveis em paralelo. Corte final (remoção de `streamlit/`) só depois que as 7 páginas estiverem em produção. |
| Estrutura de página: **1 rota + 1 template Jinja2 + 1 endpoint JSON + 1 módulo TS por página** | Template único parametrizado; SPA client-side routing | Mesmo padrão replicável de `compras-publicas-sc` — cada página é uma unidade pequena e isolada, o que torna a migração incremental (uma spec por página) natural. |

### Componentes afetados
- `api/` — novo. App FastAPI: `main.py` (lê o manifest do Vite em nível de
  módulo, fail-fast), estrutura central de páginas (tupla → rotas + menu),
  templates Jinja2 (esqueleto por página), routers `/api/v1/*` (endpoints
  JSON, rotas síncronas), `utils/bigquery.py` (adaptado do de `streamlit/`),
  `conftest.py` (stub de manifest para os testes).
- `web/` — novo. Frontend Vite + TypeScript: um módulo TS por página,
  `echarts` como única dependência de runtime, um arquivo de CSS
  customizado sem framework, config do Vite gerando `manifest.json`.
- `streamlit/` — inalterado nesta migração; permanece em produção servindo
  as páginas ainda não migradas. Removido só no corte final (fora do
  escopo desta spec).
- `Dockerfile` / imagem de deploy — adaptado para multi-stage (stage Node
  builda `web/`, imagem final só Python). Pipeline GHCR + kustomize + Argo
  CD reaproveitado.

## Casos de borda
- **Manifest do Vite ausente/malformado no boot** → falha explícita
  (`RuntimeError`) no import do módulo da app, não fallback para assets
  sem hash.
- **Testes de API rodando sem build de frontend** → stub de
  `manifest.json` criado em `conftest.py`; o stub nunca sobrescreve um
  `manifest.json` real já presente no diretório de build.
- **Página migrada com paridade de filtro/métrica divergente do Streamlit
  original** → resolvido caso a caso na spec individual de cada página,
  não aqui.
- **Rota adicionada sem item de menu** → a estrutura central de páginas
  exige rótulo de menu ou marcação explícita de omissão; não há caminho
  silencioso para uma página órfã de menu.
- **Filtro de data caindo numa janela sem dado** (pipeline atrasado) →
  endpoints novos ancoram em `max_date()`, mesma proteção que já existe
  no Streamlit.

## Fora do escopo
- **Remoção do diretório `streamlit/`.** Só acontece depois que as 7
  páginas estiverem migradas e validadas em produção — vira uma spec de
  corte própria, no fim da sequência.
- **Especificação de cada página individual.** Cada uma vira spec própria
  (7 specs, a criar em sequência — ver "Ver também"). Esta spec só fixa o
  esqueleto arquitetural comum.
- **Autenticação / autorização.** O dashboard é público; esta migração
  não muda nada nesse quesito.
- **Página `home` (mapa + KPIs + tendência).** Hoje é código inline em
  `streamlit/app.py`, não uma página em `streamlit/pages/`. Se for
  migrada, entra como uma 8ª spec de página; não está entre as 7 desta
  sequência.
- **Reescrita de models dbt ou mudança em `weather_raw`.** A migração
  consome as mesmas marts que o Streamlit consome hoje.
- **Roteamento entre Streamlit e FastAPI durante a coexistência.**
  Enquanto nem todas as 7 páginas estiverem migradas, o dashboard tem
  dois processos servindo partes diferentes da mesma URL pública
  (weather.jeysel.dev) — Streamlit e FastAPI são frameworks de serving
  distintos, não convivem no mesmo processo nem na mesma porta. Decidir
  qual rota vai pra qual serviço (Ingress/nginx no repo infra,
  provavelmente por path) é responsabilidade do infra, não desta spec
  — mas é um BLOQUEIO REAL, não um detalhe cosmético: assim que a
  primeira página migrada estiver pronta pra ir pra produção, esse
  roteamento precisa existir, ou a página não é alcançável. Levar essa
  necessidade ao chat do infra antes (ou junto) do primeiro deploy de
  página migrada, não depois.

## Referências de código
- `streamlit/app.py` — `st.navigation([...])` com as 7 páginas + home; é a
  fonte do inventário de páginas a migrar e da estrutura de menu atual
  (hardcoded — o que esta spec quer evitar no destino).
- `streamlit/pages/1_Temperatura.py` … `streamlit/pages/7_Relatorio_Cidade.py`
  — as 7 páginas a migrar; cada spec de página parte do arquivo
  correspondente.
- `streamlit/utils/bigquery.py` — cliente BigQuery síncrono, `query()`,
  `tbl()`, `max_date()`, `min_date()`, `format_temp()`; base do
  `api/utils/bigquery.py` adaptado.
- `compras-publicas-sc` (repo irmão) — implementação de referência
  completa do padrão FastAPI + Jinja2 + Vite + ECharts: estrutura
  `api/` + `web/`, `main.py` com leitura fail-fast do manifest, rotas de
  página geradas de tupla central, Dockerfile multi-stage, stub de
  manifest em `conftest.py` (spec 033 de lá).

## Ver também
- [[007-pagina-temperatura]] — 1ª página a migrar (a criar).
- [[008-pagina-precipitacao]] — (a criar).
- [[009-pagina-alertas]] — (a criar).
- [[010-pagina-horario]] — (a criar).
- [[011-pagina-cidades]] — (a criar).
- [[012-pagina-comparativo]] — (a criar).
- [[013-pagina-relatorio-cidade]] — (a criar).
- [[001-atualizar-docs-arquitetura]] — descreve a arquitetura de dados
  (Open-Meteo → pipeline → `weather_raw` → dbt → dashboard) que esta
  migração mantém intacta; só troca a camada de apresentação.
