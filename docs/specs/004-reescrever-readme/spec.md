# Reescrever README.md desatualizado

## Tipo
[x] Melhoria

## Status
[x] implementado

## Resumo
`README.md` (raiz do repo, arquivo de entrada agora que o repositório é
público) descreve integralmente a arquitetura anterior — Airflow + PostgreSQL
como orquestração/staging ativos, backfill via DAG, dbt via
`docker compose run dbt-build` dentro de `postgresql/`, seção "CI/CD
automático via GitHub Actions (Evidence → GitHub Pages)" que nunca existiu
neste repositório — e não reflete o sistema real hoje.

## Contexto
Achado confirmado em auditoria completa linha a linha do README contra
`CLAUDE.md` como fonte de verdade (2026-08-07), na mesma sessão em que
gitleaks, workflows do GitHub Actions, `docker-compose.pipeline.yml`,
histórico git e `deploy/` foram auditados por exposição — nenhum desses teve
achado de secret/credencial vazada, mas o README teve o mesmo tipo de
desatualização já corrigido em `docs/steering/weather-analytics.md` pela spec
[[001-atualizar-docs-arquitetura]]. Achado adicional relevante para segurança:
o README (linha 360/363, versão pré-reescrita) documentava publicamente o
padrão de credencial compartilhada antigo (`GOOGLE_APPLICATION_CREDENTIALS`
sem sufixo, "é o mesmo já usado no Airflow") — padrão que já foi corrigido no
código (`GOOGLE_APPLICATION_CREDENTIALS_PIPELINE` /
`GOOGLE_APPLICATION_CREDENTIALS_DASHBOARD`), mas a documentação nunca
acompanhou.

## Requirements (EARS)

### Funcionais
- THE system SHALL reescrever a seção de arquitetura para refletir o fluxo
  real: Open-Meteo → `pipeline/ingest.py` → BigQuery (`weather_raw`) → dbt
  (`staging` → `intermediate` → `marts`) → Streamlit, sem PostgreSQL/Airflow
  como caminho ativo.
- THE system SHALL remover ou condensar drasticamente as seções operacionais
  de Airflow/PostgreSQL (setup, DAGs, comandos `docker exec`, backfill) —
  mantendo no máximo uma nota breve de que essa foi uma arquitetura anterior,
  sem os comandos operacionais completos, já que não refletem nada executável
  hoje.
