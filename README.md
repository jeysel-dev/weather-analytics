# Weather Analytics Pipeline

Open-Meteo API → `pipeline/ingest.py` → BigQuery (`weather_raw`) → dbt (`staging` → `intermediate` → `marts`) → dashboard FastAPI (`api/` + `web/`)

## Arquitetura em Camadas

| Camada | Tecnologia | O que faz |
|--------|-----------|-----------|
| Ingestão | `pipeline/ingest.py` (Python) | Busca API Open-Meteo → grava direto em `weather_raw.*` no BigQuery (sem staging intermediário) |
| Transform | dbt | Lê `weather_raw` → materializa `staging` → `intermediate` → `marts` |
| Warehouse | BigQuery | Dataset `marts` com as tabelas analíticas finais (`mart_climate__daily_facts`, `mart_climate__hourly_facts`, `mart_climate__alerts`) |
| Serving / Dashboard | **FastAPI + Jinja2 + Vite/ECharts** (`api/`, `web/`) | 8 rotas (home + 7 páginas analíticas) + endpoints JSON em `/api/v1`; deploy via imagem Docker publicada no GHCR, pull/recreate gerenciados pelo repositório `infra` |
| Agendamento | cron (host) | `pipeline/run_pipeline.sh` 1×/dia via `docker compose -f docker-compose.pipeline.yml run` |

`weather_raw` guarda só uma janela recente de dias (não o histórico completo — decisão de custo). O histórico completo vive acumulado nas marts, que são `materialized='incremental'` por isso mesmo.

## Estrutura

```
Weather-Analytics/
├── pipeline/       # Ingestão (Open-Meteo → BigQuery weather_raw) + orquestração do run diário
├── dbt/            # Transformações: staging → intermediate → marts
├── api/            # Dashboard: FastAPI (páginas Jinja2 + endpoints JSON /api/v1); deploy via imagem GHCR (repo infra)
├── web/            # Frontend do dashboard: Vite + TypeScript + ECharts (build copiado para api/app/static)
├── deploy/         # crontab.example do host + manifests k8s (deploy/k8s/api/) + delegação para deploy centralizado (repo infra)
├── docs/           # Specs (docs/specs/), steering e memória de decisões
├── airflow/        # Arquitetura anterior, pausada — ver nota abaixo
└── postgresql/     # Arquitetura anterior, pausada — ver nota abaixo
```

## Pré-requisitos

- Docker Desktop instalado e rodando
- Docker Compose disponível
- Conexão com internet para download de imagens e integração com APIs
- Conta GCP com BigQuery e Service Accounts com roles: `BigQuery Data Editor` + `BigQuery Job User`

---

## Arquitetura anterior (Airflow + PostgreSQL) — pausada

Este repositório já teve uma arquitetura anterior com Airflow orquestrando
coleta → PostgreSQL → BigQuery em 4 DAGs, mais um Postgres standalone para
staging. Essa stack está **pausada** hoje (não é o caminho vivo) — o ingest
direto para BigQuery via `pipeline/ingest.py` é mais simples e mais barato
para o volume atual. Os diretórios `airflow/` e `postgresql/` continuam no
repositório para referência histórica, mas não têm setup/comandos
documentados aqui; para reativá-los, seria preciso planejamento próprio (não
é um caminho suportado atualmente).

---

## Executar o dbt manualmente

**Em produção**, o dbt roda dentro do container `weather-pipeline`, disparado
automaticamente pelo cron via `pipeline/run_pipeline.sh` — não é algo que se
roda manualmente no dia a dia.

**Para rodar manualmente/local** (dbt instalado no host, fora do container),
com `profiles.yml` gerado a partir de `pipeline/dbt_profiles.yml.example` e
variáveis de ambiente (`GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS_PIPELINE`,
etc.) configuradas no seu shell:

```bash
dbt deps --project-dir dbt --profiles-dir pipeline
dbt run  --project-dir dbt --profiles-dir pipeline
dbt test --project-dir dbt --profiles-dir pipeline
```

## Credenciais GCP

O projeto usa duas Service Accounts separadas, uma por serviço — não
compartilhe a mesma chave entre pipeline e dashboard:

| Variável | Usada por | Onde configurar |
|----------|-----------|------------------|
| `GOOGLE_APPLICATION_CREDENTIALS_PIPELINE` | `pipeline/` (ingest + dbt) | `pipeline/dbt_profiles.yml.example` → copiar e preencher |
| `GOOGLE_APPLICATION_CREDENTIALS_API` | `api/` (só leitura, SA dedicada `weather-analytics-api-sa`) | `api/.env.example` → copiar para `api/.env` |

Substitua `seu-projeto-gcp` pelo `GCP_PROJECT_ID` real do seu projeto em
qualquer comando de exemplo abaixo.

---

## 🎯 Dashboard em Produção — FastAPI + Jinja2 + Vite/ECharts

