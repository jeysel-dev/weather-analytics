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
- THE system SHALL reescrever `docs/architecture.md` para refletir o fluxo de
  dados real: Open-Meteo → `pipeline/ingest.py` (BigQuery `weather_raw`,
  direto, sem Postgres/Airbyte) → dbt (`staging` → `intermediate` → `marts`)
  → Streamlit.
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
- WHEN a reescrita de `docs/architecture.md` estiver concluída, THE system
  SHALL mover `EPIC.md`, `FEATURES.md` e `USER-STORIES.md` para
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
| `docs/architecture.md` continua na raiz de `docs/` (não `docs/steering/`) | Criar `docs/steering/` e mover o arquivo para lá, espelhando o projeto de referência | Fora do escopo desta spec — mudar a convenção de pastas de `docs/` é uma decisão maior que a atualização de conteúdo pedida aqui; o path atual (`docs/architecture.md`) já é referenciado por outros documentos e não há necessidade funcional de movê-lo agora |

### Componentes afetados
- `docs/architecture.md` — reescrito
- `docs/archive/EPIC.md`, `docs/archive/FEATURES.md`, `docs/archive/USER-STORIES.md` — movidos, conteúdo preservado

## Casos de borda
- Se algum link interno do repositório apontar para `docs/EPIC.md`,
  `docs/FEATURES.md` ou `docs/USER-STORIES.md` no path antigo, esses links
  quebram após o `git mv` — conferir antes de fechar a spec.

## Fora do escopo
- Qualquer mudança em `deploy/`, `docker-compose*.yml` ou nos workflows de CI
  — isso é configuração de infraestrutura, não documentação.
- Criar `docs/steering/` ou reorganizar a estrutura de `docs/` além de
  `docs/specs/` e `docs/archive/`.

## Referências de código
`docs/architecture.md`, `docs/archive/EPIC.md`, `docs/archive/FEATURES.md`,
`docs/archive/USER-STORIES.md`, `CLAUDE.md` (fonte de verdade da arquitetura
atual).

## Ver também
- [[002-daylight-hours-threshold]] — spec independente, sem sobreposição de
  escopo (esta spec é só documentação; a 002 é ajuste de teste dbt).
