# Página Relatório por Cidade — migração Streamlit → FastAPI

## Tipo
[x] Refatoração (migração de página) + [x] Spec retroativa (documenta o
comportamento atual da página Streamlit antes de replicá-lo)

## Status
[x] proposta — nenhum código de `api/` ou `web/` escrito.

## Resumo
Migrar `streamlit/pages/7_Relatorio_Cidade.py` para a rota FastAPI
(`/relatorio-cidade`) com template Jinja2 de esqueleto + módulo TypeScript
que busca dado via `/api/v1/*` e renderiza uma tabela consolidada + botão
de compartilhamento, conforme [[006-arquitetura-frontend-fastapi]]. É a
única página com **estado na URL** (deep link) e **seleção de intervalo de
datas absoluto**.

## Contexto
A página Relatório por Cidade hoje, em Streamlit, mostra:

- **Filtros no corpo (2 colunas):**
  - `Cidades` — `st.multiselect` sobre os 295 municípios do seed
    (multi-seleção, sem default salvo o que vem da URL).
  - `Período` — `st.date_input` de **intervalo** (`value=(inicio, fim)`),
    `min_value = min_date(daily_facts)`, `max_value = max_date(daily_facts)`,
    formato `DD/MM/YYYY`. Default: fim = `max_date`, início =
    `max(min_date, max_date - 30 dias)`.
- **Estado na URL (`st.query_params`):** `cidades` (lista separada por
  vírgula), `inicio`, `fim` (ISO). Ao abrir com esses params válidos, os
  filtros já vêm preenchidos. Validação: cada cidade tem que estar na lista
  do seed; `min_date <= inicio <= fim <= max_date`; datas mal formatadas
  são ignoradas silenciosamente.
- **Caption:** `Cidades: {lista} | Período: {dd/mm/aaaa} a {dd/mm/aaaa}`.
- **Tabela consolidada** (uma linha por cidade): Temp. Máxima
  (`MAX(temp_max_c)`), Temp. Máxima Média (`AVG(temp_max_c)`), Temp. Mínima
  (`MIN(temp_min_c)`), Temp. Mínima Média (`AVG(temp_min_c)`), Precip.
  Acumulada (`SUM(precipitation_mm)`), Vento Máximo (`MAX(wind_speed_max_kmh)`).
- **Botão "Compartilhar":** monta uma URL pública da própria página com os
  query params atuais + um texto, e abre um link de compartilhamento via
  WhatsApp (`wa.me`).
- **Mensagens condicionais:** `Selecione ao menos uma cidade para gerar o
  relatório.` (sem cidade), `Selecione a data final do período.` (só data
  inicial escolhida), `Sem dados para o período selecionado.` (query vazia).

## Investigação (retroativa)

Referência, âncoras e defaults da URL
(`streamlit/pages/7_Relatorio_Cidade.py:10-37`):

```python
_city_list = query(f"SELECT city_name FROM {tbl('locations', seeds=True)} ORDER BY city_name")...
_max_daily = max_date("mart_climate__daily_facts")
_min_daily = min_date("mart_climate__daily_facts")

_qp_cidades = st.query_params.get("cidades")
_default_cities = [c for c in _qp_cidades.split(",") if c in _city_list] if _qp_cidades else []

_default_fim = _max_daily
_default_inicio = max(_min_daily, _max_daily - timedelta(days=30))  # clamp ao min

_qp_inicio = st.query_params.get("inicio"); _qp_fim = st.query_params.get("fim")
if _qp_inicio and _qp_fim:
    try:
        _p_inicio = date.fromisoformat(_qp_inicio); _p_fim = date.fromisoformat(_qp_fim)
        if _min_daily <= _p_inicio <= _p_fim <= _max_daily:
            _default_inicio, _default_fim = _p_inicio, _p_fim
    except ValueError:
        pass
```

Guardas de fluxo:

```python
if not selected_cities:
    st.info("Selecione ao menos uma cidade para gerar o relatório."); st.stop()
if not (isinstance(periodo, (list, tuple)) and len(periodo) == 2):
    st.info("Selecione a data final do período."); st.stop()
```

Query do relatório:

```sql
SELECT city_name,
  ROUND(MAX(temp_max_c), 1)         AS temp_maxima,
  ROUND(AVG(temp_max_c), 1)         AS temp_maxima_media,
  ROUND(MIN(temp_min_c), 1)         AS temp_minima,
  ROUND(AVG(temp_min_c), 1)         AS temp_minima_media,
  ROUND(SUM(precipitation_mm), 1)   AS precip_acumulada,
  ROUND(MAX(wind_speed_max_kmh), 1) AS vento_maximo
FROM mart_climate__daily_facts
WHERE city_name IN ({cities_sql})
  AND date BETWEEN DATE '{data_inicio}' AND DATE '{data_fim}'
GROUP BY city_name
ORDER BY city_name
```

