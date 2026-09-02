# Página Comparativo — migração Streamlit → FastAPI

## Tipo
[x] Refatoração (migração de página) + [x] Spec retroativa (documenta o
comportamento atual da página Streamlit antes de replicá-lo)

## Status
[x] proposta — nenhum código de `api/` ou `web/` escrito.

## Resumo
Migrar `streamlit/pages/6_Comparativo.py` para a rota FastAPI
(`/comparativo`) com template Jinja2 de esqueleto + módulo TypeScript que
busca dado via `/api/v1/*` e renderiza as 3 abas com ECharts, conforme
[[006-arquitetura-frontend-fastapi]]. É a página com mais filtros do
dashboard.

## Contexto
A página Comparativo ("Análise Comparativa") hoje, em Streamlit, tem os
filtros **no corpo de cada aba** (não na sidebar) e 3 abas independentes:

### Aba 1 — `🌡️ Comparativo de Cidades`
- Filtros: `Cidade A` (default Florianópolis), `Cidade B` (default Lages),
  `Cidade C (opcional)` (`"—"` + lista; default Chapecó), `Métrica`
  (`Temp Máxima` / `Temp Mínima` / `Temp Média` / `Precipitação Diária`),
  `Dias` (slider 7–180, passo 7, default 30).
- Gráfico: linha temporal multi-cidade da métrica escolhida.
- Tabela resumo: por cidade, `Mínimo` / `Máximo` / `Média` da métrica.

### Aba 2 — `🌧️ Quando Choveu`
- Filtros: `Mesorregião` (lista do seed, **sem** `"Todas"`), `Dias`
  (slider 14–60, passo 7, default 30).
- Gráfico: heatmap município × dia de `SUM(precipitation_mm)` diária, com
  escala de cor customizada por faixa (Seco/Leve/Moderado/Forte/Extremo,
  `zmax=80`). Caption explicando as faixas.

### Aba 3 — `📈 Dia vs Histórico`
- Filtros: `Município` (default Florianópolis), `Data de referência`
  (selectbox das últimas 60 datas distintas com dado horário para a
  cidade).
- Gráficos: perfil horário de temperatura e de umidade — dia selecionado
  vs **média dos 30 dias anteriores** (`date < selected_date`).
- 3 métricas: `Desvio médio do dia`, `Hora mais quente vs histórico`,
  `Hora mais fria vs histórico` (só quando há histórico).
- Mensagens condicionais: `Sem dados horários disponíveis para {city}.`,
  `Sem dados horários para {city} em {date}.`

Âncora comum: `max_date("mart_climate__daily_facts")` (abas 1 e 2). A aba 3
ancora nas datas reais retornadas pela `hourly_facts` da cidade.

## Investigação (retroativa)

Dados de referência e âncora (`streamlit/pages/6_Comparativo.py:9-22`):

```python
_cities_df = query(f"SELECT city_name FROM {tbl('locations', seeds=True)} ORDER BY city_name")
_meso_df   = query(f"""SELECT DISTINCT mesoregion FROM {tbl('locations', seeds=True)}
                       WHERE mesoregion IS NOT NULL ORDER BY mesoregion""")
_max_daily = max_date("mart_climate__daily_facts")
```

Aba 1 — mapa de métrica + query:

```python
METRIC = {
  "Temp Máxima": ("temp_max_c","Temperatura Máxima (°C)"),
  "Temp Mínima": ("temp_min_c","Temperatura Mínima (°C)"),
  "Temp Média":  ("temp_avg_c","Temperatura Média (°C)"),
  "Precipitação Diária": ("precipitation_mm","Precipitação (mm)"),
}
```
```sql
SELECT date, city_name, ROUND({col}, 1) AS valor
FROM mart_climate__daily_facts
WHERE city_name IN ({cities_sql})
  AND date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {comp_days} DAY)
ORDER BY date, city_name
```
Tabela resumo: `comp_df.groupby("city_name")["valor"].agg(Mínimo="min", Máximo="max", Média="mean").round(1)`.

Aba 2 — chuva por município:

```sql
SELECT date, city_name, ROUND(SUM(precipitation_mm), 1) AS precipitation_mm
FROM mart_climate__daily_facts
WHERE mesoregion = '{meso_w}'
  AND date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {wet_days} DAY)
GROUP BY date, city_name
ORDER BY city_name, date
```
Escala de cor: faixas `0 / 0.01 / 0.15 / 0.40 / 1.00` de `zmax=80`,
`ticktext=["Seco","Leve","Moderado","Forte","Extremo"]`.

Aba 3 — datas disponíveis, dia atual e histórico:

