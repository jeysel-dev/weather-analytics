# Epic: Weather Analytics Platform

## 🎯 Objetivo Estratégico

Criar um pipeline de analytics end-to-end para monitoramento climático em tempo real de localidades brasileiras, permitindo análise histórica, identificação de padrões e detecção de anomalias para tomada de decisão baseada em dados.

---

## 💼 Valor de Negócio

**Problema:**
- Dados climáticos fragmentados em múltiplas fontes
- Dificuldade identificar tendências e anomalias
- Falta de visibilidade tempo real para tomada decisão

**Solução:**
- Pipeline automatizado: ingestão → transformação → visualização
- Testes automatizados garantem confiabilidade
- Dashboard público demonstra capacidades Analytics Engineering

**Impacto:**
- **Analistas:** Acesso insights climáticos confiáveis
- **Gestores:** Dashboards interativos para decisões rápidas
- **Portfolio:** Demonstração competências técnicas (Analytics + Data Quality + CI/CD)

---

## 🚀 Features do Epic

### Feature 1: Ingestão Automatizada de Dados Climáticos
**Prioridade:** Alta  
**Esforço:** Médio  
**Status:** ✅ Concluído

Coletar dados climáticos via API Open-Meteo, armazenar em PostgreSQL e replicar para BigQuery via Airbyte.

**Valor:** Base de dados confiável é pré-requisito para todo pipeline analytics.

---

### Feature 2: Pipeline ELT com Data Quality
**Prioridade:** Alta  
**Esforço:** Alto  
**Status:** ✅ Concluído

Transformar dados brutos em modelo dimensional analytics com camadas staging → intermediate → marts, incluindo 40+ testes automatizados.

**Valor:** Dados transformados + validados = insights confiáveis para decisões críticas.

---

### Feature 3: Dashboard Interativo em Produção
**Prioridade:** Alta  
**Esforço:** Médio  
**Status:** ✅ Concluído

Publicar dashboard Streamlit no AWS Lightsail com Nginx + systemd, servindo 6 páginas analíticas e análise comparativa conectadas diretamente ao BigQuery.

**Valor:** Visualização tempo real com interatividade full-stack democratiza acesso a insights (não apenas analistas técnicos).

---

## ✅ Critérios de Sucesso (Epic Level)

### Critérios Técnicos
- [x] Pipeline completo: API → PostgreSQL → BigQuery → dbt → Dashboard
- [x] 15+ localidades brasileiras monitoradas
- [x] 40+ testes automatizados data quality
- [x] Deploy Streamlit em produção (Nginx + systemd no Lightsail)
- [x] Dashboard acessível via HTTPS com subdomínio dedicado (uptime > 95%)

### Critérios de Negócio
- [x] Dados atualizados diariamente (freshness < 24h)
- [x] Tempo resposta dashboard < 3s (performance)
- [x] Zero alertas críticos data quality (confiabilidade)

### Critérios de Portfolio
- [x] Código documentado (schema.yml completo)
- [x] README profissional com setup reproduzível
- [x] Demonstrar stack moderna (dbt, Airflow, BigQuery, Streamlit)

---

## 📊 Métricas de Sucesso

| Métrica | Target | Atual | Status |
|---------|--------|-------|--------|
| Localidades monitoradas | 15+ | 295 (SC) | ✅ |
| Testes automatizados | 40+ | 49 | ✅ |
| Freshness dados | < 24h | ~12h | ✅ |
| Uptime dashboard | > 95% | 99.8% | ✅ |
| Tempo deploy CI/CD | < 10min | ~6min | ✅ |

---

## 🗓️ Timeline

**Sprint 1 (Semana 1-2):** Ingestão dados
- Setup PostgreSQL + Docker
- Integração API Open-Meteo
- Configuração Airbyte → BigQuery

**Sprint 2 (Semana 3-4):** Transformações dbt
- Camadas staging, intermediate, marts
- Window functions (médias móveis, anomalias)
- Testes data quality

**Sprint 3 (Semana 5-6):** Dashboard em Produção
- Setup Streamlit + BigQuery SDK
- 6 páginas analíticas + análise comparativa
- Deploy Lightsail com Nginx + systemd + SSL

**Sprint 4 (Semana 7):** Refinamento
- Otimizações performance
- Documentação completa
- Testes finais

---

## 🎓 Competências Demonstradas

**Analytics Engineering:**
- Modelagem dimensional (staging → marts)
- dbt avançado (macros, testes, documentação)
- Data quality (49 testes automatizados)

**Data Engineering:**
- Pipeline ELT (Airbyte)
- Cloud data warehouse (BigQuery)
- Orquestração (Airflow + GitHub Actions)

**Product Ownership:**
- Definição valor negócio
- Priorização features (impacto vs esforço)
- Acceptance criteria (BDD)

**DevOps:**
- CI/CD (GitHub Actions)
- Infraestrutura como código
- Monitoramento (freshness checks)

---

## 🔗 Referências

**Código fonte:** https://github.com/jeysel/Analytics-Engineer/tree/main/Weather-Analytics  
**Documentação dbt:** [schema.yml](../dbt/models/schema.yml)

---

**Última atualização:** Abril 2026  
**Status Epic:** ✅ Concluído (em produção)