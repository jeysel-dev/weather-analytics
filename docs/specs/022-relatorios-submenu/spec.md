# Quatro relatórios novos sob o submenu "Relatórios"

## Tipo
[x] Nova feature  [ ] Melhoria  [ ] Bug fix  [ ] Refatoração  [ ] Spec retroativa

## Status
[x] implementado — 4 páginas (`relatorio-mensal`, `relatorio-macrorregiao`,
`relatorio-extremos`, `relatorio-chuva-acumulada`) no submenu "Relatórios",
todas puramente tabulares no padrão `.data-table` / `renderTable` (spec 021).

## Resumo
O submenu "Relatórios" (spec 017) tinha um único filho. Entram mais quatro,
todos **só tabela** (spec 021), cada um com um endpoint `/dados` próprio:

| Página | Rota | Pergunta que responde |
|---|---|---|
| Consolidado Mensal | `/relatorio-mensal` | Como foi cada mês, por cidade (médias, chuva acumulada, dias com chuva). |
| Por Macrorregião | `/relatorio-macrorregiao` | Panorama das 8 macrorregiões num período: médias, chuva, nº de alertas. |
| Extremos e Recordes | `/relatorio-extremos` | Os recordes do período — maior máxima, menor mínima, maior chuva/rajada/UV — com cidade e data. |
| Chuva Acumulada | `/relatorio-chuva-acumulada` | Ranking de precipitação acumulada por cidade, com dias de chuva e o maior volume diário. |

