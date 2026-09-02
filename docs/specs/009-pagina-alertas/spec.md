# Página Alertas — migração Streamlit → FastAPI

## Tipo
[x] Refatoração (migração de página) + [x] Spec retroativa (documenta o
comportamento atual da página Streamlit antes de replicá-lo)

## Status
[x] proposta — nenhum código de `api/` ou `web/` escrito.

## Resumo
Migrar `streamlit/pages/3_Alertas.py` para a rota FastAPI (`/alertas`) com
template Jinja2 de esqueleto + módulo TypeScript que busca dado via
`/api/v1/*` e renderiza KPIs, gráficos ECharts e tabela, conforme
[[006-arquitetura-frontend-fastapi]].

## Contexto
A página Alertas hoje, em Streamlit, mostra:

- **Filtros na sidebar (nesta ordem):** `Período (dias)` (slider 7–60,
  passo 7, default 30 — **range diferente** das páginas 007/008),
  `Mesorregião` (`"Todas"` + lista do seed), `Severidade` (selectbox
  `["Todas", "critical", "high", "medium", "low"]` — valores crus em
  inglês, sem tradução no filtro).
- **Título + caption:** `🚨 Alertas Climáticos` /
  `Dados disponíveis até {max_alerts}`.
- **Linha de 5 KPIs:** Total, `🔴 Críticos`, `🟠 Altos`, `🟡 Médios`,
  `🟢 Baixos` (contagens por severidade).
- **Por tipo de alerta (col. esquerda):** barra horizontal empilhada,
  `COUNT(*)` por `alert_type` × `severity`; `alert_type` traduzido por
  `ALERT_TYPE_PT`, `severity` por `SEVERITY_PT`, cor fixa por severidade.
- **Municípios mais afetados (col. direita):** barra horizontal,
  `COUNT(*)` por município; limite **15** quando `Mesorregião = Todas`,
  **300** quando filtrado.
- **Tabela de alertas recentes — últimos N dias:** até 200 linhas, ordenada
  por `date DESC, severity ASC`; colunas: Data, Município, Mesorregião,
  Tipo (traduzido), Severidade (ícone + PT), Temp Máx, Anomalia, Precip,
  Vento, UV Máx. Mensagem condicional quando vazia:
  `Nenhum alerta encontrado no período e filtros selecionados.`

## Investigação (retroativa)

Filtros, âncora e `WHERE` base (`streamlit/pages/3_Alertas.py:23-36`):

```python
days = st.slider("Período (dias)", 7, 60, 30, step=7)
meso = st.selectbox("Mesorregião", ["Todas"] + _meso_list)
severity = st.selectbox("Severidade", ["Todas", "critical", "high", "medium", "low"])

meso_clause = f"AND mesoregion = '{meso}'" if meso != "Todas" else ""
sev_clause  = f"AND severity = '{severity}'" if severity != "Todas" else ""
_max_alerts = max_date("mart_climate__alerts")
base_where  = f"""
  date >= DATE_SUB(DATE '{_max_alerts}', INTERVAL {days} DAY)
  {meso_clause}
  {sev_clause}
"""
```

KPIs:

```sql
SELECT COUNT(*) AS total,
  COUNTIF(severity = 'critical') AS critical,
  COUNTIF(severity = 'high')     AS high,
  COUNTIF(severity = 'medium')   AS medium,
  COUNTIF(severity = 'low')      AS low
FROM mart_climate__alerts
WHERE {base_where}
```

Por tipo × severidade:

```sql
SELECT alert_type, severity, COUNT(*) AS qtd
FROM mart_climate__alerts
WHERE {base_where}
GROUP BY alert_type, severity
ORDER BY qtd DESC
```

Municípios mais afetados (`city_limit = 15 if meso == "Todas" else 300`):

```sql
SELECT city_name, mesoregion, COUNT(*) AS alertas
FROM mart_climate__alerts
WHERE {base_where}
GROUP BY city_name, mesoregion
ORDER BY alertas DESC
LIMIT {city_limit}
```

Tabela recente:

```sql
SELECT date, city_name, mesoregion, alert_type, severity,
  ROUND(temp_max_c, 1) AS temp_max, ROUND(temp_anomaly_c, 1) AS anomalia,
  ROUND(precipitation_mm, 1) AS precip, ROUND(wind_speed_max_kmh, 1) AS vento_max,
  uv_index_max
FROM mart_climate__alerts
WHERE {base_where}
ORDER BY date DESC, severity ASC
LIMIT 200
```

