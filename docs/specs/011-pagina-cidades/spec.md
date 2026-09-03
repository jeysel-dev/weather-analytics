# Página Cidades (Perfil por Município) — migração Streamlit → FastAPI

## Tipo
[x] Refatoração (migração de página) + [x] Spec retroativa (documenta o
comportamento atual da página Streamlit antes de replicá-lo)

## Status
[x] implementado — página Cidades no FastAPI, validada em produção.

## Resumo
Migrar `streamlit/pages/5_Cidades.py` para a rota FastAPI (`/cidades`) com
template Jinja2 de esqueleto + módulo TypeScript que busca dado via
`/api/v1/*` e renderiza cabeçalho, KPIs e 4 abas com ECharts, conforme
[[006-arquitetura-frontend-fastapi]]. No menu o item chama-se "Cidades"; o
título da página é "Perfil por Município".

## Contexto
A página Cidades hoje, em Streamlit, mostra:

- **Filtros na sidebar:** `Selecione` município (selectbox — lista dos
  **295** municípios do seed `locations`, com metadados) e `Período (dias)`
  (slider 30–365, passo 30, default 90 — range/passo próprios, o maior de
  todas as páginas).
- **Cabeçalho:** `📍 {city}` + caption com `mesoregion`, `altitude_m`
  formatada (`%.0f m`), latitude/longitude formatadas com hemisfério
  (`{abs(lat):.2f}°S/N, {abs(lon):.2f}°W/E`).
- **Linha de 4 KPIs** (calculados no cliente a partir do dataframe
  `climate`): Temp Máx Média (`mean(temp_max_c)`), Temp Mín Média
  (`mean(temp_min_c)`), Precip. Acumulada (`sum(precipitation_mm)`),
  Anomalia Média (`mean(temp_anomaly_c)`, `delta_color="inverse"`).
- **4 abas (`st.tabs`):**
  - `🌡️ Temperatura`: linhas max/avg/min + barra de anomalia
    (vermelho se `>0`, azul se `≤0`), dois eixos Y.
  - `🌧️ Precipitação`: barra diária por `date`, cor por
    `precipitation_class` traduzida (`CLASS_LABELS_PT`) + 2 métricas
    (`Total acumulado`, `Dias com chuva` = `X de N`).
  - `💨 Vento & UV`: barra `wind_speed_max_kmh` + linha `uv_index_max`,
    dois eixos Y.
  - `🚨 Alertas`: tabela de até 100 alertas do município
    (`alert_type`/`severity` traduzidos), ordenada por `date DESC`.
    Mensagem quando vazia: `Nenhum alerta registrado para {city} nos
    últimos N dias.` (via `st.success`).
- **Mensagens condicionais:** erro se a lista de municípios não carrega;
  `Sem dados para {city} no período de N dias.` se `climate` vem vazio.

## Investigação (retroativa)

Lista de municípios com metadados (do seed) e filtros
(`streamlit/pages/5_Cidades.py:19-39`):

```python
cities = query(f"""
SELECT city_name, mesoregion,
       ROUND(latitude, 4)  AS latitude,
       ROUND(longitude, 4) AS longitude,
       altitude_m
FROM {tbl('locations', seeds=True)}
WHERE city_name IS NOT NULL
ORDER BY city_name
""")
...
city = st.selectbox("Selecione", cities["city_name"].tolist())
days = st.slider("Período (dias)", 30, 365, 90, step=30)
_max_daily  = max_date("mart_climate__daily_facts")
_max_alerts = max_date("mart_climate__alerts")
```

Dados climáticos diários do município:

```sql
SELECT date, temp_max_c, temp_min_c, temp_avg_c,
  temp_anomaly_c, precipitation_mm, precipitation_class,
  wind_speed_max_kmh, uv_index_max, uv_risk_level
FROM mart_climate__daily_facts
WHERE city_name = '{city}'
  AND date >= DATE_SUB(DATE '{_max_daily}', INTERVAL {days} DAY)
ORDER BY date
```

KPIs (client-side, `pandas`):

```python
agg = climate.agg({"temp_max_c":"mean","temp_min_c":"mean",
                   "precipitation_mm":"sum","temp_anomaly_c":"mean"}).round(1)
```

Aba Alertas:

```sql
SELECT date, alert_type, severity,
  ROUND(temp_max_c, 1) AS temp_max, ROUND(temp_anomaly_c, 1) AS anomalia,
  ROUND(precipitation_mm, 1) AS precip, ROUND(wind_speed_max_kmh, 1) AS vento,
  uv_index_max
FROM mart_climate__alerts
WHERE city_name = '{city}'
  AND date >= DATE_SUB(DATE '{_max_alerts}', INTERVAL {days} DAY)
ORDER BY date DESC
LIMIT 100
```