```sql
SELECT DISTINCT date FROM mart_climate__hourly_facts
WHERE city_name = '{city_h}' ORDER BY date DESC LIMIT 60
```
```sql
-- atual
SELECT hour, ROUND(AVG(temperature_c),1) AS temp, ROUND(AVG(relative_humidity_pct),1) AS humidity
FROM mart_climate__hourly_facts
WHERE city_name = '{city_h}' AND date = DATE '{selected_date}'
GROUP BY hour ORDER BY hour
```
```sql
-- histórico: 30 dias ANTES da data de referência
SELECT hour, ROUND(AVG(temperature_c),1) AS avg_temp, ROUND(AVG(relative_humidity_pct),1) AS avg_humidity
FROM mart_climate__hourly_facts
WHERE city_name = '{city_h}'
  AND date >= DATE_SUB(DATE '{selected_date}', INTERVAL 30 DAY)
  AND date <  DATE '{selected_date}'
GROUP BY hour ORDER BY hour
```
Métricas: `merged["diff_temp"] = (temp - avg_temp).round(1)`, depois
`mean` / `max` / `min`.

Nenhum uso de `utils/labels.py`. Defaults de cidade hardcoded via
`_idx("Florianópolis")` / `_idx("Lages")` / `_idx("Chapecó")`.

## Requirements (EARS)

### Funcionais
- THE system SHALL servir `GET /comparativo`, renderizando
  `comparativo.html` (esqueleto das 3 abas, com os filtros de cada aba no
  corpo — não numa sidebar — e os alvos de gráfico vazios).
- THE system SHALL registrar a entrada de menu **"Comparativo"** (ícone
  `🔍`) na posição 6, a partir da estrutura central de rotas.
- THE system SHALL expor `GET /api/v1/comparativo/cidades-serie` com
  parâmetros `cities` (2 a 3 nomes), `metric`
  (`temp_max|temp_min|temp_avg|precip`) e `days` (7–180), retornando
  `valor` por `date` × `city_name` + o resumo `min`/`max`/`mean` por cidade.
- THE system SHALL expor `GET /api/v1/comparativo/chuva-heatmap` com
  `meso` (obrigatório, sem `"Todas"`) e `days` (14–60), retornando
  `SUM(precipitation_mm)` por `date` × `city_name`.
- THE system SHALL expor `GET /api/v1/comparativo/datas-disponiveis` com
  `city`, retornando as últimas **60** datas distintas com dado em
  `mart_climate__hourly_facts`.
- THE system SHALL expor `GET /api/v1/comparativo/dia-vs-historico` com
  `city` e `date`, retornando o perfil horário (`temp`, `humidity`) do dia
  **e** a média horária dos **30 dias anteriores** (`avg_temp`,
  `avg_humidity`), mais o resumo de desvio (`médio`, `máx`, `mín`).
- THE frontend SHALL obter as listas de referência (`city_name` do seed,
  mesorregiões) e a `max_date` de `mart_climate__daily_facts` dos endpoints
  `/api/v1/ref/cidades`, `/api/v1/ref/mesorregioes` e
  `/api/v1/ref/daily-meta`, definidos em [[014-camada-referencia]] — esta
  spec não os redefine.
- FOR paridade de filtros: **todos** os filtros das 3 abas — Cidade A/B/C,
  Métrica (4 opções), Dias (3 ranges distintos: 7–180 / 14–60 / n/a),
  Mesorregião (sem "Todas"), Município, Data de referência — SHALL existir
  com a mesma semântica e os mesmos defaults (Florianópolis / Lages /
  Chapecó).
- FOR paridade de métricas: série comparativa por métrica, resumo
  min/máx/média por cidade, heatmap de chuva por município, perfis horários
  dia-vs-histórico e os 3 deltas de desvio SHALL estar presentes.

### Não-funcionais
- Abas 1 e 2 ancoram em `max_date('mart_climate__daily_facts')` via
  `/api/v1/ref/daily-meta` ([[014-camada-referencia]]); a aba 3 ancora nas
  datas reais da `hourly_facts` do município (endpoint próprio
  `datas-disponiveis`, não a camada de referência).
- Rotas síncronas (`def`); cliente BigQuery reutilizado.
- `cities`/`city`/`meso` validados contra as listas de referência;
  `metric` contra a lista fechada; `days` e `date` validados numericamente
  / como data ISO dentro do range disponível.