Traduções (`utils/labels.py`) + cores/ícones locais da página:

```python
ALERT_TYPE_PT = {"cold_anomaly":"Anomalia de Frio","precip_anomaly":"Anomalia de Precipitação",
                 "heat_anomaly":"Anomalia de Calor","heavy_rain":"Chuva Forte"}
SEVERITY_PT   = {"critical":"Crítica","high":"Alta","medium":"Média","low":"Baixa"}
SEV_COLORS = {"critical":"#D32F2F","high":"#F57C00","medium":"#FBC02D","low":"#388E3C"}
SEV_ICON   = {"critical":"🔴","high":"🟠","medium":"🟡","low":"🟢"}
```
Ambos `.map(...).fillna(<valor cru>)` — enum desconhecido cai no valor
original.

## Requirements (EARS)

### Funcionais
- THE system SHALL servir `GET /alertas`, renderizando `alertas.html`
  (esqueleto: faixa de KPIs, 2 gráficos, tabela — todos vazios no HTML).
- THE system SHALL registrar a entrada de menu **"Alertas"** (ícone `🚨`)
  na posição 3, a partir da estrutura central de rotas.
- THE system SHALL expor `GET /api/v1/alertas/resumo` (KPIs) com parâmetros
  `days` (7–60), `meso` (opcional), `severity` (opcional; um de
  `critical|high|medium|low`), retornando `total` e a contagem por
  severidade.
- THE system SHALL expor `GET /api/v1/alertas/por-tipo` com os mesmos
  filtros, retornando `COUNT(*)` por `alert_type` × `severity`, com os
  rótulos PT de tipo e severidade na resposta.
- THE system SHALL expor `GET /api/v1/alertas/municipios` com os mesmos
  filtros, retornando `COUNT(*)` por município; **15** resultados quando
  `meso` ausente/`Todas`, **todos** quando `meso` específico (paridade com
  `LIMIT 300`).
- THE system SHALL expor `GET /api/v1/alertas/recentes` com os mesmos
  filtros, retornando até **200** linhas ordenadas por `date DESC,
  severity ASC`, com `alert_type`/`severity` traduzidos e as métricas
  numéricas arredondadas (`temp_max`, `anomalia`, `precip`, `vento_max`,
  `uv_index_max`).
- THE frontend SHALL obter a lista de mesorregiões (selectbox) e a
  `max_date` de `mart_climate__alerts` (caption
  `Dados disponíveis até {max_alerts}`) dos endpoints
  `/api/v1/ref/mesorregioes` e `/api/v1/ref/alerts-meta`, definidos em
  [[014-camada-referencia]] — esta spec não os redefine.
- FOR paridade de filtros: `Período (dias)` (7–60, passo 7, default 30),
  `Mesorregião` e `Severidade` SHALL existir com a mesma semântica; a
  ordem visual dos filtros (dias → mesorregião → severidade) SHALL ser
  preservada.
- FOR paridade de métricas: contagens por severidade (KPIs), `COUNT(*)` por
  tipo × severidade, `COUNT(*)` por município e a tabela de 200 alertas com
  todas as colunas atuais SHALL estar presentes.

### Não-funcionais
- Janela ancorada em `max_date('mart_climate__alerts')` via
  `/api/v1/ref/alerts-meta` ([[014-camada-referencia]]) — tabela **alerts**,
  não daily_facts (âncora própria).
- Rotas síncronas (`def`); cliente BigQuery reutilizado.
- `severity` validada contra a lista fechada; `meso` contra o seed; `days`
  numérico 7–60.
- `ALERT_TYPE_PT` / `SEVERITY_PT` (tradução) e `SEV_COLORS` / `SEV_ICON`
  (apresentação) SHALL vir da camada compartilhada de
  [[014-camada-referencia]]: `api/utils/labels.py` no backend (para a
  tabela de alertas que já sai traduzida) e `web/src/labels.ts` no
  frontend (cor/ícone). Os dois lados SHALL ter os mesmos pares
  chave→valor.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| 4 endpoints (`resumo`, `por-tipo`, `municipios`, `recentes`) | 1 endpoint devolvendo tudo num payload | As 4 queries têm o mesmo `WHERE` mas grãos/limites diferentes; separar mantém o 1:1 com o Streamlit e permite recarregar só a tabela ao paginar no futuro. Todos compartilham os mesmos query params. |
