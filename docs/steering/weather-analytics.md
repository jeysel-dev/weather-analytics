# Steering — Weather Analytics

Documentação técnica interna do processo SDD para este repositório: o que
`weather-analytics` precisa/espera logicamente do restante do ambiente
(nomes de dataset, fluxo de dados, arquitetura de camadas). Não descreve
como o repositório `infra` entrega isso fisicamente (paths de servidor,
IPs, mecanismo exato de deploy) — essa fronteira é deliberada, ver
[[003-estrutura-steering-memory]]. Para decisões e incidentes de produção,
`CLAUDE.md` na raiz do repo é a fonte de verdade; este documento descreve a
arquitetura em regime, não o histórico de como ela chegou lá.

## Fluxo de dados

```
 ┌──────────────────────┐
 │   Open-Meteo API     │  REST JSON, gratuita, sem autenticação
 └──────────┬───────────┘
            │  HTTP GET, 1x/dia (via pipeline/run_pipeline.sh)
            ▼
 ┌──────────────────────────────────────────────────────┐
 │   pipeline/ingest.py (Python)                        │
 │   Busca Open-Meteo → grava direto no BigQuery         │
 │   (sem staging intermediário em Postgres/Airbyte)     │
 └──────────────────┬───────────────────────────────────┘
                    │
                    ▼
             ┌──────────────────────────────┐
             │   BigQuery — dataset          │
             │   weather_raw                 │
             │                               │
             │   open_meteo_daily            │
             │   open_meteo_hourly           │
             └──────────────┬────────────────┘
                            │
                            │  dbt (target: prod)
                            │  Sources: weather_raw.*
                            ▼
             ┌──────────────────────────────────────────┐
             │   BigQuery — datasets                     │
             │                                          │
             │   staging.*      (views)                 │
             │   intermediate.* (view — só 1 model)      │
             │   marts.*        (tabelas particionadas) │
             │   seeds.*        (locations)              │
             │                                          │
             │   mart_climate__daily_facts               │
             │   mart_climate__hourly_facts               │
             │   mart_climate__alerts                    │
             └──────────────┬───────────────────────────┘
                            │
                            │  google-cloud-bigquery (Python SDK)
                            ▼
             ┌──────────────────────────────────────────┐
             │   Dashboard FastAPI (api/ + web/)          │
             │   home + 7 páginas (Jinja2 + ECharts)      │
             │   + endpoints JSON /api/v1                 │
             └──────────────────────────────────────────┘
```

`weather_raw` só guarda uma janela recente (o `--days` que `ingest.py`
busca a cada run — padrão 2 dias), não o histórico completo. Isso é
decisão deliberada de custo, e é a razão pela qual `mart_climate__daily_facts`
e `mart_climate__hourly_facts` são `materialized='incremental'` — sem
histórico completo no raw, um rebuild `'table'` apagaria o histórico
acumulado nas marts. Detalhes de por que essa arquitetura existe e o
incidente que a tornou obrigatória (não só desejável) estão em `CLAUDE.md`,
não repetidos aqui.

### `intermediate` é dataset real — não segue o default `ephemeral` do projeto

`dbt_project.yml` define `intermediate: +materialized: ephemeral` como
default de pasta, mas o único model que existe hoje em
`dbt/models/intermediate/` (`int_weather__daily_enriched.sql`) sobrescreve
esse default no próprio `config()` do model:

```sql
{{ config(materialized = 'view', schema = 'intermediate') }}
```

Ou seja, `intermediate` **existe como dataset físico no BigQuery**, com
uma view (`int_weather__daily_enriched`) — não é inlinado como CTE. A
service account do pipeline precisa de permissão de escrita nesse dataset
especificamente (não só em `staging`/`marts`). Se um novo model for
adicionado a `dbt/models/intermediate/` sem `config()` próprio, aí sim ele
herdaria o default `ephemeral` do projeto — o comportamento atual é
específico deste model, não da camada como um todo.

## Lineage dbt

```
weather_raw.open_meteo_daily  ──► stg_weather__daily ──► int_weather__daily_enriched (view, dataset intermediate)
                                                                    │
seeds.locations ─────────────────────────────────────────────────┤
                                                                    │
                                                       ┌────────────┴────────────┐
                                                       │                         │
                                             mart_climate__daily_facts   mart_climate__alerts
                                             (incremental, 295 mun ×    (table, lê de daily_facts —
                                              histórico completo)        não do raw, rebuild seguro)

weather_raw.open_meteo_hourly ──► stg_weather__hourly ──► mart_climate__hourly_facts
                                                           (incremental, 295 mun × dados horários)
```

## Datasets BigQuery em produção

| Dataset | Origem | Conteúdo |
|---------|--------|----------|
| `weather_raw` | `pipeline/ingest.py` | Dados brutos diários e horários — só janela recente |
| `staging` | dbt (view) | Limpeza e padronização, 1:1 com o raw |
| `intermediate` | dbt (view — 1 model, override do default ephemeral) | `int_weather__daily_enriched` — join com `seeds.locations`, cálculo de `daylight_hours` e médias móveis 30d |
| `marts` | dbt (table/incremental) | Tabelas analíticas finais, particionadas por mês e clusterizadas por `location_id`/`year_month` |
| `seeds` | dbt seed | Tabela `locations` — 295 municípios de Santa Catarina |

## Agendamento