Compartilhamento:

```python
share_params = urlencode({"cidades": ",".join(selected_cities),
                          "inicio": data_inicio.isoformat(), "fim": data_fim.isoformat()})
share_url = f"https://weather.jeysel.dev/Relatorio_Cidade?{share_params}"
message = (f"Relatório de clima - {', '.join(selected_cities)} - "
           f"Período: {inicio dd/mm} a {fim dd/mm}. Veja o relatório completo: {share_url}")
wa_url = f"https://wa.me/?text={quote(message)}"
```

Nenhum uso de `utils/labels.py`. Formatação: `ROUND` no SQL +
`st.column_config.NumberColumn(format="%.1f")`.

## Requirements (EARS)

### Funcionais
- THE system SHALL servir `GET /relatorio-cidade`, renderizando
  `relatorio-cidade.html` (esqueleto: 2 filtros, caption, tabela vazia,
  botão de compartilhar).
- THE system SHALL registrar a entrada de menu **"Relatório por Cidade"**
  (ícone `📋`) na posição 7, a partir da estrutura central de rotas.
- THE frontend SHALL obter `min_date` e `max_date` de
  `mart_climate__daily_facts` (para configurar o seletor de intervalo) do
  endpoint `/api/v1/ref/daily-meta`, definido em [[014-camada-referencia]]
  — este substitui o `/api/v1/relatorio-cidade/limites` que uma versão
  anterior desta spec havia proposto isoladamente.
- THE system SHALL expor `GET /api/v1/relatorio-cidade/dados` com
  parâmetros `cidades` (1+ nomes), `inicio` e `fim` (datas ISO),
  retornando uma linha por cidade com `temp_maxima` (MAX), `temp_maxima_media`
  (AVG), `temp_minima` (MIN), `temp_minima_media` (AVG), `precip_acumulada`
  (SUM), `vento_maximo` (MAX), ordenada por `city_name`.
- THE frontend SHALL obter a lista de `city_name` do seed do endpoint
  `/api/v1/ref/cidades`, definido em [[014-camada-referencia]] — esta spec
  não o redefine.
- THE frontend SHALL ler e escrever o estado (`cidades`, `inicio`, `fim`)
  na query string da própria URL — abrir a página com esses parâmetros
  válidos SHALL pré-preencher os filtros e disparar o relatório; mudar os
  filtros SHALL atualizar a URL (para o link ser copiável).
- THE frontend SHALL validar os parâmetros da URL com a mesma regra do
  Streamlit: cada cidade tem que existir na lista de referência;
  `min_date <= inicio <= fim <= max_date`; datas inválidas são ignoradas
  e caem no default.
- THE default do período SHALL ser `fim = max_date`,
  `inicio = max(min_date, max_date - 30 dias)`.
- WHEN nenhuma cidade está selecionada, THE frontend SHALL exibir
  `Selecione ao menos uma cidade para gerar o relatório.` e não chamar
  `/dados`.
- WHEN só a data inicial do intervalo foi escolhida, THE frontend SHALL
  exibir `Selecione a data final do período.`
- WHEN `/dados` retorna vazio, THE frontend SHALL exibir
  `Sem dados para o período selecionado.`
- THE botão "Compartilhar" SHALL montar a URL pública da página com os
  parâmetros atuais e abrir um link de compartilhamento via WhatsApp
  (`https://wa.me/?text=...`), com o mesmo texto atual (cidades + período +
  link).

### Não-funcionais
- `min_date` / `max_date` vêm de `mart_climate__daily_facts` via
  `/api/v1/ref/daily-meta` ([[014-camada-referencia]]) — âncora no dado
  real, nunca `CURRENT_DATE()`.
- Rota síncrona (`def`); cliente BigQuery reutilizado.
- `cidades` validadas server-side contra o seed; `inicio`/`fim` parseadas
  como data e checadas contra `[min_date, max_date]` — a query **não** deve
  interpolar string livre (o `IN (...)` de nomes de cidade deve usar
  parâmetros ou uma allowlist derivada do seed).