| Tradução de `alert_type`/`severity` no **backend**, usando `api/utils/labels.py` de [[014-camada-referencia]] | Traduzir no frontend TS | A tabela recente e os dois gráficos precisam do rótulo; centralizar no endpoint evita 3 cópias do dicionário no TS. A fonte canônica é a spec 014. |
| Tabela recente → HTML `<table>` no template, populada via `fetch` | Grid component / lib de tabela | Paridade com `st.dataframe`; volume pequeno (≤200 linhas), sem necessidade de virtualização. |
| Ícone + cor por severidade → `web/src/labels.ts` de [[014-camada-referencia]] | Backend devolver emoji | Emoji/cor são apresentação; ficam no frontend, na fonte única da spec 014. |

### Componentes afetados
| Rota | Endpoint(s) JSON | Template Jinja2 | Módulo TS | Visualização |
|---|---|---|---|---|
| `/alertas` | `/api/v1/alertas/resumo`, `/api/v1/alertas/por-tipo`, `/api/v1/alertas/municipios`, `/api/v1/alertas/recentes` (+ `/api/v1/ref/mesorregioes`, `/api/v1/ref/alerts-meta` de [[014-camada-referencia]]) | `alertas.html` | `web/src/pages/alertas.ts` (+ `web/src/labels.ts` de [[014-camada-referencia]]) | KPIs → 5 tiles HTML (sem gráfico); Por tipo de alerta → **bar** horizontal empilhada (`stack`), cor por severidade; Municípios mais afetados → **bar** horizontal, cor por `mesoregion`, altura dinâmica; Alertas recentes → **tabela HTML** |

## Casos de borda
- **Nenhum alerta no período/filtros** → tabela vazia mostra
  `Nenhum alerta encontrado no período e filtros selecionados.`; KPIs
  mostram zeros; gráficos renderizam container vazio (paridade).
- **Pipeline atrasado** → âncora em `max_date('mart_climate__alerts')` —
  `alerts` pode ter `max_date` diferente de `daily_facts`.
- **`severity` inválida na URL** → 422/validação; não interpolar.
- **`alert_type` novo não mapeado em `ALERT_TYPE_PT`** → fallback para o
  valor cru (paridade com `.fillna`).
- **Ordenação `severity ASC`** é alfabética (`critical` < `high` < `low` <
  `medium`), não por gravidade — replicar como está (não "corrigir" na
  migração; fora do escopo).

## Fora do escopo
- Reordenar a tabela por gravidade real de severidade (hoje é alfabético).
- Traduzir os valores do próprio selectbox de severidade (hoje mostra
  `critical`/`high`/… crus).
- Paginação server-side da tabela (200 linhas é suficiente).
- Mudanças em `mart_climate__alerts` ou nos models de alerta.

## Referências de código
- `streamlit/pages/3_Alertas.py` — página de origem.
- `streamlit/utils/labels.py` — `ALERT_TYPE_PT`, `SEVERITY_PT`
  (consolidados em `api/utils/labels.py` + `web/src/labels.ts` pela
  [[014-camada-referencia]]).
- `streamlit/utils/bigquery.py` — `query()`, `tbl()`, `max_date()`.
- `streamlit/app.py:188` — entrada de menu atual (`Alertas`, `🚨`).
- `docs/specs/006-arquitetura-frontend-fastapi/spec.md` — arquitetura.
- `docs/specs/014-camada-referencia/spec.md` — endpoints `ref/*` e
  camada de rótulos.

## Ver também
- [[006-arquitetura-frontend-fastapi]] — spec fundacional.
- [[014-camada-referencia]] — define `/api/v1/ref/mesorregioes`,
  `/api/v1/ref/alerts-meta` e a camada de rótulos que esta página consome.
- [[007-pagina-temperatura]] / [[008-pagina-precipitacao]] — filtros
  `meso`/`days` semelhantes (range de `days` difere aqui).
- [[010-pagina-horario]] — próxima da sequência.
- [[011-pagina-cidades]] — aba de alertas por município (mesmas traduções).
- [[012-pagina-comparativo]] — usa `ALERT_TYPE_PT`/`SEVERITY_PT`.
- [[013-pagina-relatorio-cidade]] — relatório tabular por cidade.
