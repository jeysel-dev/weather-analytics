# Arquitetura — Weather Analytics Pipeline

## Fluxo de dados

```
 ┌──────────────────────┐
 │   Open-Meteo API     │  REST JSON, gratuita, sem autenticação
 └──────────┬───────────┘
            │  HTTP GET 4x/dia (00:30, 06:30, 12:30, 18:30 BRT)
            ▼
 ┌──────────────────────────────────────────────────────┐
 │   Airflow (Docker — LocalExecutor)                   │
 │                                                      │
 │   dag_weather_collection  ──► collector.py --once    │
 │   dag_weather_ingest      ──► PostgreSQL → BigQuery  │
 │   dag_weather_transform   ──► dbt seed/run/test      │
 └──────────────────┬───────────────────────────────────┘
                    │
                    ▼
 ┌──────────────────────────────────────────────────────┐
 │   container: weather_postgres (Ubuntu 24.04 + PG 17) │
 │                                                      │
 │   collector.py        UPSERT                         │
 │   (Python)      ──────► raw.open_meteo_hourly        │
 │                          raw.open_meteo_daily         │
 └──────────────────────────┬───────────────────────────┘
                            │
                            │  dag_weather_ingest (Airflow + BigQuery SDK)
                            │  Incremental por _extracted_at | 4x/dia
                            ▼
             ┌──────────────────────────────┐
             │   BigQuery — dataset          │
             │   weather_raw                 │
             │                               │
             │   open_meteo_hourly           │
             │   open_meteo_daily            │
             └──────────────┬────────────────┘
                            │
                            │  dbt (target: prod)
                            │  Sources: weather_raw.*
                            ▼
             ┌──────────────────────────────────────────┐
             │   BigQuery — datasets                     │
             │                                          │
             │   staging.*         (views)              │
             │   intermediate.*    (views)              │
             │   marts.*           (tables particionadas)│
             │   seeds.*           (locations)          │
             │                                          │
             │   mart_climate__daily_facts              │
             │   mart_climate__hourly_facts             │
             │   mart_climate__alerts                   │
             └──────────────┬───────────────────────────┘
                            │
                            │  google-cloud-bigquery (Python SDK)
                            │  @st.cache_data TTL=1h
                            ▼
             ┌──────────────────────────────────────────┐
             │   Streamlit (Python)                      │
             │   Nginx + systemd (AWS Lightsail)        │
             │   SSL via Certbot                        │
             │                                          │
             │   6 páginas analíticas + Comparativo     │
             └──────────────────────────────────────────┘
```

## Dois targets do dbt

| Target | Source | Destination | Quando usar |
|--------|--------|-------------|-------------|
| `dev` | `weather_staging.raw` (PostgreSQL) | `weather_staging.dbt_dev` (PostgreSQL) | Desenvolvimento local |
| `prod` | `weather_raw` (BigQuery) | `marts.*` (BigQuery) | Produção |

A variável `DBT_SOURCE_DATABASE` controla qual banco o dbt usa como source:
- `dev`: `weather_staging` (PostgreSQL local)
- `prod`: `weather_raw` (BigQuery, populado pelo ingestor Airflow)

## Responsabilidades por pasta

| Pasta | Responsabilidade |
|-------|-----------------|
| `airflow/` | Orquestração: 4 DAGs (coleta, ingestão PostgreSQL→BigQuery, transformação, backfill histórico) |
| `postgresql/` | Container PG17 + app coletor + setup documentado |
| `dbt/` | Transformações staging → intermediate → marts, testes, documentação |
| `streamlit/` | Dashboard interativo em Python: 6 páginas + comparativo; deploy no Lightsail |
| `docs/` | Arquitetura, Epic, Features e User Stories |

## Estrutura de arquivos

```
Weather-Analytics/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── EPIC.md
│   ├── FEATURES.md
│   └── USER-STORIES.md
│
├── airflow/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example
│   └── dags/
│       ├── dag_weather_collection.py
│       ├── dag_weather_ingest.py
│       ├── dag_weather_transform.py
│       └── dag_weather_backfill.py
│
├── postgresql/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── config/
│   ├── init/
│   └── collector/
│       ├── collector.py
│       └── README.md
│
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   │       ├── mart_climate__daily_facts.sql
│   │       ├── mart_climate__hourly_facts.sql
│   │       └── mart_climate__alerts.sql
│   ├── tests/
│   ├── macros/
│   └── seeds/
│       └── locations.csv              # 295 municípios de SC
│
└── streamlit/
    ├── app.py                         # Home: KPIs + tendência + mapa SC
    ├── pages/
    │   ├── 1_Temperatura.py           # Rankings, tendência regional, anomalia
    │   ├── 2_Precipitacao.py          # Acumulados, distribuição, heatmap
    │   ├── 3_Alertas.py               # Severidade, tipos, tabela filtrável
    │   ├── 4_Horario.py               # Perfil horário + dia vs média 30d
    │   ├── 5_Cidades.py               # Perfil completo por município
    │   └── 6_Comparativo.py           # Comparativo cidades, quando choveu, dia vs histórico
    ├── utils/
    │   └── bigquery.py                # Client singleton + query cache 1h
    ├── .streamlit/config.toml
    ├── requirements.txt
    ├── .env.example
    └── deploy/
        ├── nginx-weather.conf
        └── weather-streamlit.service
```

## Lineage dbt

```
raw.open_meteo_daily  ──► stg_weather__daily ──► int_weather__daily_enriched
                                                           │
seeds.locations ───────────────────────────────────────────┤
                                                           │
                                              ┌────────────┴────────────┐
                                              │                         │
                                    mart_climate__daily_facts   mart_climate__alerts
                                    (295 mun × histórico)       (eventos extremos)

raw.open_meteo_hourly ──► stg_weather__hourly ──► mart_climate__hourly_facts
                                                   (295 mun × dados horários)
```

## Datasets BigQuery em produção

| Dataset | Origem | Conteúdo |
|---------|--------|----------|
| `weather_raw` | Airflow (ingestão) | Dados brutos diários e horários |
| `staging` | dbt | Views de limpeza e padronização |
| `intermediate` | dbt | Views de enriquecimento (ephemeral) |
| `marts` | dbt | Tabelas analíticas finais (particionadas) |
| `seeds` | dbt seed | Tabela `locations` — 295 municípios de SC |

## Detalhes técnicos importantes

### Cache do Streamlit
- `@st.cache_resource` no client BigQuery → singleton por processo, não re-autentica a cada página
- `@st.cache_data(ttl=3600)` em todas as queries → evita hits desnecessários; 1h adequado dado o pipeline diário
- Cache invalidado automaticamente quando o SQL muda (ex: filtro de mesorregião diferente)

### generate_schema_name (dbt macro)
O macro sobrescreve o comportamento padrão do dbt: usa apenas o `custom_schema` sem prefixar o dataset base. Resultado: modelos com `+schema: marts` materializam no dataset `marts` (não em `weather_dw_marts`).

### mesoregion vs region
- `region` = macrorregião brasileira (sempre "Sul" para todos os 295 municípios de SC)
- `mesoregion` = mesorregião IBGE de SC (6 valores: Grande Florianópolis, Norte Catarinense, Vale do Itajaí, Serrana, Oeste Catarinense, Sul Catarinense)

Os dashboards filtram por `mesoregion` para análise geográfica interna de Santa Catarina.