Cron 1x/dia no host, via `pipeline/run_pipeline.sh` (não Airflow/DAGs). O
script roda três passos em sequência e aborta se `dbt run` falhar:

1. `pipeline/ingest.py` — ingestão Open-Meteo → `weather_raw`
2. `dbt run` — staging → marts
3. `dbt test` — falha nos testes gera alerta, mas não reverte dados já
   carregados (o `dbt run` do passo 2 já commitou)

## Arquitetura anterior — pausada, não é caminho ativo

`airflow/` (orquestração via DAGs, 4x/dia) e `postgresql/` (staging
standalone com collector Python) existem no repositório mas estão
**pausados**. Não documentar esses diretórios como parte do fluxo em
produção — são referência histórica de uma arquitetura anterior, mantida
no repo sem setup/comandos operacionais aqui (ver `README.md` para a nota
condensada voltada a leitor externo).

## Deploy

Cada serviço (`weather-pipeline`, `weather-analytics-api`) é publicado como
imagem Docker no GHCR, disparado em push para `main`: `build-and-push-api.yml`
para a API (toca `api/`, `web/`, `Dockerfile`), `build-and-push.yml` para o
pipeline (toca `pipeline/`, `dbt/`). O deploy em si — pull da imagem e recreate do container — é
responsabilidade do repositório `infra`, que também é dono do agendamento
físico (cron do host) e do runtime dos containers. Este repositório não
documenta esse mecanismo além de "a imagem é publicada no GHCR e consumida
pelo `infra`" — detalhes de servidor, path ou IP não pertencem aqui (ver
[[003-estrutura-steering-memory]]).

## Credenciais GCP — duas service accounts por privilégio mínimo

O pipeline e o dashboard usam service accounts GCP distintas, cada uma com
o menor privilégio necessário para o que faz:

- **Pipeline** (`ingest.py` + `dbt run`/`dbt test`): precisa escrever em
  `weather_raw` e nas marts — role `BigQuery Data Editor`.
- **Dashboard** (API FastAPI, só leitura): só consulta `marts`/`seeds` —
  role `BigQuery Data Viewer`.

Nenhuma das duas compartilha chave com a outra. Nomes de arquivo de chave
e paths onde as chaves ficam no servidor são detalhe físico do `infra`,
fora do escopo deste documento.

## Detalhes técnicos importantes

### Filtros de data ancoram no dado real
- As queries do dashboard ancoram a janela de período em `MAX(date)` da
  própria tabela (`api/app/utils/bigquery.py::max_date`), nunca em
  `CURRENT_DATE()` — necessário porque o pipeline roda em lote e pode
  atrasar; ver `CLAUDE.md` para o padrão de query a seguir ao adicionar uma
  rota nova. Regra herdada da versão Streamlit do dashboard.

### Cache — o que a FastAPI mantém em memória (equivalente ao do Streamlit)
O modelo de cache mudou na migração Streamlit → FastAPI; o que a API guarda:

- **Client BigQuery: singleton por processo** via `@lru_cache(maxsize=1)` em
  `api/app/utils/bigquery.py::_client` — equivalente direto do
  `@st.cache_resource` do Streamlit: não re-autentica nem reabre conexão a
  cada request.
- **Listas de referência** (`/api/v1/ref/mesorregioes`, `/api/v1/ref/cidades`,
  e o `_cidades()` de `horario.py`): `@lru_cache(maxsize=1)`, **sem TTL e sem
  invalidação automática** — diferente do `@st.cache_data(ttl=3600)` do
  Streamlit. Justificativa (documentada em `api/app/routers/ref.py`): essas
  listas só mudam quando o seed `locations` muda, o que é raríssimo.
- **Queries de dado** (não-referência), incluindo `/api/v1/ref/daily-meta` e
  `/api/v1/ref/alerts-meta`: **sem cache de aplicação**. Dependem do cache de
  resultado server-side do próprio BigQuery (24h, sem custo, para SQL
  idêntico). Diferença deliberada do modelo antigo, que punha
  `@st.cache_data(ttl=3600)` em toda query.
- Tanto o client singleton quanto as listas de referência vivem na memória do
  processo — **só limpam com restart/recreate do container** (mesma
  observação que valia para o cache do Streamlit, ainda verdadeira).

### `generate_schema_name` (dbt macro)
`dbt/macros/weather_utils.sql` sobrescreve o comportamento padrão do dbt:
usa só o `custom_schema` sem prefixar o dataset base. Resultado: models
com `+schema: marts` materializam direto no dataset `marts` (não em algo
como `weather_dw_marts`).

### `mesoregion` vs `region`
- `region` = macrorregião brasileira — sempre `"Sul"` para os 295
  municípios do seed `locations.csv`.
- `mesoregion` = mesorregião IBGE de Santa Catarina (6 valores: Grande
  Florianópolis, Norte Catarinense, Vale do Itajaí, Serrana, Oeste
  Catarinense, Sul Catarinense).

Os dashboards filtram por `mesoregion` para análise geográfica interna de
Santa Catarina — `region` não distingue nada dentro do dataset atual.

## Ver também
- `CLAUDE.md` (raiz) — decisões de custo, incidentes de produção e a razão
  histórica por trás da arquitetura incremental.
- [[001-atualizar-docs-arquitetura]] — spec que motivou esta reescrita.
- [[003-estrutura-steering-memory]] — regra de fronteira entre este
  documento e o repositório `infra`.
