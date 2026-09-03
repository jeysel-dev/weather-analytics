# Página Temperatura — migração Streamlit → FastAPI

## Tipo
[x] Refatoração (migração de página) + [x] Spec retroativa (documenta o
comportamento atual da página Streamlit antes de replicá-lo)

## Status
[x] implementado — página Temperatura no FastAPI, validada em produção. Esta
spec fixou a paridade de filtros/métricas que a versão FastAPI preservou.

## Resumo
Migrar `streamlit/pages/1_Temperatura.py` para uma rota FastAPI (`/temperatura`)
com template Jinja2 de esqueleto + módulo TypeScript que busca dado via
endpoints `/api/v1/*` e renderiza os gráficos com ECharts, seguindo a
arquitetura da spec [[006-arquitetura-frontend-fastapi]].

## Contexto
A página Temperatura hoje, em Streamlit, mostra:

- **Filtros na sidebar:** `Mesorregião` (selectbox — `"Todas"` + lista lida
  do seed `locations`) e `Período (dias)` (slider 7–90, passo 7, default 30).
- **Título + caption:** `🌡️ Temperatura` e `Dados disponíveis até {max_date}`.
- **Dois rankings lado a lado (sempre 7 dias, independentemente do slider):**
  - `🔥 Municípios mais quentes — 7 dias`: top 10 por média de `temp_max_c`.
  - `❄️ Municípios mais frios — 7 dias`: top 10 por média de `temp_min_c`.
- **Tendência de temperatura média por mesorregião — últimos N dias:** uma
  linha por mesorregião, `AVG(temp_avg_c)` por dia. Respeita o filtro de
  mesorregião (uma linha só se um filtro estiver ativo).
- **Heatmap de anomalia térmica por mesorregião — últimos N dias:**
  `AVG(temp_anomaly_c)` por dia × mesorregião. **Ignora** o filtro de
  mesorregião (sempre mostra todas). Caption:
  `Positivo (vermelho) = mais quente que a média 30d · Negativo (azul) = mais frio`.

Comportamento especial: o slider `Período (dias)` **não** afeta os dois
rankings — eles são fixos em 7 dias. Só a tendência e o heatmap usam `N`.

## Investigação (retroativa)

Filtros e âncora de data (`streamlit/pages/1_Temperatura.py:6-23`):

```python
_meso_df = query(f"""
SELECT DISTINCT mesoregion
FROM {tbl('locations', seeds=True)}
WHERE mesoregion IS NOT NULL
ORDER BY mesoregion
""")
...
meso = st.selectbox("Mesorregião", ["Todas"] + _meso_list)
days = st.slider("Período (dias)", 7, 90, 30, step=7)
meso_clause = f"AND mesoregion = '{meso}'" if meso != "Todas" else ""
_max_daily = max_date("mart_climate__daily_facts")
```

Ranking dos mais quentes (mais frios é simétrico, `temp_min_c` + `ASC`):

```sql
SELECT city_name, mesoregion, ROUND(AVG(temp_max_c), 1) AS media_max
FROM mart_climate__daily_facts
WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL 7 DAY)
  {meso_clause}
GROUP BY city_name, mesoregion
ORDER BY media_max DESC
LIMIT 10
```

Tendência por mesorregião:

```sql
SELECT date, mesoregion, ROUND(AVG(temp_avg_c), 1) AS temp_avg
FROM mart_climate__daily_facts
WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
  {meso_clause}
GROUP BY date, mesoregion
ORDER BY date
```

Heatmap de anomalia (note: **sem `{meso_clause}`**):

```sql
SELECT date, mesoregion, ROUND(AVG(temp_anomaly_c), 2) AS anomaly
FROM mart_climate__daily_facts
WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
GROUP BY date, mesoregion
ORDER BY date
```