## Contexto
- Infra já pronta: `Page(menu_group="Relatórios")` + `_build_menu` em
  [api/app/main.py](../../../api/app/main.py) monta o `MenuGroup`; o
  template e o `nav.ts` já renderizam o submenu (spec 017, "Fora do
  escopo" era justamente *adicionar* relatórios).
- Padrão de tabela: `.data-table` + `web/src/table.ts::renderTable`
  (spec 021) — `<thead>` no template com `.col-num` nas numéricas, a
  página monta `RowDef[]`.
- Colunas disponíveis: `mart_climate__daily_facts` (date, year_month,
  city_name, mesoregion, temp_max_c, temp_min_c, temp_avg_c,
  temp_amplitude_c, precipitation_mm, wind_speed_max_kmh, uv_index_max, …)
  e `mart_climate__alerts` (date, city_name, mesoregion, alert_type,
  severity, …). `mesoregion` já é desnormalizada nas duas marts.
- Filtro de data ancora em `max_date(tabela)`, nunca `CURRENT_DATE()`
  (CLAUDE.md).
- Referência: `/api/v1/ref/cidades`, `/api/v1/ref/mesorregioes`,
  `/api/v1/ref/daily-meta` (spec 014); `require_cidade`,
  `meso_filter` em `app/routers/ref.py`.

## Requirements (EARS)

### Comum às 4 páginas
- THE cada página SHALL declarar um `Page(..., menu_group="Relatórios")`
  em `PAGES`, com `menu_position` 8–11 (após "Relatório por Cidade" = 7).
- THE cada página SHALL ser esqueleto Jinja (`.filter-bar` +
  `<div class="data-table"><table hidden>` com `<thead>`) preenchido pelo
  respectivo `web/src/pages/<id>.ts`, registrado no `DISPATCH` de `main.ts`.
- THE cada página SHALL exibir um `#…-caption` "Dados disponíveis até
  DD/MM/YYYY" a partir de `/api/v1/ref/daily-meta`.
- THE cada endpoint SHALL ancorar a janela em `max_date(...)`; quando a
  mart está vazia (`None`), SHALL responder com a estrutura vazia (sem
  erro), e a página mostra a mensagem de vazio.
- THE nenhuma página nova SHALL ter estado na URL nem botão "Compartilhar"
  (isso é exclusivo de `/relatorio-cidade`).
- THE `IN (...)` / filtros dinâmicos SHALL usar parâmetros nomeados do
  BigQuery; `cidades` e `meso` SHALL ser validados contra o seed
  (`require_cidade` / `meso_filter`).

### Consolidado Mensal — `/relatorio-mensal`
- Filtros: `#filtro-cidades` (multi, Tom Select via `enhanceCitySelect`) e
  `#filtro-inicio` / `#filtro-fim` (`<input type="month">`, `min`/`max` =
  `daily-meta` recortada a `YYYY-MM`).
- `GET /api/v1/relatorio-mensal/dados?cidades=…&inicio=YYYY-MM&fim=YYYY-MM`
  — `cidades` repetido (≥1), `inicio`/`fim` no formato `YYYY-MM`
  (regex; `inicio <= fim`). Resposta: `meses` (cidade × mês), `subtotais`
  (por cidade) e `total_geral` — mesmo formato de 3 partes do
  `/relatorio-cidade`.
- Colunas: Mês · Cidade · Temp. Máx. Média (°C) · Temp. Mín. Média (°C) ·
  Amplitude Média (°C) · Precip. Acumulada (mm) · Dias com Chuva ·
  Vento Máx. (km/h). Agrupado por cidade com linha `row-subtotal` por
  cidade e `row-total` no fim.
- Mês exibido como `MM/AAAA` (`formatarMesISO` em `format.ts`).

### Por Macrorregião — `/relatorio-macrorregiao`
- Filtro: `#filtro-dias` (`number`, 7–365, default 30).
- `GET /api/v1/relatorio-macrorregiao/dados?dias=N`. Duas queries:
  `daily_facts` agrupado por `mesoregion` (âncora `daily-meta`) e
  `alerts` agrupado por `mesoregion` (âncora `alerts-meta`, própria),
  casadas por macrorregião em Python. Uma linha por macrorregião +
  `row-total` (agregado do estado).
- Colunas: Macrorregião · Municípios · Temp. Máx. Média (°C) ·
  Temp. Mín. Média (°C) · Precip. Média (mm) · Precip. Acumulada (mm) ·
  Alertas.

### Extremos e Recordes — `/relatorio-extremos`
- Filtros: `#filtro-dias` (7–365, default 30) e `#filtro-mesorregiao`
  (opcional).
- `GET /api/v1/relatorio-extremos/dados?dias=N&meso=…`. **Uma** query em
  `daily_facts` com `MAX_BY`/`MIN_BY` de um `STRUCT(city_name, date, valor)`
  por indicador (ignoram métrica `NULL`; `NULL` quando não sobra linha).
  Servidor devolve 6 linhas em ordem fixa (`indicador`, `valor`,
  `city_name`, `date`).
- Indicadores: maior temperatura máxima (°C), menor temperatura mínima
  (°C), maior amplitude térmica (°C), maior precipitação em 24 h (mm),
  maior rajada de vento (km/h), maior índice UV.
- Colunas: Indicador · Valor · Cidade · Data. Sem linhas de fecho.

### Chuva Acumulada — `/relatorio-chuva-acumulada`
- Filtros: `#filtro-dias` (7–365, default 30) e `#filtro-mesorregiao`
  (opcional).
- `GET /api/v1/relatorio-chuva-acumulada/dados?dias=N&meso=…`. Query em
  `daily_facts` agrupada por cidade: `SUM` acumulado, `COUNTIF(> 0)` dias
  de chuva, `MAX` do dia e `MAX_BY(date, precipitation_mm)` para a data do
  maior volume. `ORDER BY precip_acumulada DESC`.
- Colunas: Cidade · Macrorregião · Precip. Acumulada (mm) · Dias com Chuva
  · Maior Volume 24 h (mm) · Data do Maior Volume. Sem linha de total
  (soma de chuva entre municípios não é grandeza física útil).

## Design

### Decisões de arquitetura
| Decisão | Alternativa | Motivo |
|---|---|---|
| 4 routers + 4 schemas + 4 páginas separados | Um router "relatorios" com 4 endpoints | Consistência total com as páginas existentes (uma pasta de router/schema/página por página) e com a "estrutura central" — cada `Page` puxa seu template e seu `page_id`. |
| `relatorio-mensal` reusa o formato de 3 partes (`linhas`/`subtotais`/`total`) do `/relatorio-cidade` | Formato próprio | Mesma necessidade (agrupar por cidade, subtotal, total geral); o front já tem o jeito de renderar isso com `renderTable` + `variant`. |
| `relatorio-extremos` numa query só com `MAX_BY`/`MIN_BY(STRUCT(...))` | 6 queries `ORDER BY x LIMIT 1`; ou `ARRAY_AGG(... ORDER BY ... LIMIT 1)` | Um scan da janela em vez de seis (CLAUDE.md — custo do BigQuery). `MAX_BY`/`MIN_BY` já ignoram linhas com a métrica `NULL` (`temp_min_c`/`wind`/`uv` não são `not_null`) e devolvem `NULL` sem linha — sem depender de `NULLS LAST` dentro de agregado. |
| `relatorio-macrorregiao`: alerts com âncora própria (`alerts-meta`) | Reusar a âncora de `daily-meta` | As duas marts podem divergir de data (o `alerts` deriva de `daily_facts` mas o `MAX(date)` pode diferir se um run parcial). Mesmo cuidado do router de alertas. |
| `<input type="month">` no mensal | Dois `<select>` de ano/mês, ou range de datas | Nativo, valor `YYYY-MM` (ordenável lexicograficamente = filtro direto por `year_month`), sem JS de povoamento. Firefox sem suporte cai para texto com o mesmo formato — aceitável. |
| Chuva Acumulada sem paginação (retorna todas as cidades) | "Ver mais" como em alertas | `renderTable` já tem `opts.limit`, mas o `.btn-mais-alertas` é específico de alertas; um ranking climático completo (≤295 linhas) é uso legítimo de um relatório. Paginação genérica fica para depois se virar problema. |
| Home: 4 cards novos + texto do hero genérico ("várias visões") | Deixar a home como está | A home lista as páginas; 4 relatórios invisíveis lá seria inconsistente. "Sete visões" vira texto sem número. |

### Componentes afetados
- `api/app/main.py` — 4 `Page(...)` novos em `PAGES`; 4 `import` de router;
  4 `app.include_router(...)`.
- `api/app/routers/relatorio_mensal.py`, `relatorio_macrorregiao.py`,
  `relatorio_extremos.py`, `relatorio_chuva_acumulada.py` — novos.
- `api/app/schemas/…` — 4 arquivos novos, um por router.
- `api/app/templates/relatorio-mensal.html`, `relatorio-macrorregiao.html`,
  `relatorio-extremos.html`, `relatorio-chuva-acumulada.html` — novos.
- `web/src/pages/relatorio-mensal.ts`, `relatorio-macrorregiao.ts`,
  `relatorio-extremos.ts`, `relatorio-chuva-acumulada.ts` — novos.
- `web/src/main.ts` — 4 `import` + 4 entradas no `DISPATCH`.
- `web/src/format.ts` — `formatarMesISO("2026-01") -> "01/2026"`.
- `api/app/templates/home.html` — 4 `.link-card` + ajuste do texto do hero.

## Casos de borda
- **Mensal sem cidade selecionada** → mensagem "Selecione ao menos uma
  cidade"; nenhum fetch.
- **Mensal `inicio > fim`** → 422 do endpoint; a página valida antes e
  mostra mensagem.
- **Mês parcial** (o mês corrente tem só alguns dias) → entra no relatório
  com o que houver; "Dias com Chuva" e médias refletem os dias existentes.
- **Macrorregião sem alerta no período** → `alertas = 0` (LEFT join em
  Python: macrorregião existe em `daily_facts`, ausente no dict de
  alertas → 0).
- **`daily-meta` e `alerts-meta` divergentes** → cada bloco usa sua
  âncora; a caption cita a de `daily-meta`.
- **Extremos: janela sem nenhum dado** → `MAX_BY`/`MIN_BY` devolvem
  `NULL`; servidor devolve 6 linhas com `valor`/`city_name`/`date` nulos,
  a página renderiza "—".
- **Extremos com empate** (duas cidades no mesmo valor) → `LIMIT 1`
  desempata pela ordenação do BigQuery (não determinístico entre runs;
  aceitável para "um" recorde).
- **Chuva Acumulada: cidade sem nenhuma chuva no período** → aparece com
  acumulada `0.0`, dias `0`, maior volume `0.0` e a data de um dos dias
  secos (`MAX_BY` só ignora `precipitation_mm` `NULL`, não `0`). Ordena
  no fim.
- **`meso` inexistente** → `meso_filter` → 404.
- **`<input type="month">` vazio ao abrir** (defaults aplicados pelo JS) →
  fim = mês de `max_date`, início = 12 meses antes (ou o mês de
  `min_date`, o que for maior).

## Fora do escopo
- Gráficos em qualquer um dos 4 (decisão do dono: só tabela).
- Estado na URL / deep-link / compartilhamento (só `/relatorio-cidade`).
- Paginação / "ver mais" / ordenação por clique no cabeçalho.
- Export CSV/PDF.
- Redirects de URL antiga (páginas novas, nunca existiram no Streamlit).
- Novos campos nas marts — tudo sai de colunas já existentes.
- `require_partition_filter` nas marts (decisão da spec anterior de custo;
  todas as queries daqui já filtram `date`).

## Referências de código
- `api/app/main.py` — `Page`, `PAGES`, `_build_menu`, `MENU`,
  `include_router`.
- `api/app/routers/relatorio_cidade.py` / `precipitacao.py` /
  `alertas.py` — padrões de router (3 partes, `meso_filter`, âncora).
- `api/app/routers/ref.py` — `require_cidade`, `meso_filter`, metas.
- `web/src/pages/relatorio-cidade.ts` — filtro multi-cidade + `renderTable`
  com `variant`.
- `web/src/pages/precipitacao.ts` — filtro `dias` + `meso` + caption.
- `web/src/table.ts` — `renderTable`, `RowDef` (spec 021).
- `web/src/citypicker.ts` — `enhanceCitySelect`.

## Ver também
- [[021-tabela-dados-padrao]] — o padrão `.data-table` / `renderTable` que
  as 4 páginas usam.
- [[017-navbar-submenu-relatorios]] — o submenu "Relatórios" que recebe os
  4 filhos.
- [[013-pagina-relatorio-cidade]] — o primeiro relatório, cujo formato de
  resposta o "Consolidado Mensal" reaproveita.
- [[014-camada-referencia]] — `/api/v1/ref/*` consumido pelos filtros.
- [[006-arquitetura-frontend-fastapi]] — estrutura central de páginas.