Traduções usadas: `CLASS_LABELS_PT` (aba Precipitação), `ALERT_TYPE_PT` +
`SEVERITY_PT` (aba Alertas). `uv_risk_level` é selecionado mas **não** é
exibido. `CLASS_COLORS` repetido localmente (igual ao da página 008).

## Requirements (EARS)

### Funcionais
- THE system SHALL servir `GET /cidades`, renderizando `cidades.html`
  (esqueleto: cabeçalho, faixa de KPIs, 4 abas com alvos de gráfico/tabela
  vazios).
- THE system SHALL registrar a entrada de menu **"Cidades"** (ícone `🏙️`)
  na posição 5, a partir da estrutura central de rotas.
- THE system SHALL expor `GET /api/v1/cidades/lista` retornando os 295
  municípios do seed com `mesoregion`, `latitude`, `longitude`,
  `altitude_m` (para o selectbox e o cabeçalho).
- THE system SHALL expor `GET /api/v1/cidades/clima` com parâmetros `city`
  (obrigatório) e `days` (30–365), retornando as linhas diárias
  (`date`, `temp_max_c`, `temp_min_c`, `temp_avg_c`, `temp_anomaly_c`,
  `precipitation_mm`, `precipitation_class`, `wind_speed_max_kmh`,
  `uv_index_max`) ancoradas em `max_date('mart_climate__daily_facts')`. THE
  resposta SHALL incluir o resumo agregado (médias de temp máx/mín/anomalia,
  soma de precipitação, contagem de dias com chuva e total de dias) — os 4
  KPIs e as 2 métricas da aba Precipitação derivam desse resumo.
- THE system SHALL expor `GET /api/v1/cidades/alertas` com `city` e `days`,
  retornando até **100** alertas do município (`date DESC`), com
  `alert_type`/`severity` traduzidos e métricas arredondadas, ancorados em
  `max_date('mart_climate__alerts')`.
- FOR paridade de filtros: `Município` (295 do seed) e `Período (dias)`
  (30–365, passo 30, default 90) SHALL existir com a mesma semântica.
- FOR paridade de métricas: os 4 KPIs, as séries de temperatura
  (max/avg/min + anomalia), a série de precipitação por classe, as métricas
  `Total acumulado` / `Dias com chuva`, a série vento+UV e a tabela de
  alertas SHALL estar presentes.
- THE cabeçalho SHALL exibir mesorregião, altitude e coordenadas com
  hemisfério, com a mesma formatação atual.
- IF `altitude_m` for nulo para um município, THE system SHALL exibir um
  placeholder (`—`) no lugar da altitude no cabeçalho, em vez de falhar na
  formatação. Esta é uma **correção deliberada de robustez** em relação ao
  Streamlit atual (que executaria `f"{None:.0f}"` e levantaria
  `TypeError`) — não é uma mudança de escopo da página.

### Não-funcionais
- Janelas ancoradas em `max_date()` das tabelas respectivas
  (`daily_facts` para clima, `alerts` para a aba de alertas), obtidas de
  `/api/v1/ref/daily-meta` e `/api/v1/ref/alerts-meta`
  ([[014-camada-referencia]]).
- Rotas síncronas (`def`); cliente BigQuery reutilizado.
- `city` validada contra `/api/v1/cidades/lista`; `days` numérico 30–365.
- O resumo agregado dos KPIs SHALL ser calculado **no servidor** (SQL ou
  em memória sobre o resultado), não depender de o cliente somar linha a
  linha — mas o resultado numérico SHALL bater com o `pandas.agg` atual
  (média sobre dias presentes, soma de precipitação, `round(1)`).
- IF `altitude_m` for nulo, THE formatação do cabeçalho SHALL usar o
  placeholder `—` (ver requirement funcional acima); nenhum outro campo do
  cabeçalho SHALL quebrar por valor ausente.
- `CLASS_LABELS_PT` / `CLASS_COLORS` / `ALERT_TYPE_PT` / `SEVERITY_PT`
  SHALL vir do módulo compartilhado `web/src/labels.ts` definido em
  [[014-camada-referencia]], não de um dicionário reimplementado nesta
  página.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| `clima` devolve linhas **+** resumo agregado no mesmo payload | Endpoint `/kpis` separado | Os KPIs são derivados exatamente do mesmo conjunto de linhas; recomputar num segundo endpoint duplicaria a query. Um payload, o cliente desenha os gráficos e lê o resumo. |
