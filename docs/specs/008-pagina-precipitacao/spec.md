# Página Precipitação — migração Streamlit → FastAPI

## Tipo
[x] Refatoração (migração de página) + [x] Spec retroativa (documenta o
comportamento atual da página Streamlit antes de replicá-lo)

## Status
[x] implementado — página Precipitação no FastAPI, validada em produção.

## Resumo
Migrar `streamlit/pages/2_Precipitacao.py` para a rota FastAPI
(`/precipitacao`) com template Jinja2 de esqueleto + módulo TypeScript que
busca dado via `/api/v1/*` e renderiza os gráficos com ECharts, conforme
[[006-arquitetura-frontend-fastapi]].

## Contexto
A página Precipitação hoje, em Streamlit, mostra:

- **Filtros na sidebar:** `Mesorregião` (selectbox — `"Todas"` + lista do
  seed `locations`) e `Período (dias)` (slider 7–90, passo 7, default 30).
- **Título:** `🌧️ Precipitação` (sem caption de data — divergência das
  outras páginas, ver Casos de borda).
- **Ranking de municípios mais chuvosos (col. esquerda, ~75% largura):**
  `SUM(precipitation_mm)` acumulado + contagem de `dias_chuva`
  (`precipitation_mm > 0`). Limite **20** quando `Mesorregião = Todas`,
  **300** (efetivamente todos) quando uma mesorregião está selecionada.
  Subtítulo muda: `Top 20 — últimos N dias` vs `{meso} — últimos N dias`.
- **Distribuição por intensidade (col. direita, ~25%):** pizza de
  `COUNT(*)` por `precipitation_class`, com os rótulos traduzidos por
  `CLASS_LABELS_PT` e cores fixas por classe.
- **Heatmap de precipitação média diária por mesorregião — últimos N
  dias:** `AVG(precipitation_mm)` por `date` × `mesoregion`. **Ignora** o
  filtro de mesorregião (sempre todas).

## Investigação (retroativa)

Filtros e âncora (`streamlit/pages/2_Precipitacao.py:6-20`):

```python
meso = st.selectbox("Mesorregião", ["Todas"] + _meso_list)
days = st.slider("Período (dias)", 7, 90, 30, step=7)
meso_clause = f"AND mesoregion = '{meso}'" if meso != "Todas" else ""
_max_daily = max_date("mart_climate__daily_facts")
```

Ranking de chuvosos (limite dinâmico):

```python
limit = 20 if meso == "Todas" else 300
```
```sql
SELECT city_name, mesoregion,
       ROUND(SUM(precipitation_mm), 1)                  AS total_mm,
       COUNT(CASE WHEN precipitation_mm > 0 THEN 1 END) AS dias_chuva
FROM mart_climate__daily_facts
WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
  {meso_clause}
GROUP BY city_name, mesoregion
ORDER BY total_mm DESC
LIMIT {limit}
```

Distribuição por intensidade + tradução (`utils/labels.py`):

```sql
SELECT precipitation_class, COUNT(*) AS qtd
FROM mart_climate__daily_facts
WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
  {meso_clause}
GROUP BY precipitation_class
ORDER BY qtd DESC
```
```python
CLASS_LABELS_PT = {"dry":"Seco","light":"Leve","moderate":"Moderado",
                   "heavy":"Forte","extreme":"Extremo"}
CLASS_COLORS = {"dry":"#78909C","light":"#4FC3F7","moderate":"#0288D1",
                "heavy":"#1565C0","extreme":"#4A148C"}
```

Heatmap (note: **sem `{meso_clause}`**):

```sql
SELECT date, mesoregion, ROUND(AVG(precipitation_mm), 1) AS avg_precip
FROM mart_climate__daily_facts
WHERE date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
GROUP BY date, mesoregion
ORDER BY date
```

## Requirements (EARS)

### Funcionais
- THE system SHALL servir `GET /precipitacao`, renderizando
  `precipitacao.html` (esqueleto, elementos-alvo vazios: ranking, pizza,
  heatmap).
- THE system SHALL registrar a entrada de menu **"Precipitação"** (ícone
  `🌧️`) na posição 2, a partir da estrutura central de rotas.
- THE system SHALL expor `GET /api/v1/precipitacao/ranking` com parâmetros
  `meso` (opcional) e `days` (7–90), retornando `total_mm`
  (`SUM(precipitation_mm)`) e `dias_chuva` por município. WHEN `meso = Todas`
  ou ausente, THE system SHALL limitar a **20** resultados; WHEN uma
  mesorregião específica é passada, THE system SHALL retornar **todos** os
  municípios dela (paridade com o `LIMIT 300` atual).
- THE system SHALL expor `GET /api/v1/precipitacao/intensidade` com `meso`
  (opcional) e `days`, retornando `COUNT(*)` por `precipitation_class`
  (valor cru). O rótulo PT (`CLASS_LABELS_PT`) e a cor por classe vêm do
  módulo `web/src/labels.ts` de [[014-camada-referencia]] no cliente — a
  tradução não pode sumir, mas também não é reimplementada aqui.
- THE system SHALL expor `GET /api/v1/precipitacao/heatmap-mesorregiao`
  com `days`, retornando `AVG(precipitation_mm)` por `date` × `mesoregion`
  para **todas** as mesorregiões (sem filtro `meso`, paridade).
- THE frontend SHALL obter a lista de mesorregiões (selectbox) e a
  `max_date` de `mart_climate__daily_facts` dos endpoints
  `/api/v1/ref/mesorregioes` e `/api/v1/ref/daily-meta` de
  [[014-camada-referencia]].
