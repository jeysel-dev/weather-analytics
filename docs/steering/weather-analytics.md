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
             │   marts.*        (tabelas particionadas) │
             │   seeds.*        (locations)              │
             │                                          │
             │   mart_climate__daily_facts               │
             │   mart_climate__hourly_facts               │
             │   mart_climate__alerts                    │
             └──────────────┬───────────────────────────┘
                            │
                            │  google-cloud-bigquery (Python SDK)
                            │  @st.cache_data TTL=1h
                            ▼
             ┌──────────────────────────────────────────┐
             │   Streamlit                                │
             │   6 páginas analíticas + comparativo       │
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

### Camadas dbt não têm 1:1 com datasets BigQuery

`staging` e `marts` materializam como datasets reais no BigQuery
(`staging.*` como views, `marts.*` como tabelas particionadas). A camada
`intermediate` é `materialized: ephemeral` (`dbt_project.yml`) — não existe
como dataset ou tabela própria; o SQL é inlinado como CTE dentro dos
models de `marts` que a consomem em tempo de compilação. Quem for procurar
`intermediate.*` no BigQuery não vai encontrar nada — o lugar certo para
ler essa lógica é o `.sql` do model em `dbt/models/intermediate/`.

## Lineage dbt

```
weather_raw.open_meteo_daily  ──► stg_weather__daily ──► int_weather__daily_enriched (ephemeral)
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
| `marts` | dbt (table/incremental) | Tabelas analíticas finais, particionadas por mês e clusterizadas por `location_id`/`year_month` |
| `seeds` | dbt seed | Tabela `locations` — 295 municípios de Santa Catarina |

(`intermediate` não aparece aqui — é ephemeral, ver seção acima.)

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

Cada serviço (`weather-pipeline`, `streamlit-weather`) é publicado como
imagem Docker no GHCR (workflow `build-and-push.yml`, disparado em push
para `main` que toque `streamlit/`, `pipeline/`, `dbt/` ou o próprio
workflow). O deploy em si — pull da imagem e recreate do container — é
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
- **Dashboard** (Streamlit, só leitura): só consulta `marts`/`seeds` —
  role `BigQuery Data Viewer`.

Nenhuma das duas compartilha chave com a outra. Nomes de arquivo de chave
e paths onde as chaves ficam no servidor são detalhe físico do `infra`,
fora do escopo deste documento.

## Detalhes técnicos importantes

### Cache do Streamlit
- `@st.cache_resource` no client BigQuery → singleton por processo, não
  re-autentica a cada página.
- `@st.cache_data(ttl=3600)` em todas as queries → evita hits
  desnecessários; 1h é adequado dado o pipeline rodar 1x/dia.
- Cache em memória do processo — só limpa com restart/recreate do
  container (não sobrevive a deploy sem restart).
- Filtros de data ancoram em `MAX(date)` da própria tabela
  (`utils/bigquery.py::max_date`), nunca em `CURRENT_DATE()` — necessário
  porque o pipeline roda em lote e pode atrasar; ver `CLAUDE.md` para o
  padrão de query a seguir ao adicionar uma página nova.

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