Não há uso de `utils/labels.py` nesta página — nenhuma tradução de
enum/classe. A única formatação é numérica (`ROUND(...)` no SQL,
`%{text:.1f}°C` no rótulo das barras).

## Requirements (EARS)

### Funcionais
- THE system SHALL servir a página em `GET /temperatura`, renderizando o
  template Jinja2 `temperatura.html` com o esqueleto HTML e os elementos-alvo
  de gráfico vazios (rankings, tendência, heatmap) — sem dado no HTML.
- THE system SHALL registrar a entrada de menu **"Temperatura"** (ícone
  `🌡️`) na posição 1 (primeiro item após a Home), a partir da mesma
  estrutura central que define a rota — conforme [[006-arquitetura-frontend-fastapi]].
- THE system SHALL expor `GET /api/v1/temperatura/rankings` que retorna, em
  JSON, os 10 municípios mais quentes (`AVG(temp_max_c)`) e os 10 mais frios
  (`AVG(temp_min_c)`) na janela **fixa de 7 dias** ancorada em
  `max_date('mart_climate__daily_facts')`. WHEN o parâmetro `meso` é
  fornecido e diferente de `Todas`, THE system SHALL filtrar por
  `mesoregion = :meso`.
- THE system SHALL expor `GET /api/v1/temperatura/tendencia-mesorregiao`
  com parâmetros `meso` (opcional) e `days` (7–90), retornando
  `AVG(temp_avg_c)` por `date` × `mesoregion` na janela de `days` dias.
- THE system SHALL expor `GET /api/v1/temperatura/anomalia` com parâmetro
  `days` (7–90), retornando `AVG(temp_anomaly_c)` por `date` × `mesoregion`
  para **todas** as mesorregiões (o filtro `meso` não se aplica a este
  endpoint, paridade com o Streamlit).
- THE frontend SHALL obter a lista de mesorregiões (para o selectbox) e a
  `max_date` de `mart_climate__daily_facts` (para a caption
  `Dados disponíveis até {max_date}`) dos endpoints
  `/api/v1/ref/mesorregioes` e `/api/v1/ref/daily-meta`, definidos em
  [[014-camada-referencia]] — esta spec não redefine esses endpoints.
- FOR paridade de filtros: `Mesorregião` (`Todas` + lista do seed) e
  `Período (dias)` (7–90, passo 7, default 30) SHALL existir na versão nova
  com a mesma semântica — inclusive a de que `days` **não** afeta os
  rankings.
- FOR paridade de métricas: média de `temp_max_c` (ranking quente), média
  de `temp_min_c` (ranking frio), `AVG(temp_avg_c)` por mesorregião
  (tendência) e `AVG(temp_anomaly_c)` (heatmap) SHALL estar presentes.

### Não-funcionais
- THE endpoints SHALL ancorar a janela de data em `max_date()`, nunca em
  `CURRENT_DATE()` (regra de [[006-arquitetura-frontend-fastapi]] e do
  `CLAUDE.md`).
- THE rotas de API SHALL ser síncronas (`def`), reusando o cliente
  BigQuery de `api/utils/bigquery.py`.
- THE parâmetros `meso` e `days` SHALL ser validados no servidor (lista
  fechada de mesorregiões vinda do seed; `days` numérico dentro de 7–90) —
  a query não deve interpolar string livre do cliente.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| 3 endpoints (`rankings`, `tendencia-mesorregiao`, `anomalia`) | 1 endpoint só devolvendo tudo | Cada bloco tem janela/filtro distinto (rankings fixos em 7d e sensíveis a `meso`; heatmap ignora `meso`). Endpoints separados espelham 1:1 as 4 queries atuais e evitam refazer trabalho quando só um filtro muda. |
