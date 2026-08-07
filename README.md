# Weather Analytics Pipeline

Open-Meteo API → `pipeline/ingest.py` → BigQuery (`weather_raw`) → dbt (`staging` → `intermediate` → `marts`) → Streamlit

## Arquitetura em Camadas

| Camada | Tecnologia | O que faz |
|--------|-----------|-----------|
| Ingestão | `pipeline/ingest.py` (Python) | Busca API Open-Meteo → grava direto em `weather_raw.*` no BigQuery (sem staging intermediário) |
| Transform | dbt | Lê `weather_raw` → materializa `staging` → `intermediate` → `marts` |
| Warehouse | BigQuery | Dataset `marts` com as tabelas analíticas finais (`mart_climate__daily_facts`, `mart_climate__hourly_facts`, `mart_climate__alerts`) |
| Visualização | **Streamlit** | 6 páginas analíticas + análise comparativa; deploy via Docker no Lightsail com Nginx + systemd |
| Agendamento | cron (host) | `pipeline/run_pipeline.sh` 1×/dia via `docker compose -f docker-compose.pipeline.yml run` |

`weather_raw` guarda só uma janela recente de dias (não o histórico completo — decisão de custo). O histórico completo vive acumulado nas marts, que são `materialized='incremental'` por isso mesmo.

## Estrutura

```
Weather-Analytics/
├── pipeline/       # Ingestão (Open-Meteo → BigQuery weather_raw) + orquestração do run diário
├── dbt/            # Transformações: staging → intermediate → marts
├── streamlit/       # Dashboard interativo em Python; deploy no Lightsail
├── deploy/         # crontab.example do host + delegação para deploy centralizado (repo infra)
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
| `GOOGLE_APPLICATION_CREDENTIALS_DASHBOARD` | `streamlit/` | `streamlit/.env.example` → copiar para `.env` |

Substitua `seu-projeto-gcp` pelo `GCP_PROJECT_ID` real do seu projeto em
qualquer comando de exemplo abaixo.

---

## 🎯 Streamlit — Dashboard em Produção

Dashboard interativo construído em Python, conectado diretamente ao BigQuery via `google-cloud-bigquery`.
Deploy no AWS Lightsail com Nginx como proxy reverso e systemd gerenciando o processo.

### Estrutura

```
streamlit/
├── app.py                        ← Home: KPIs + linha de temperatura + mapa SC
├── pages/
│   ├── 1_Temperatura.py          ← Rankings hot/cold, tendência mesorregião, heatmap anomalia
│   ├── 2_Precipitacao.py         ← Top 20 acumulado, pizza de classes, heatmap diário
│   ├── 3_Alertas.py              ← KPIs severidade, barras por tipo, tabela filtrável
│   ├── 4_Horario.py              ← Temp+umidade, vento+chuva, perfil médio 24h
│   └── 5_Cidades.py              ← Perfil completo por município (temp/precip/vento/alertas)
├── utils/
│   └── bigquery.py               ← Client singleton (@cache_resource) + query (@cache_data 1h)
├── .streamlit/config.toml        ← Tema dark + server escutando só 127.0.0.1:8501
├── requirements.txt
├── .env.example
└── deploy/
    ├── nginx-weather.conf        ← Proxy com WebSocket headers (obrigatório pro Streamlit)
    └── weather-streamlit.service ← systemd com EnvironmentFile e restart automático
```

### Executar localmente (Windows)

#### 1. Criar o ambiente virtual

```powershell
cd streamlit
python.exe -m pip install --upgrade pip
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Configurar credenciais

```powershell
copy .env.example .env
```

Editar o `.env` com os valores locais:

```env
GCP_PROJECT_ID=seu-projeto-gcp
BIGQUERY_DATASET=marts
BIGQUERY_SEEDS_DATASET=seeds
GOOGLE_APPLICATION_CREDENTIALS_DASHBOARD=C:/Users/seu-usuario/secrets/weather-dashboard-sa-key.json
```

