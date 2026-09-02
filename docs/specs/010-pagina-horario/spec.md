# Página Horário — migração Streamlit → FastAPI

## Tipo
[x] Refatoração (migração de página) + [x] Spec retroativa (documenta o
comportamento atual da página Streamlit antes de replicá-lo)

## Status
[x] proposta — nenhum código de `api/` ou `web/` escrito.

## Resumo
Migrar `streamlit/pages/4_Horario.py` para a rota FastAPI (`/horario`) com
template Jinja2 de esqueleto + módulo TypeScript que busca dado via
`/api/v1/*` e renderiza as 3 abas de gráficos horários com ECharts,
conforme [[006-arquitetura-frontend-fastapi]].

## Contexto
A página Horário ("Padrão Horário") hoje, em Streamlit, é a única que lê de
`mart_climate__hourly_facts`. Mostra:

- **Filtros na sidebar:** `Município` (selectbox — lista de `city_name`
  **distintos que têm dado horário**, vinda da própria `hourly_facts`, não
  do seed) e `Período (dias)` (slider 3–30, passo 1, default 7 — range e
  passo próprios).
- **Âncora de data por município:** `MAX(date)` filtrado por
  `city_name = :city` (não usa o helper global `max_date()`) — cada
  município pode ter uma data máxima diferente.
- **Título/subtítulo:** `🕐 Padrão Horário`, `{city} — últimos N dias`,
  caption `Dados disponíveis até {max_date}`.
- **3 abas (`st.tabs`):**
  - `🌡️ Temperatura & Umidade`: série horária de `temperature_c` +
    `relative_humidity_pct` (dois eixos Y), por `observed_at`.
  - `💨 Vento & Chuva`: série horária de `precipitation_mm` (barra) +
    `wind_speed_kmh` (linha), dois eixos Y.
  - `📊 Padrão 24h`: perfil médio das 24 horas — `AVG` por `hour` de
    temperatura, umidade e precipitação/dia
    (`SUM(precipitation_mm) / NULLIF(COUNT(DISTINCT date), 0)`); 3 eixos Y.
    Caption: `Médias calculadas sobre {days} dias de dados horários.`
- **Mensagens condicionais:** `Selecione um município na barra lateral.`
  (sem seleção), `Sem dados horários para este município.` (sem `max_date`),
  `Sem dados horários para este município no período.` / `Sem dados
  suficientes para calcular o padrão horário.` (query vazia por aba).

## Investigação (retroativa)

Lista de municípios e filtros (`streamlit/pages/4_Horario.py:8-29`):

```python
cities_df = query(f"""
SELECT DISTINCT city_name
FROM {tbl('mart_climate__hourly_facts')}
ORDER BY city_name
""")
...
city = st.selectbox("Município", city_list)
days = st.slider("Período (dias)", 3, 30, 7, step=1)
...
max_date_df = query(f"""
SELECT MAX(date) AS max_date
FROM {tbl('mart_climate__hourly_facts')}
WHERE city_name = '{city}'
""")
```

Aba Temperatura & Umidade:

```sql
SELECT observed_at, temperature_c, relative_humidity_pct
FROM mart_climate__hourly_facts
WHERE city_name = '{city}'
  AND date >= DATE_SUB(DATE '{max_date}', INTERVAL {days} DAY)
ORDER BY observed_at
```

Aba Vento & Chuva:

```sql
SELECT observed_at, wind_speed_kmh, precipitation_mm
FROM mart_climate__hourly_facts
WHERE city_name = '{city}'
  AND date >= DATE_SUB(DATE '{max_date}', INTERVAL {days} DAY)
ORDER BY observed_at
```

Aba Padrão 24h:

```sql
SELECT hour,
  ROUND(AVG(temperature_c), 1)         AS avg_temp,
  ROUND(AVG(relative_humidity_pct), 1) AS avg_humidity,
  ROUND(AVG(wind_speed_kmh), 1)        AS avg_wind,
  ROUND(SUM(precipitation_mm) / NULLIF(COUNT(DISTINCT date), 0), 2) AS avg_precip_dia
FROM mart_climate__hourly_facts
WHERE city_name = '{city}'
  AND date >= DATE_SUB(DATE '{max_date}', INTERVAL {days} DAY)
GROUP BY hour
ORDER BY hour
```

Nenhum uso de `utils/labels.py`. Formatação só numérica (`ROUND` no SQL).
`avg_wind` é selecionado mas **não** é plotado na aba Padrão 24h (só temp,
umidade e precip/dia entram no gráfico).

## Requirements (EARS)

### Funcionais
- THE system SHALL servir `GET /horario`, renderizando `horario.html`
  (esqueleto com as 3 abas e os elementos-alvo de gráfico vazios).
- THE system SHALL registrar a entrada de menu **"Horário"** (ícone `🕐`)
  na posição 4, a partir da estrutura central de rotas.
- THE system SHALL expor `GET /api/v1/horario/cidades` retornando a lista
  de `city_name` distintos presentes em `mart_climate__hourly_facts`
  (ordenada) — **não** a lista do seed.
- THE system SHALL expor `GET /api/v1/horario/serie` com parâmetros `city`
  (obrigatório) e `days` (3–30), retornando as linhas horárias por
  `observed_at` com `temperature_c`, `relative_humidity_pct`,
  `wind_speed_kmh` e `precipitation_mm` — as abas "Temperatura & Umidade" e
  "Vento & Chuva" leem a **mesma** série (mesmo `WHERE`, mesmo grão), então
  um endpoint serve as duas. THE resposta SHALL incluir a `max_date`
  específica do município (metadado para a caption).