| Lista de mesorregiões + `max_date` vêm da camada de referência ([[014-camada-referencia]]: `/api/v1/ref/mesorregioes`, `/api/v1/ref/daily-meta`) | Cada página expõe seu próprio endpoint de referência | Várias páginas (007, 008, 009, 012) precisam da mesma lista; endpoint único, definido uma vez na spec 014, evita duplicação e divergência. |
| Rankings: **bar horizontal** no ECharts (`yAxis.type: 'category'`, `series.type: 'bar'`), cor por gradiente do valor | Manter escala de cor contínua Plotly (`Reds` / `Blues_r`) idêntica | ECharts cobre com `visualMap` contínuo; o gradiente vermelho/azul é preservado conceitualmente. |

### Componentes afetados
| Rota | Endpoint(s) JSON | Template Jinja2 | Módulo TS | Gráfico(s) ECharts |
|---|---|---|---|---|
| `/temperatura` | `/api/v1/temperatura/rankings`, `/api/v1/temperatura/tendencia-mesorregiao`, `/api/v1/temperatura/anomalia` (+ `/api/v1/ref/mesorregioes`, `/api/v1/ref/daily-meta` de [[014-camada-referencia]]) | `temperatura.html` | `web/src/pages/temperatura.ts` | Rankings quente/frio → 2× **bar** horizontal com `visualMap` contínuo; Tendência por mesorregião → **line** multi-série; Anomalia térmica → **heatmap** (`visualMap` divergente centrado em 0, vermelho↔azul) |

## Casos de borda
- **Pipeline atrasado / janela sem dado** → âncora em
  `max_date('mart_climate__daily_facts')`; a caption informa a data real.
- **Mesorregião sem dado no período** (ex.: filtro ativo + janela curta) →
  endpoint retorna lista vazia; o frontend renderiza o container do gráfico
  vazio com aviso "sem dados para esta mesorregião" (paridade com o
  comportamento do Streamlit, que simplesmente não desenha o gráfico).
- **`days` fora de 7–90** → clamp/validação no servidor (o slider já
  limitava; a URL do endpoint pode não).
- **Heatmap com filtro de mesorregião ativo** → o endpoint `anomalia`
  ignora `meso` de propósito (paridade); documentar para não parecer bug.
- **Coluna NUMERIC do BigQuery voltando como `Decimal`** → o
  `api/utils/bigquery.py` herda a conversão para `float` já feita em
  `streamlit/utils/bigquery.py`.

## Fora do escopo
- Alterar o comportamento "rankings fixos em 7 dias" para respeitar o
  slider — é uma mudança de produto, não de migração; replicar como está.
- Adicionar seleção de intervalo de datas absoluto (a página só tem
  "últimos N dias").
- Qualquer mudança em models dbt ou em `mart_climate__daily_facts`.

## Referências de código
- `streamlit/pages/1_Temperatura.py` — página de origem (filtros, 4
  queries, formatação).
- `streamlit/utils/bigquery.py` — `query()`, `tbl()`, `max_date()`,
  conversão `Decimal`→`float`; base do `api/utils/bigquery.py`.
- `streamlit/app.py:186` — entrada de menu atual (`Temperatura`, `🌡️`).
- `docs/specs/006-arquitetura-frontend-fastapi/spec.md` — arquitetura,
  invariantes de rota/menu/endpoint, fail-fast do manifest.

## Ver também
- [[006-arquitetura-frontend-fastapi]] — spec fundacional da migração.
- [[014-camada-referencia]] — define `/api/v1/ref/mesorregioes` e
  `/api/v1/ref/daily-meta` que esta página consome.
- [[008-pagina-precipitacao]] — mesma dupla de filtros (`meso` + `days`),
  compartilha os endpoints de referência.
- [[009-pagina-alertas]] — compartilha lista de mesorregiões.
- [[010-pagina-horario]] — próxima página da sequência.
- [[011-pagina-cidades]] — perfil por município (temperatura por cidade).
- [[012-pagina-comparativo]] — comparativo de temperatura entre cidades.
- [[013-pagina-relatorio-cidade]] — relatório tabular por cidade.