- FOR paridade de filtros: `Mesorregião` e `Período (dias)` (7–90, passo 7,
  default 30) SHALL existir com a mesma semântica, **incluindo** a regra do
  limite dinâmico do ranking (20 vs todos).
- FOR paridade de métricas: `SUM(precipitation_mm)`, contagem de dias com
  chuva, `COUNT(*)` por classe de intensidade e `AVG(precipitation_mm)`
  diária por mesorregião SHALL estar presentes.
- THE subtítulo do ranking SHALL refletir o filtro ativo
  (`Top 20 — últimos N dias` vs `{meso} — últimos N dias`).

### Não-funcionais
- Janela de data ancorada em `max_date('mart_climate__daily_facts')` via
  `/api/v1/ref/daily-meta` ([[014-camada-referencia]]).
- Rotas síncronas (`def`), cliente BigQuery reutilizado.
- `meso` validado contra a lista fechada do seed; `days` numérico 7–90.
- Os rótulos (`CLASS_LABELS_PT`) e cores (`CLASS_COLORS`) por classe de
  intensidade (`dry`…`extreme`) SHALL vir exclusivamente de
  `web/src/labels.ts` ([[014-camada-referencia]]) — esta página não define
  o dicionário localmente (hoje o Streamlit o repete entre esta página e a
  `5_Cidades.py`).

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Limite do ranking resolvido no servidor a partir de `meso` | Frontend pedir sempre "todos" e cortar no cliente | Paridade exata e menos dado trafegado; a regra "20 quando Todas, todos quando filtrado" é do domínio, fica no endpoint. |
| `CLASS_LABELS_PT` / cores por classe consumidos de `web/src/labels.ts` ([[014-camada-referencia]]) | Repetir o dicionário em cada `*.ts` de página | O `CLAUDE.md`/spec 006 valorizam fonte única; hoje o Streamlit já repete `CLASS_COLORS` em 2 páginas — a spec 014 corrige isso de vez. |
| Pizza de intensidade → **pie** ECharts | Donut / barra empilhada | O gráfico atual é `px.pie`; manter pizza com o mesmo mapa de cores. |

### Componentes afetados
| Rota | Endpoint(s) JSON | Template Jinja2 | Módulo TS | Gráfico(s) ECharts |
|---|---|---|---|---|
| `/precipitacao` | `/api/v1/precipitacao/ranking`, `/api/v1/precipitacao/intensidade`, `/api/v1/precipitacao/heatmap-mesorregiao` (+ `/api/v1/ref/mesorregioes`, `/api/v1/ref/daily-meta` de [[014-camada-referencia]]) | `precipitacao.html` | `web/src/pages/precipitacao.ts` (+ `web/src/labels.ts` de [[014-camada-referencia]]) | Ranking de chuvosos → **bar** horizontal, cor por `mesoregion`, tooltip com `dias_chuva`; Distribuição por intensidade → **pie** com `color` fixo por classe; Precipitação média diária por mesorregião → **heatmap** (`visualMap` sequencial azul) |

## Casos de borda
- **Sem caption de data hoje** — a página Streamlit não mostra
  `Dados disponíveis até …` (as outras mostram). A versão nova SHOULD
  adicionar a caption por consistência, mas isso é melhoria, não bloqueio
  de paridade; decidir na implementação.
- **Mesorregião sem dado no período** → Streamlit mostra
  `Sem dados para {meso}…` implícito (gráfico não desenha). Endpoint
  retorna vazio; frontend mostra aviso equivalente.
- **`precipitation_class` nulo / fora do dicionário** → hoje `.map()`
  deixaria `NaN`; a versão nova SHALL usar fallback para o valor cru (mesmo
  padrão de `fillna(...)` usado nas páginas de alertas).
- **Ranking com mesorregião selecionada retornando centenas de linhas** →
  o gráfico cresce em altura (`bar_height = max(520, len(top) * 22)`);
  replicar a altura dinâmica no ECharts.
- **Pipeline atrasado** → âncora em `max_date()`.

## Fora do escopo
- Trocar a pizza por outro tipo de gráfico.
- Adicionar filtro por classe de intensidade (não existe hoje).
- Mudanças em models dbt / `mart_climate__daily_facts`.

## Referências de código
- `streamlit/pages/2_Precipitacao.py` — página de origem.
- `streamlit/utils/labels.py` — `CLASS_LABELS_PT`.
- `streamlit/utils/bigquery.py` — `query()`, `tbl()`, `max_date()`.
- `streamlit/app.py:187` — entrada de menu atual (`Precipitação`, `🌧️`).
- `docs/specs/006-arquitetura-frontend-fastapi/spec.md` — arquitetura.
- `docs/specs/014-camada-referencia/spec.md` — endpoints `ref/*` e
  `web/src/labels.ts`.

## Ver também
- [[006-arquitetura-frontend-fastapi]] — spec fundacional.
- [[014-camada-referencia]] — define `/api/v1/ref/mesorregioes`,
  `/api/v1/ref/daily-meta` e `web/src/labels.ts` que esta página consome.
- [[007-pagina-temperatura]] — mesma dupla de filtros, mesmos endpoints de
  referência.
- [[009-pagina-alertas]] — usa `utils/labels.py` (padrão de tradução de
  enum compartilhado).
- [[010-pagina-horario]] — precipitação horária.
- [[011-pagina-cidades]] — reusa `CLASS_LABELS_PT` / cores por classe.
- [[012-pagina-comparativo]] — heatmap de chuva por município (tab "Quando
  Choveu").
- [[013-pagina-relatorio-cidade]] — precipitação acumulada tabular.