> Use barras `/` ou `\\` no caminho — barra invertida simples `\` causa erro no Python.

#### 3. Sobrescrever o endereço para desenvolvimento

O `config.toml` padrão escuta apenas `127.0.0.1` com `headless = true` (modo servidor).
Para rodar localmente sem precisar alterar o arquivo commitado, passe os overrides via CLI:

```powershell
streamlit run app.py --server.address localhost --server.headless false
```

O Streamlit abrirá automaticamente [http://localhost:8501](http://localhost:8501) no browser.

#### 4. Testar cada página

| Página | O que validar |
|--------|--------------|
| Home (`app.py`) | KPIs carregam, mapa SC renderiza com pontos |
| Temperatura | Rankings hot/cold preenchidos, heatmap de anomalia sem erros |
| Precipitação | Top 20 acumulado, pizza de classes sem fatias zeradas |
| Alertas | Tabela filtrável responde aos selects de severidade/tipo |
| Horário | Gráficos de temp+umidade e perfil 24h carregam para qualquer município |
| Cidades | Dropdown de município funciona e exibe todos os painéis |

#### 5. Verificar o cache

O cache de queries tem TTL de 1h. Para forçar recarga durante testes:

```powershell
# Na UI do Streamlit: menu ⋮ (canto superior direito) → "Clear cache"
# Ou reinicie o processo:
# Ctrl+C no terminal → streamlit run app.py ...
```

---

### Deploy na AWS (Maquina Linux) — passo a passo

#### 1. Preparar o servidor

```bash
# Instalar Python venv e criar ambiente isolado
sudo apt install python3-venv python3-pip -y
python3 -m venv ~/venv/weather
source ~/venv/weather/bin/activate

# Clonar o repositório (segue a convenção ~/app_* do servidor)
git clone https://github.com/SEU_USUARIO/weather-analytics.git ~/app_weather
cd ~/app_weather/streamlit
source ~/venv/weather/bin/activate
pip install -r requirements.txt
```

#### 2. Configurar credenciais

```bash
# Copiar a service account do GCP para o servidor
mkdir -p ~/secrets
# scp da sua máquina local:
# scp <caminho-local>/weather-dashboard-sa-key.json ubuntu@<ip>:~/secrets/

# Criar o .env a partir do exemplo
cp .env.example .env
nano .env   # preencher GCP_PROJECT_ID e ajustar BIGQUERY_DATASET
```

> **Atenção nos datasets BigQuery:** verifique no console GCP quais datasets
> existem no projeto — o dashboard lê do dataset `marts`.

#### 3. Nginx

```bash
sudo cp deploy/nginx-weather.conf /etc/nginx/sites-available/weather.jeysel.dev
sudo ln -s /etc/nginx/sites-available/weather.jeysel.dev /etc/nginx/sites-enabled/

# Obter certificado SSL para o novo subdomínio
sudo certbot certonly --nginx -d weather.jeysel.dev

sudo nginx -t && sudo systemctl reload nginx
```

#### 4. systemd

```bash
# Ajustar o caminho do venv no .service se necessário
sudo cp deploy/weather-streamlit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable weather-streamlit
sudo systemctl start weather-streamlit

# Verificar logs
sudo journalctl -u weather-streamlit -f
```

### Decisões de arquitetura

| Decisão | Motivo |
|---------|--------|
| `@st.cache_data(ttl=3600)` em todas as queries | Evita hits desnecessários no BigQuery; 1h é adequado dado o pipeline diário |
| `@st.cache_resource` no client BigQuery | Singleton por processo — não re-autentica a cada página |
| Streamlit escuta só `127.0.0.1` | Nginx faz o proxy; app não fica exposta diretamente |
| `QUALIFY ROW_NUMBER()` no mapa | Filtra último dia por município sem subquery extra, aproveitando o partition pruning do BigQuery |
| `clip(lower=1)` nos scatter mapbox | Plotly mapbox falha silenciosamente com tamanho zero |

---

## CI/CD

Único workflow: `.github/workflows/build-and-push.yml` — builda e publica
imagens Docker no GHCR (`ghcr.io/jeysel-dev/...`) para `streamlit/` e para o
pipeline (`pipeline/Dockerfile`), disparado em push para `main` que toque
`streamlit/`, `pipeline/`, `dbt/` ou o próprio arquivo do workflow. O deploy
em si (pull da imagem + recreate do container) é feito manualmente/via script
no servidor — ver `docs/steering/` para o fluxo de deploy completo.

---

## Metodologia

Este projeto foi desenvolvido seguindo práticas Scrum e BDD (Epic → Features
→ User Stories), combinando competências de Analytics Engineering e Product
Ownership. O histórico completo desse planejamento — Epic, Features e User
Stories originais — está preservado em [`docs/archive/`](docs/archive/).