Dashboard servido por FastAPI: páginas HTML (Jinja2) + endpoints JSON em
`/api/v1`, consumidos por um frontend TypeScript (Vite + ECharts) cujo build
é copiado para `api/app/static/`. Consulta o BigQuery direto via
`google-cloud-bigquery`. Deploy via imagem Docker publicada no GHCR
(`build-and-push-api.yml`); pull e recreate do container são gerenciados pelo
repositório `infra` — ver "Deploy em produção" abaixo.

> Antes de setembro/2026 este dashboard era um app Streamlit
> (`streamlit/`). A migração para FastAPI foi incremental, página a página
> (specs `006`–`014`); o corte do código legado é a spec `015`. As 7 URLs
> antigas em maiúscula (`/Temperatura`, `/Relatorio_por_Cidade`, …)
> respondem `308` para a rota nova equivalente.

### Estrutura

```
api/
├── app/
│   ├── main.py          ← monta as 8 rotas de página a partir de uma tupla central (PAGES) + os 7 redirects 308 das URLs antigas
│   ├── routers/         ← endpoints JSON /api/v1 (um módulo por página + ref.py da camada de referência)
│   ├── schemas/         ← modelos Pydantic de resposta
│   ├── templates/       ← Jinja2 (home.html + uma por página + layout compartilhado)
│   ├── static/          ← build do Vite (gitignored; vem de `npm run build` em web/)
│   └── utils/bigquery.py ← client BigQuery + query() + max_date()/min_date() + tbl()
├── tests/               ← pytest (importa a app com manifest do Vite forjado — sem credencial)
└── .env.example

web/
├── src/
│   ├── main.ts          ← dispatch por document.body.dataset.page
│   ├── pages/           ← um módulo de gráficos ECharts por página
│   ├── nav.ts, ui.ts, format.ts, labels.ts
│   └── style.css
└── vite.config.ts       ← outDir aponta para ../api/app/static
```

### Executar localmente

```bash
# 1. Frontend: build do Vite -> api/app/static (a API falha ao subir sem o manifest)
cd web && npm ci && npm run build && cd ..

# 2. Credenciais: copiar api/.env.example para api/.env e preencher
#    GCP_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS_API, BIGQUERY_DATASET=marts

# 3. API
cd api
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell/CMD)
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Abre em [http://localhost:8000](http://localhost:8000). Sem `npm run build`
a API não sobe (leitura fail-fast do manifest do Vite em `main.py`).

### Deploy em produção

O deploy não é feito manualmente neste repositório: a imagem Docker da API
(FastAPI + frontend, `Dockerfile` multi-stage na raiz) é publicada no GHCR
pelo workflow `build-and-push-api.yml`, e o pull da imagem + recreate do
container são gerenciados pelo repositório `infra`. Os manifests k8s
(`deploy/k8s/api/`) vivem aqui; o Ingress colapsou numa regra única
`/` → `weather-analytics-api:8000` após o corte do Streamlit (spec `015`).
Ver `docs/steering/weather-analytics.md` para a fronteira entre os dois
repositórios.

### Decisões de arquitetura

| Decisão | Motivo |
|---------|--------|
| Rotas de página + menu saem de uma tupla central (`PAGES` em `main.py`) | Não dá para registrar uma rota e esquecer o item de menu — os dois campos são obrigatórios na dataclass |
| Filtros de data ancoram em `max_date()` da tabela, nunca em `CURRENT_DATE()` | O pipeline roda em lote e pode atrasar; ancorar no relógio deixaria os gráficos vazios (regra herdada do Streamlit, ainda válida) |
| Lib de gráfico: ECharts | Mesmo vocabulário do repo irmão `compras-publicas-sc` |
| Leitura fail-fast do manifest do Vite no import de `main.py` | Sobe sem frontend buildado = erro explícito, não asset sem hash |

---

## CI/CD

Dois workflows, ambos disparados em push para `main`:

- `.github/workflows/build-and-push-api.yml` — roda a suíte `pytest`, builda
  e publica `ghcr.io/jeysel-dev/weather-analytics/api` (FastAPI + frontend) e
  faz `kustomize edit set image` no overlay de staging. Dispara ao tocar
  `api/`, `web/`, `Dockerfile` ou o próprio workflow.
- `.github/workflows/build-and-push.yml` — builda e publica
  `ghcr.io/jeysel-dev/weather-pipeline` (`pipeline/Dockerfile`). Dispara ao
  tocar `pipeline/`, `dbt/` ou o próprio workflow.

O deploy em si (pull da imagem + recreate do container) é responsabilidade do
repositório `infra` — ver `docs/steering/` para o fluxo completo.

---

## Metodologia

Este projeto foi desenvolvido seguindo práticas Scrum e BDD (Epic → Features
→ User Stories), combinando competências de Analytics Engineering e Product
Ownership. O histórico completo desse planejamento — Epic, Features e User
Stories originais — está preservado em [`docs/archive/`](docs/archive/).

---

## Licença

Código, templates, modelos dbt, specs e documentação deste repositório: **[MIT](LICENSE)** —
livre para baixar, estudar, modificar e redistribuir.

Os dados climáticos são do [Open-Meteo](https://open-meteo.com/), servidos pela API sob
[CC BY 4.0](https://open-meteo.com/en/licence); este repositório apenas os consome e não os
relicencia.