| KPIs calculados no servidor | Manter cálculo no cliente (TS) como o Streamlit faz em pandas | Menos lógica numérica no TS; garante que "média sobre dias presentes" seja idêntica. O cliente só formata. |
| Aba Alertas → tabela HTML | Grid component | Paridade com `st.dataframe`; ≤100 linhas. |
| `lista` de municípios como endpoint próprio, **não** o `/api/v1/ref/cidades` de [[014-camada-referencia]] | Reusar o ref compartilhado | Aqui a lista precisa dos metadados (lat/lon/altitude/meso) que as outras páginas não usam; endpoint dedicado. `/api/v1/ref/cidades` devolve só `city_name` e serve as páginas 012/013. |
| `altitude_m` nulo → placeholder `—` | Replicar o comportamento atual do Streamlit (quebra em `f"{None:.0f}"`) | O comportamento atual é um bug latente, não uma decisão de produto; a migração corrige de propósito (ver Requirements). |

### Componentes afetados
| Rota | Endpoint(s) JSON | Template Jinja2 | Módulo TS | Gráfico(s) ECharts |
|---|---|---|---|---|
| `/cidades` | `/api/v1/cidades/lista`, `/api/v1/cidades/clima`, `/api/v1/cidades/alertas` (+ `/api/v1/ref/daily-meta`, `/api/v1/ref/alerts-meta` de [[014-camada-referencia]]) | `cidades.html` | `web/src/pages/cidades.ts` (+ `web/src/labels.ts` de [[014-camada-referencia]]) | Aba Temperatura → **line** (max/avg/min) + **bar** (anomalia, cor condicional), 2 `yAxis`; Aba Precipitação → **bar** por data, cor por classe (`CLASS_COLORS`); Aba Vento & UV → **bar** (vento) + **line** (UV), 2 `yAxis`; Aba Alertas → **tabela HTML** |

## Casos de borda
- **Lista de municípios não carrega** → erro equivalente a
  `Não foi possível carregar a lista de municípios.`
- **`climate` vazio para o município/período** →
  `Sem dados para {city} no período de N dias.`; KPIs e abas não renderizam.
- **Sem alertas no período** → aba Alertas mostra
  `Nenhum alerta registrado para {city} nos últimos N dias.`
- **`precipitation_class` nulo / não mapeado** → fallback para valor cru.
- **`altitude_m` nulo para o município selecionado** → o cabeçalho exibe
  `—` no lugar da altitude e continua renderizando normalmente. O
  Streamlit atual quebraria aqui (`f"{None:.0f}"` → `TypeError`); a versão
  nova trata como correção deliberada de robustez, não como mudança de
  escopo (ver Requirements funcionais e não-funcionais).
- **Pipeline atrasado** → âncoras em `max_date()` via
  [[014-camada-referencia]].

## Fora do escopo
- Exibir `uv_risk_level` (hoje selecionado e ignorado).
- Mapa de localização do município no cabeçalho (não existe hoje).
- Exportação / compartilhamento (isso é a página 013).
- Mudanças em models dbt.

## Referências de código
- `streamlit/pages/5_Cidades.py` — página de origem.
- `streamlit/utils/labels.py` — `CLASS_LABELS_PT`, `ALERT_TYPE_PT`,
  `SEVERITY_PT` (consolidados em `web/src/labels.ts` por
  [[014-camada-referencia]]).
- `streamlit/utils/bigquery.py` — `query()`, `tbl()`, `max_date()`,
  `format_temp()`.
- `streamlit/app.py:190` — entrada de menu atual (`Cidades`, `🏙️`).
- `docs/specs/006-arquitetura-frontend-fastapi/spec.md` — arquitetura.
- `docs/specs/014-camada-referencia/spec.md` — endpoints de referência
  (`daily-meta`, `alerts-meta`) e `web/src/labels.ts`.

## Ver também
- [[006-arquitetura-frontend-fastapi]] — spec fundacional.
- [[014-camada-referencia]] — endpoints de referência e módulo de rótulos
  compartilhados que esta página consome.
- [[008-pagina-precipitacao]] — mesma paleta/rótulos de classe de
  precipitação.
- [[009-pagina-alertas]] — mesma tradução de tipo/severidade de alerta.
- [[012-pagina-comparativo]] — compara municípios (métricas diárias).
- [[013-pagina-relatorio-cidade]] — relatório tabular multi-cidade.
- [[007-pagina-temperatura]] / [[010-pagina-horario]] — outras páginas da
  sequência.