- THE system SHALL expor `GET /api/v1/horario/padrao-24h` com `city` e
  `days`, retornando `AVG` por `hour` de temperatura, umidade, vento e
  precipitação/dia (`SUM / NULLIF(COUNT(DISTINCT date), 0)`).
- WHEN nenhum `city` é informado, THE frontend SHALL exibir
  `Selecione um município na barra lateral.` e não disparar `fetch` de
  série.
- WHEN a série ou o padrão vêm vazios, THE frontend SHALL exibir a
  mensagem condicional equivalente à do Streamlit (por aba).
- FOR paridade de filtros: `Município` (lista da `hourly_facts`) e
  `Período (dias)` (3–30, passo 1, default 7) SHALL existir com a mesma
  semântica.
- FOR paridade de métricas: séries horárias de temperatura, umidade, vento
  e precipitação, e o perfil médio das 24h (temp/umidade/precip-dia) SHALL
  estar presentes.

### Não-funcionais
- A âncora de data SHALL ser `MAX(date)` filtrado por `city_name` (âncora
  por município), não `CURRENT_DATE()` nem o `max_date()` global.
- Rotas síncronas (`def`); cliente BigQuery reutilizado.
- `city` validada contra a lista de `/api/v1/horario/cidades`; `days`
  numérico 3–30.
- `mart_climate__hourly_facts` é a tabela mais volumosa do projeto (ver
  `CLAUDE.md`); as queries SHALL manter o filtro por `date` (partição) e
  por `city_name` — nunca varrer a tabela inteira.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| 1 endpoint `serie` para as abas "Temperatura & Umidade" e "Vento & Chuva" | 1 endpoint por aba | Mesma tabela, mesmo `WHERE`, mesmo grão — só muda quais colunas o gráfico usa. Um `fetch` cobre as duas abas; menos round-trips ao trocar de aba. |
| `max_date` por município no payload da `serie` | Endpoint `/meta?city=` separado | Evita um round-trip extra; a caption precisa exatamente do valor que a query já usou. |
| Lista de cidades da `hourly_facts`, não do seed | Usar o seed `locations` (295) | Nem todo município tem dado horário; o seed traria opções que resultam em "sem dados". Paridade com o `SELECT DISTINCT` atual. |
| Aba 24h → **line** (temp, umidade) + **bar** (precip/dia) num gráfico com múltiplos `yAxis` | 3 gráficos separados | Paridade visual: hoje é um `go.Figure` único com 3 eixos. `avg_wind` fica disponível no payload mas não plotado (paridade). |

### Componentes afetados
| Rota | Endpoint(s) JSON | Template Jinja2 | Módulo TS | Gráfico(s) ECharts |
|---|---|---|---|---|
| `/horario` | `/api/v1/horario/cidades`, `/api/v1/horario/serie`, `/api/v1/horario/padrao-24h` | `horario.html` | `web/src/pages/horario.ts` | Aba Temp & Umidade → **line** dupla, 2 `yAxis`; Aba Vento & Chuva → **bar** (precip) + **line** (vento), 2 `yAxis`; Aba Padrão 24h → **line** (temp, umidade) + **bar** (precip/dia), múltiplos `yAxis`, `xAxis` = hora 0–23 |

## Casos de borda
- **Município sem dado horário** → `/api/v1/horario/serie` retorna
  `max_date` nulo / linhas vazias; frontend mostra
  `Sem dados horários para este município.`
- **Série vazia no período** (município tem dado, mas não nos últimos N
  dias) → `Sem dados horários para este município no período.`
- **Padrão 24h sem dado suficiente** →
  `Sem dados suficientes para calcular o padrão horário.`
- **`observed_at` como timestamp** → o payload JSON SHALL serializar em ISO
  8601; o eixo temporal do ECharts usa `type: 'time'`.
- **`COUNT(DISTINCT date) = 0`** → `NULLIF` evita divisão por zero (mantido
  na query migrada).
- **Pipeline atrasado** → âncora por `MAX(date)` do município.

## Fora do escopo
- Plotar `avg_wind` na aba Padrão 24h (hoje é calculado e ignorado).
- Filtro por mesorregião (esta página é sempre por município único).
- Seleção de intervalo de datas absoluto.
- Mudanças em `mart_climate__hourly_facts` ou na expiração de partição
  (450 dias) descrita no `CLAUDE.md`.

## Referências de código
- `streamlit/pages/4_Horario.py` — página de origem.
- `streamlit/utils/bigquery.py` — `query()`, `tbl()` (esta página faz o
  `MAX(date)` inline, sem o helper `max_date()`).
- `streamlit/app.py:189` — entrada de menu atual (`Horário`, `🕐`).
- `docs/specs/006-arquitetura-frontend-fastapi/spec.md` — arquitetura.

## Ver também
- [[006-arquitetura-frontend-fastapi]] — spec fundacional.
- [[014-camada-referencia]] — esta página **não** consome a camada de
  referência (lista de cidades vem da própria `hourly_facts`, âncora de
  data é por município); link só para deixar a exceção explícita.
- [[012-pagina-comparativo]] — a aba "Dia vs Histórico" também lê
  `hourly_facts` por hora e por município; compartilha padrão de query.
- [[007-pagina-temperatura]] / [[008-pagina-precipitacao]] /
  [[009-pagina-alertas]] — páginas de agregação diária.
- [[011-pagina-cidades]] — perfil diário por município.
- [[013-pagina-relatorio-cidade]] — relatório tabular por cidade.
