# Features: Weather Analytics Platform

Este documento detalha as features do Epic Weather Analytics Platform, seguindo estrutura:
- Objetivo
- User Stories relacionadas
- Critérios de aceite
- Implementação técnica

---

## Feature 1: Ingestão Automatizada de Dados Climáticos

### 🎯 Objetivo
Coletar dados climáticos de múltiplas localidades brasileiras via API Open-Meteo, armazenar em PostgreSQL e replicar para BigQuery via Airbyte.

### 📖 User Stories
- US-001: Coletar dados temperatura via API
- US-002: Coletar dados precipitação via API
- US-003: Armazenar dados PostgreSQL
- US-004: Replicar dados para BigQuery

### ✅ Critérios de Aceite (Feature Level)

**Given** API Open-Meteo disponível  
**When** executar script coleta diária  
**Then** dados devem ser armazenados em PostgreSQL  
**And** Airbyte deve replicar para BigQuery (< 1h latência)  
**And** logs devem registrar sucesso/falha  

### 🔧 Implementação Técnica

**Stack:**
- Python (requests, psycopg2, google-cloud-bigquery)
- PostgreSQL 17
- Docker Compose
- Airflow (orquestração da coleta e ingestão)

**Arquivos:**
- `postgresql/collector/collector.py` - Script coleta API
- `airflow/dags/dag_weather_collection.py` - DAG de coleta (4x/dia)
- `airflow/dags/dag_weather_ingest.py` - DAG de ingestão PostgreSQL → BigQuery (incremental)

**Testes:**
- [x] Teste unitário: parsing resposta API
- [x] Teste integração: insert PostgreSQL
- [x] Teste E2E: PostgreSQL → BigQuery sync

### 📊 Métricas
- Localidades: 295 (todos os municípios de Santa Catarina)
- Frequência: 4x/dia (coleta) + 4x/dia (ingestão)
- Latência média: ~30min (coleta → BigQuery)
- Taxa sucesso: 99.2%

---

## Feature 2: Pipeline ELT com Data Quality

### 🎯 Objetivo
Transformar dados brutos em modelo dimensional analytics com camadas staging → intermediate → marts, incluindo testes automatizados para garantir confiabilidade.

### 📖 User Stories
- US-005: Criar camada staging (dados brutos limpos)
- US-006: Calcular métricas agregadas (intermediate)
- US-007: Criar data marts por domínio
- US-008: Implementar 40+ testes data quality

### ✅ Critérios de Aceite (Feature Level)

**Given** dados brutos no BigQuery  
**When** executar `dbt run`  
**Then** camadas staging/intermediate/marts devem ser criadas  
**And** todos testes dbt devem passar (49/49)  
**And** documentação schema.yml deve estar completa  
**And** lineage graph dbt deve exibir dependências  

### 🔧 Implementação Técnica

**Stack:**
- dbt 1.9
- BigQuery
- dbt packages: dbt_utils, dbt_expectations

**Camadas:**
```
staging/
  stg_weather__raw_observations.sql
intermediate/
  int_weather__temperature_aggregates.sql
  int_weather__precipitation_metrics.sql
marts/
  marts_weather__daily_summary.sql
  marts_weather__climate_alerts.sql
```

**Testes (49 total):**
- 15x unique
- 12x not_null
- 10x accepted_values
- 8x dbt_utils.expression_is_true
- 4x freshness

### 📊 Métricas
- Modelos dbt: 12
- Testes: 49
- Cobertura: 100%
- Tempo execução: ~3min

---

## Feature 3: Dashboard Interativo em Produção

### 🎯 Objetivo
Publicar dashboard Streamlit no AWS Lightsail com Nginx + systemd, servindo visualizações interativas conectadas ao BigQuery em tempo real.

### 📖 User Stories
- US-009: Criar visualizações temperatura
- US-010: Criar visualizações precipitação
- US-011: Implementar página alertas climáticos
- US-012: Deploy em produção com HTTPS

### ✅ Critérios de Aceite (Feature Level)

**Given** modelos dbt finalizados no BigQuery  
**When** acessar o subdomínio do dashboard  
**Then** Streamlit deve servir as páginas via Nginx (HTTPS)  
**And** dados devem ser carregados do BigQuery com cache de 1h  
**And** visualizações devem carregar em < 5s (primeira carga) e < 1s (cache)  
**And** systemd deve reiniciar o processo automaticamente em caso de falha  

### 🔧 Implementação Técnica

**Stack:**
- Streamlit 1.41 + google-cloud-bigquery 3.27
- Nginx (proxy reverso + WebSocket headers)
- systemd (gerenciamento de processo)
- Certbot (SSL/HTTPS)
- AWS Lightsail (servidor Ubuntu)

**Páginas:**
- `app.py` — Home: KPIs, tendência de temperatura, mapa SC
- `1_Temperatura.py` — Rankings, tendência regional, heatmap de anomalia
- `2_Precipitacao.py` — Acumulados, distribuição, heatmap diário
- `3_Alertas.py` — Severidade, tipos, tabela filtrável
- `4_Horario.py` — Perfil horário, dia vs média 30d
- `5_Cidades.py` — Perfil completo por município
- `6_Comparativo.py` — Comparativo de cidades, "quando choveu", dia vs histórico

**Deploy:**
```bash
# systemd unit: weather-streamlit.service
# Nginx: proxy para 127.0.0.1:8501 com WebSocket support
# SSL: certbot --nginx -d weather.jeysel.dev
```

### 📊 Métricas
- Uptime: > 99% (restart automático via systemd)
- Tempo resposta (cache): < 1s
- Tempo resposta (cold): < 5s
- Municípios disponíveis: 295 (todos os municípios de SC)

---

## 📈 Priorização Features

| Feature | Valor Negócio | Esforço | Prioridade | Status |
|---------|---------------|---------|------------|--------|
| Feature 1: Ingestão | Alto | Médio | P0 | ✅ |
| Feature 2: ELT + Quality | Alto | Alto | P0 | ✅ |
| Feature 3: Dashboard Streamlit | Alto | Médio | P0 | ✅ |

**Critérios priorização:**
- P0: Essencial (MVP não funciona sem)
- P1: Importante (valor alto, pode adiar)
- P2: Desejável (nice-to-have)

---

## 🔄 Backlog Futuro

### Features Não Implementadas (Backlog)

**Feature 4: Previsão Climática (ML)**  
**Prioridade:** P1  
Implementar modelo ML para previsão temperatura/precipitação próximos 7 dias.

**Feature 5: Notificações Automáticas**  
**Prioridade:** P2  
Enviar alertas email/Slack quando anomalias detectadas.

**Feature 6: API REST Pública**  
**Prioridade:** P2  
Expor dados via API REST para consumo externo.

---

**Última atualização:** Abril 2026