- A URL de compartilhamento SHALL usar o domínio público do dashboard
  (o mesmo já referenciado em [[006-arquitetura-frontend-fastapi]]); o
  path muda de `/Relatorio_Cidade` para `/relatorio-cidade` (nova rota).

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Estado na query string mantido pelo JS (`history.replaceState` / `URLSearchParams`) | Estado só em memória, sem deep link | Paridade — o compartilhamento por URL é a razão de existir desta página. |
| Limites de data vêm de `/api/v1/ref/daily-meta` ([[014-camada-referencia]]) | Endpoint `/limites` próprio desta página; ou fold em `/dados` | O seletor de datas precisa dos limites **antes** de qualquer cidade ser escolhida; `/dados` só roda depois. E `min`/`max` de `daily_facts` não é dado exclusivo desta página — pertence à camada de referência. |
| Validação de `cidades` por allowlist do seed (a mesma lista de `/api/v1/ref/cidades`) | Parâmetro BigQuery `ARRAY` | Ambos servem; a allowlist já é necessária para a validação da URL, então reusar. |
| Tabela → `<table>` HTML no template, populada via `fetch` | Grid component | Paridade com `st.dataframe`; poucas linhas (nº de cidades selecionadas). |
| Sem gráfico ECharts nesta página | Adicionar um gráfico comparativo | A página Streamlit é puramente tabular; comparação visual já é a página [[012-pagina-comparativo]]. **ECharts não é dependência desta página.** |

### Componentes afetados
| Rota | Endpoint(s) JSON | Template Jinja2 | Módulo TS | Visualização |
|---|---|---|---|---|
| `/relatorio-cidade` | `/api/v1/relatorio-cidade/dados` (+ `/api/v1/ref/cidades`, `/api/v1/ref/daily-meta` de [[014-camada-referencia]]) | `relatorio-cidade.html` | `web/src/pages/relatorio-cidade.ts` | **Tabela HTML** consolidada (1 linha/cidade, 6 métricas) + botão "Compartilhar" (link `wa.me`). Sem gráfico. |

## Casos de borda
- **URL com cidade inexistente** → filtrada fora (`c in _city_list`);
  as válidas permanecem.
- **URL com `inicio > fim` ou fora de `[min, max]`** → ignorada, cai no
  default.
- **URL com data não-ISO** → `ValueError` silencioso, cai no default.
- **`inicio = min_date` clampado** — o default `max_date - 30d` pode ser
  anterior ao `min_date` se a tabela tiver menos de 30 dias; o `max(...)`
  evita um valor fora do range aceito pelo seletor.
- **Só data inicial escolhida no seletor de intervalo** →
  `Selecione a data final do período.` (não chama `/dados`).
- **Nenhuma cidade** → `Selecione ao menos uma cidade…`.
- **Query vazia** (cidades válidas, mas sem dado no período) →
  `Sem dados para o período selecionado.`
- **Pipeline atrasado** → `min_date`/`max_date` refletem o dado real.

## Fora do escopo
- Exportação para CSV/PDF do relatório (não existe hoje).
- Gráfico comparativo nesta página (é a página 012).
- Outros canais de compartilhamento além do WhatsApp.
- Redirecionar/observar a URL antiga `/Relatorio_Cidade` para a nova rota
  — isso é responsabilidade do roteamento de infra (ver "Fora do escopo"
  de [[006-arquitetura-frontend-fastapi]]).
- Mudanças em models dbt.

## Referências de código
- `streamlit/pages/7_Relatorio_Cidade.py` — página de origem (estado na
  URL, seletor de intervalo, compartilhamento).
- `streamlit/utils/bigquery.py` — `query()`, `tbl()`, `max_date()`,
  `min_date()`.
- `streamlit/app.py:192` — entrada de menu atual
  (`Relatório por Cidade`, `📋`).
- `docs/specs/006-arquitetura-frontend-fastapi/spec.md` — arquitetura;
  seção "Roteamento entre Streamlit e FastAPI" (bloqueio de infra relevante
  para a URL de compartilhamento).
- `docs/specs/014-camada-referencia/spec.md` — `/api/v1/ref/cidades` e
  `/api/v1/ref/daily-meta` (este absorve o antigo `/limites`).

## Ver também
- [[006-arquitetura-frontend-fastapi]] — spec fundacional; trata do
  roteamento público de path e do domínio.
- [[014-camada-referencia]] — define `/api/v1/ref/cidades` e
  `/api/v1/ref/daily-meta` que esta página consome.
- [[012-pagina-comparativo]] — comparação visual entre municípios (esta é
  a versão tabular/relatório).
- [[011-pagina-cidades]] — perfil detalhado de um município.
- [[007-pagina-temperatura]] / [[008-pagina-precipitacao]] /
  [[009-pagina-alertas]] / [[010-pagina-horario]] — demais páginas da
  sequência.
