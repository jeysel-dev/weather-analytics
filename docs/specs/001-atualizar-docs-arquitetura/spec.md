# Atualizar documentação de arquitetura desatualizada

## Tipo
[x] Melhoria

## Status
[x] draft

## Resumo
`docs/architecture.md` e os artefatos de planejamento (`EPIC.md`, `FEATURES.md`,
`USER-STORIES.md`) descrevem uma arquitetura anterior (Airflow ativo, ingestão
via PostgreSQL/Airbyte, deploy Nginx+systemd na Lightsail) que não reflete o
sistema real hoje.

## Requirements (EARS)

### Funcionais
- THE system SHALL reescrever `docs/steering/weather-analytics.md` (path
  atualizado pela spec [[003-estrutura-steering-memory]] — arquivo era
  `docs/architecture.md` na raiz de `docs/`) para refletir o fluxo de dados
  real: Open-Meteo → `pipeline/ingest.py` (BigQuery `weather_raw`, direto,
  sem Postgres/Airbyte) → dbt (`staging` → `intermediate` → `marts`) →
  Streamlit.
- THE system SHALL documentar que a stack Airflow (`airflow/`) e o Postgres
  standalone (`postgresql/`) existem no repositório mas estão pausados/não
  usados hoje — não removê-los do repo, só corrigir a documentação para não
  descrevê-los como caminho ativo.
- THE system SHALL documentar a ingestão como cron 1x/dia via
  `pipeline/run_pipeline.sh` no host (não 4x/dia via DAGs Airflow).
- THE system SHALL documentar o deploy real de cada serviço: `weather-pipeline`
  via imagem GHCR com SHA fixo (repo `infra`) e `streamlit-weather` via
  `deploy-streamlit-weather.sh` (também repo `infra`) — não Nginx+systemd+Certbot
  gerenciado localmente neste repositório.
- WHEN a reescrita de `docs/steering/weather-analytics.md` estiver concluída,
  THE system SHALL mover `EPIC.md`, `FEATURES.md` e `USER-STORIES.md` para
  `docs/archive/`, preservando o conteúdo original sem reescrevê-los — são
  artefatos de um processo de planejamento anterior (Epic/Features/User
  Stories em formato BDD), não specs SDD, e carregam a mesma descrição de
  arquitetura obsoleta; arquivar em vez de corrigir evita manter duas fontes
  divergentes da mesma informação.

### Não-funcionais
- A reescrita SHALL ser verificada contra o código real (não só contra o
  CLAUDE.md) antes de publicar qualquer afirmação nova — CLAUDE.md é a fonte
  de verdade de mais alto nível, mas detalhes de implementação (nomes de
  variável, comandos exatos) devem ser confirmados no código quando citados.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Arquivar `EPIC.md`/`FEATURES.md`/`USER-STORIES.md` em vez de reescrever | Reescrever os três para bater com a arquitetura atual | Não são specs SDD nem documentação técnica consultada operacionalmente — são artefatos de planejamento de portfólio (Epic/Features/User Stories BDD) que, mantidos "vivos", exigiriam atualização toda vez que a arquitetura mudar de novo; arquivar reconhece que esse processo de planejamento não é mais o mecanismo usado neste repo (que passa a ser SDD via `docs/specs/`) |
~~`docs/architecture.md` continua na raiz de `docs/` (não `docs/steering/`)~~ — **superada por [[003-estrutura-steering-memory]]**: arquivo movido para `docs/steering/weather-analytics.md`, conteúdo ainda não reescrito | Criar `docs/steering/` e mover o arquivo para lá, espelhando o projeto de referência | Decisão original: fora do escopo desta spec, mudar convenção de pastas de `docs/` era decisão maior que a atualização de conteúdo pedida aqui. Revertida pela spec 003 — ver lá o motivo da reversão |

### Componentes afetados
- `docs/steering/weather-analytics.md` (movido pela spec 003; conteúdo ainda desatualizado) — reescrever
- `docs/archive/EPIC.md`, `docs/archive/FEATURES.md`, `docs/archive/USER-STORIES.md` — movidos, conteúdo preservado

## Casos de borda
- Se algum link interno do repositório apontar para `docs/EPIC.md`,
  `docs/FEATURES.md` ou `docs/USER-STORIES.md` no path antigo, esses links
  quebram após o `git mv` — conferir antes de fechar a spec.

## Fora do escopo
- Qualquer mudança em `deploy/`, `docker-compose*.yml` ou nos workflows de CI
  — isso é configuração de infraestrutura, não documentação.
- ~~Criar `docs/steering/` ou reorganizar a estrutura de `docs/` além de
  `docs/specs/` e `docs/archive/`~~ — superado por [[003-estrutura-steering-memory]],
  que criou `docs/steering/` e `docs/memory/`.

## Referências de código
`docs/steering/weather-analytics.md` (path atual; era `docs/architecture.md`),
`docs/archive/EPIC.md`, `docs/archive/FEATURES.md`,
`docs/archive/USER-STORIES.md`, `CLAUDE.md` (fonte de verdade da arquitetura
atual).

## Ver também
- [[002-daylight-hours-threshold]] — spec independente, sem sobreposição de
  escopo (esta spec é só documentação; a 002 é ajuste de teste dbt).
- [[003-estrutura-steering-memory]] — moveu `docs/architecture.md` para
  `docs/steering/weather-analytics.md`, revertendo a decisão original desta
  spec de manter o arquivo na raiz de `docs/`. O requirement de reescrever o
  conteúdo continua desta spec (001), só o path mudou.
