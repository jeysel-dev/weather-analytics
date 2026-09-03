# dbt — Transformações e Data Warehouse

Projeto dbt para transformação dos dados coletados da Open-Meteo API.
Conecta no PostgreSQL (dev) e no BigQuery (prod) via profiles configurados localmente.

> **Os containers dbt fazem parte do agrupador `weather-analytics`.**
> Todos os comandos são executados a partir da pasta `postgresql/`.

## Estrutura

```
dbt/
├── dbt_project.yml             # Configuração central + variáveis + testes
├── packages.yml                # dbt_utils, dbt_expectations, audit_helper
├── profiles.yml.example        # Template para ~/.dbt/profiles.yml
├── models/
│   ├── staging/
│   │   ├── sources.yml         # Fontes + freshness + testes de source
│   │   ├── schema.yml          # Documentação e testes dos modelos staging
│   │   ├── stg_weather__hourly.sql
│   │   └── stg_weather__daily.sql
│   ├── intermediate/
│   │   └── int_weather__daily_enriched.sql  # join daily + seed locations (enriquece com mesoregion)
│   └── marts/
│       ├── schema.yml          # Documentação e testes dos marts
│       ├── mart_climate__daily_facts.sql    # 1 linha por município × dia (últimos 12 meses)
│       ├── mart_climate__hourly_facts.sql   # 1 linha por município × hora (últimos 30 dias)
│       └── mart_climate__alerts.sql         # 1 linha por evento extremo (histórico completo)
├── tests/                      # Testes personalizados (singular tests)
│   ├── test_temp_min_less_than_max.sql
│   ├── test_no_date_gaps_per_location.sql
│   ├── test_unique_daily_facts_pk.sql
│   ├── test_alerts_have_valid_location.sql
│   └── test_raw_data_freshness.sql
├── macros/
│   └── weather_utils.sql       # wmo_code_to_label, beaufort, celsius_to_f
└── seeds/
    └── locations.csv           # 295 municípios de Santa Catarina monitorados
```

## Setup inicial

```powershell
# 1. Configure o profiles.yml (Windows PowerShell)
New-Item -ItemType Directory -Force "$env:USERPROFILE\.dbt"
Copy-Item "C:\Dev\Analytics-Engineer\Weather-Analytics\dbt\profiles.yml.example" `
          "$env:USERPROFILE\.dbt\profiles.yml"
```

> O build e a subida dos containers é feita a partir da pasta `postgresql/`.
> Ver `postgresql/README.md`.

## Executando o pipeline

Todos os comandos abaixo devem ser executados dentro da pasta `postgresql/`:

```bash
cd C:\Dev\Analytics-Engineer\Weather-Analytics\postgresql

# Validar conexao com o banco
docker compose run --rm dbt-debug

# Carregar seeds (locations.csv)
docker compose run --rm dbt-seed

# Pipeline completo (run + test)
docker compose run --rm dbt-build

# So os modelos
docker compose run --rm dbt-run

# So os testes
docker compose run --rm dbt-test

# Camada por camada
docker compose run --rm dbt-run-staging
docker compose run --rm dbt-run-marts
```

## Executar em producao (BigQuery)

```bash
cd C:\Dev\Analytics-Engineer\Weather-Analytics\postgresql

DBT_TARGET=prod docker compose run --rm dbt-build
```

PowerShell:

```powershell
$env:DBT_TARGET="prod"; docker compose run --rm dbt-seed
$env:DBT_TARGET="prod"; docker compose run --rm dbt-build
```

## Documentacao (http://localhost:8080)

```bash
cd C:\Dev\Analytics-Engineer\Weather-Analytics\postgresql

# Gera a documentacao
docker compose run --rm dbt-docs-generate

# Serve a documentacao (mante rodando -- acesse http://localhost:8080)
docker compose run --rm --service-ports dbt-docs
```

## Modelos

### Staging

| Modelo | Source | O que faz |
|--------|--------|-----------|
| `stg_weather__daily` | `raw.open_meteo_daily` | Renomeia colunas, tipagem, filtragem básica |
| `stg_weather__hourly` | `raw.open_meteo_hourly` | Renomeia colunas, tipagem, código WMO traduzido |

### Intermediate

| Modelo | Inputs | O que faz |
|--------|--------|-----------|
| `int_weather__daily_enriched` | `stg_weather__daily` + `seeds.locations` | Join que acrescenta city_name, state_name, region, **mesoregion**, latitude, longitude, altitude ao dado diário |

### Marts

| Modelo | Granularidade | Materialização | Período |
|--------|---------------|----------------|---------|
| `mart_climate__daily_facts` | Município × dia | Table (particionada por date) | Últimos 12 meses |
| `mart_climate__hourly_facts` | Município × hora | Table (particionada por date) | Últimos 30 dias |
| `mart_climate__alerts` | Evento extremo | Table | Histórico completo |

### Colunas-chave compartilhadas

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `location_id` | string | Slug do município (ex: `florianopolis`) |
| `city_name` | string | Nome completo |
| `mesoregion` | string | Macrorregião de SC — 8 macrorregiões socioassistenciais / FECAM (ex: `Meio Oeste`, `Grande Oeste`). Nome da coluna é histórico; não é a mesorregião do IBGE. |
| `region` | string | Macrorregião brasileira (sempre `Sul` para SC) |
| `year_month` | string | Formato `YYYY-MM` (pré-computado para filtros no Evidence) |

## Testes implementados

### Testes default (schema.yml)

| Modelo | Coluna | Teste |
|--------|--------|-------|
| `stg_weather__hourly` | `location_id` | not_null, accepted_values |
| `stg_weather__hourly` | `temperature_c` | accepted_range (-20..55) |
| `stg_weather__hourly` | `relative_humidity_pct` | accepted_range (0..100) |
| `mart_climate__daily_facts` | `temp_max_c` | not_null, accepted_range |
| `mart_climate__daily_facts` | `precipitation_class` | accepted_values |
| `mart_climate__daily_facts` | `uv_risk_level` | accepted_values |
| `mart_climate__alerts` | `alert_type` | not_null, accepted_values |
| `mart_climate__alerts` | `severity` | accepted_values |

### Testes personalizados (tests/)

| Arquivo | O que verifica |
|---------|---------------|
| `test_temp_min_less_than_max` | temp_min nunca maior que temp_max |
| `test_no_date_gaps_per_location` | sem dias faltando (ultimos 30 dias) |
| `test_unique_daily_facts_pk` | unicidade de location_id + date |
| `test_alerts_have_valid_location` | alertas com cidade existente no seed |
| `test_raw_data_freshness` | todos os locais com dados < 25h |

## Lineage

```
raw.open_meteo_daily  ──► stg_weather__daily ──► int_weather__daily_enriched
                                                           │
seeds.locations ───────────────────────────────────────────┤
                                                           │
                                              ┌────────────┴────────────┐
                                              │                         │
                                    mart_climate__daily_facts   mart_climate__alerts
                                    (295 mun × 12 meses)        (eventos extremos)

raw.open_meteo_hourly ──► stg_weather__hourly ──► mart_climate__hourly_facts
                                                   (295 mun × últimos 30 dias)
```