- A janela "histórico" da aba 3 SHALL ser estritamente
  `[date - 30d, date)` — **exclui** o próprio dia (paridade com
  `date < DATE '{selected_date}'`).

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| 4 endpoints, 1 por bloco de dado das 3 abas (aba 3 usa 2) | 1 endpoint por aba | A aba 3 tem 2 datasets com filtros diferentes (lista de datas vs perfis); as abas são independentes e carregadas sob demanda ao abrir cada uma. |
| Resumo `min/max/mean` calculado no servidor junto com a série | Cliente agrega (como o `groupby` pandas hoje) | Menos lógica no TS; garante paridade numérica com `.round(1)`. |
| Filtros no corpo da página (não sidebar) | Padronizar tudo em sidebar como as outras páginas | Paridade — a refatoração `cf5b614` moveu os filtros desta página para o corpo de propósito; manter. |
| Heatmap da aba 2 → **heatmap** ECharts com `visualMap` por faixas (`pieces`) | `visualMap` contínuo | Reproduz as faixas nomeadas Seco→Extremo e a caption; `pieces` mapeia faixa→cor→rótulo diretamente. |
| Aba 3 → **line** com 2 séries por gráfico (dia vs média 30d) | Área/banda de referência | Paridade: hoje são 2 `go.Scatter` (linha cheia + linha pontilhada). |

### Componentes afetados
| Rota | Endpoint(s) JSON | Template Jinja2 | Módulo TS | Gráfico(s) ECharts |
|---|---|---|---|---|
| `/comparativo` | `/api/v1/comparativo/cidades-serie`, `/api/v1/comparativo/chuva-heatmap`, `/api/v1/comparativo/datas-disponiveis`, `/api/v1/comparativo/dia-vs-historico` (+ `/api/v1/ref/cidades`, `/api/v1/ref/mesorregioes`, `/api/v1/ref/daily-meta` de [[014-camada-referencia]]) | `comparativo.html` | `web/src/pages/comparativo.ts` | Aba 1 → **line** multi-série + **tabela HTML** de resumo; Aba 2 → **heatmap** município×dia, `visualMap.pieces` (Seco→Extremo); Aba 3 → 2× **line** (temp, umidade) com série "dia" e série "média 30d" + 3 tiles de delta |

## Casos de borda
- **Cidade C = "—"** → não entra no `IN (...)`; a série tem 2 cidades.
- **Cidades A e B iguais** → hoje o Streamlit não impede; a série
  colapsa numa linha. Replicar (não validar contra duplicata; fora do
  escopo).
- **Aba 2 sem dado para a mesorregião/período** →
  `Sem dados para {meso} no período selecionado.`
- **Aba 3, cidade sem dado horário** →
  `Sem dados horários disponíveis para {city}.`
- **Aba 3, data de referência sem dado horário** →
  `Sem dados horários para {city} em {date}.`
- **Aba 3 sem histórico** (data de referência é a mais antiga) → gráficos
  só com a linha do dia; os 3 deltas **não** são exibidos (paridade com
  `if not hist.empty`).
- **Pipeline atrasado** → abas 1/2 ancoram em `max_date()`; aba 3 usa
  datas reais.

## Fora do escopo
- Impedir seleção de cidades duplicadas nas abas 1/3.
- Adicionar "Todas" ao filtro de mesorregião da aba 2.
- Permitir janela de histórico configurável na aba 3 (fixa em 30 dias).
- Comparar mais de 3 cidades na aba 1.
- Mudanças em models dbt.

## Referências de código
- `streamlit/pages/6_Comparativo.py` — página de origem (3 abas, filtros
  no corpo, defaults de cidade).
- `streamlit/utils/bigquery.py` — `query()`, `tbl()`, `max_date()`.
- `streamlit/app.py:191` — entrada de menu atual (`Comparativo`, `🔍`).
- `docs/specs/006-arquitetura-frontend-fastapi/spec.md` — arquitetura.
- `docs/specs/014-camada-referencia/spec.md` — endpoints `ref/cidades`,
  `ref/mesorregioes`, `ref/daily-meta`.

## Ver também
- [[006-arquitetura-frontend-fastapi]] — spec fundacional.
- [[014-camada-referencia]] — define os endpoints `/api/v1/ref/*` que as
  abas 1 e 2 consomem.
- [[010-pagina-horario]] — a aba 3 usa o mesmo padrão de query horária por
  cidade/hora.
- [[008-pagina-precipitacao]] — faixas de intensidade de chuva
  (Seco→Extremo) aparecem nas duas.
- [[011-pagina-cidades]] — perfil de um município; esta compara vários.
- [[007-pagina-temperatura]] / [[009-pagina-alertas]] /
  [[013-pagina-relatorio-cidade]] — demais páginas da sequência.