- THE system SHALL corrigir a instrução de credencial (antes
  `GOOGLE_APPLICATION_CREDENTIALS` sem sufixo, com a frase "é o mesmo já
  usado no Airflow") para documentar as duas variáveis atuais:
  `GOOGLE_APPLICATION_CREDENTIALS_PIPELINE` e
  `GOOGLE_APPLICATION_CREDENTIALS_DASHBOARD`, cada uma com sua própria
  service account.
- THE system SHALL remover a seção "CI/CD automático via GitHub Actions
  (Evidence → GitHub Pages)" — não existe workflow desse tipo neste
  repositório; o único workflow real (`build-and-push.yml`) deve ser descrito
  corretamente (build + push de imagem Docker para GHCR, disparado em push
  para `main` que toque `streamlit/`, `pipeline/`, `dbt/` ou o próprio
  workflow).
- THE system SHALL generalizar o GCP Project ID real
  (`weather-analytics-490113`) para um placeholder (`seu-projeto-gcp`) em
  qualquer comando de exemplo.
- THE system SHALL remover a credencial de exemplo `admin`/`admin` do setup
  local do Airflow junto com a remoção/condensação da seção Airflow — não é
  requirement independente, é consequência direta do requirement anterior.
- THE system SHALL condensar a seção "Metodologia Ágil"/Epic/Features para um
  parágrafo curto com link para `docs/archive/` (que já preserva a versão
  histórica completa via `EPIC.md`, `FEATURES.md`, `USER-STORIES.md` — 658
  linhas — movidos lá pela spec 001), em vez de duplicar o conteúdo no
  README.

### Não-funcionais
- A reescrita SHALL ser verificada contra `CLAUDE.md` e contra o código real
  (não só contra a versão anterior do README) antes de ser considerada
  completa.
- Nenhum path de servidor específico da VPS, IP, ou domínio interno SHALL ser
  introduzido na reescrita além do que já é público de qualquer forma (ex: o
  domínio do dashboard, que já é o link público).

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Condensar (não deletar totalmente) as seções de Airflow/PostgreSQL para uma nota breve | Remover toda menção a Airflow/PostgreSQL do README | Preservar contexto histórico do projeto (por que a stack existe no repo, por que está pausada) sem manter documentação operacional completa de algo que não roda mais — quem quiser o passo a passo original ainda pode ler `postgresql/README.md`/`airflow/` diretamente, ou o histórico git do README |
| Condensar "Metodologia Ágil" para um parágrafo com link, em vez de reescrever Epic/Features linha a linha | Reescrever a seção inteira para bater com a arquitetura atual, mantendo o mesmo nível de detalhe | `docs/archive/EPIC.md`/`FEATURES.md`/`USER-STORIES.md` já preservam essa informação (movidos lá pela spec 001); manter duas versões (README + archive) da mesma narrativa exigiria atualizar as duas toda vez que algo mudasse |

### Componentes afetados
- `README.md` — reescrita das seções de arquitetura, setup Airflow/PostgreSQL,
  credenciais, CI/CD e Metodologia Ágil; mantidas sem alteração as seções que
  já refletem a realidade (estrutura de `streamlit/`, decisões de arquitetura
  do dashboard, pré-requisitos gerais)

## Casos de borda
- Se algum link externo (badge, GitHub "About", link em outro repositório)
  referenciar uma seção específica do README por âncora/nome — verificado
  internamente (nenhum arquivo do repo referencia `README.md#`); links
  externos ao repositório não são verificáveis a partir daqui e ficam como
  risco residual aceito.

## Fora do escopo
- `docs/steering/weather-analytics.md` (spec [[001-atualizar-docs-arquitetura]],
  ainda pendente) — trata da mesma desatualização de arquitetura, mas em
  outro arquivo com outro público (documentação técnica interna via SDD, não
  o arquivo de entrada do repositório). Não duplicar o trabalho aqui.
- Qualquer mudança em `deploy/`, `docker-compose*.yml`, workflows de CI ou
  `.gitignore` — a limpeza do `.gitignore` feita na mesma sessão é um item
  operacional separado, sem requirement formal nesta spec.
- Remover ou alterar os diretórios `airflow/`/`postgresql/` em si — só a
  documentação no README muda; os diretórios continuam no repo, pausados,
  como já documentado em `CLAUDE.md`.

## Referências de código
- `README.md` — arquivo reescrito por esta spec
- `CLAUDE.md` — fonte de verdade da arquitetura atual
- `docs/steering/weather-analytics.md` — para não duplicar trabalho da spec 001
- `pipeline/ingest.py`, `pipeline/dbt_profiles.yml.example` — confirmam
  `GOOGLE_APPLICATION_CREDENTIALS_PIPELINE`
- `streamlit/.env.example`, `streamlit/utils/bigquery.py` — confirmam
  `GOOGLE_APPLICATION_CREDENTIALS_DASHBOARD`
- `.github/workflows/build-and-push.yml` — único workflow real, usado para
  descrever CI/CD corretamente
- `docs/archive/EPIC.md`, `docs/archive/FEATURES.md`,
  `docs/archive/USER-STORIES.md` — conteúdo histórico preservado, referenciado
  pela versão condensada da seção "Metodologia Ágil"

## Ver também
- [[001-atualizar-docs-arquitetura]] — mesma classe de achado (documentação
  descrevendo arquitetura anterior como ativa), aplicado a
  `docs/steering/weather-analytics.md` em vez do README; esta spec (004) não
  duplica aquele trabalho, é o mesmo tipo de correção num arquivo diferente
  com público diferente.
