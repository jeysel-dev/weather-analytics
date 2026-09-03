# Relatório Detalhamento Horário

## Tipo
[x] Nova feature  [ ] Melhoria  [ ] Bug fix  [ ] Refatoração  [ ] Spec retroativa

## Status
[x] implementado — `/relatorio-horario` no submenu "Relatórios", só tabela
(padrão spec 021): tabela de extremos do período + tabela de resumo diário
com linha de total.

## Resumo
Quinto relatório do submenu. Pega o **dado horário** que hoje só existe em
gráfico na página `/horario` (abas "Temperatura & Umidade" e "Vento &
Chuva" — série de `temperature_c`, `relative_humidity_pct`,
`wind_speed_kmh`, `precipitation_mm` de `mart_climate__hourly_facts`) e
apresenta em duas tabelas para um município + janela (3–30 dias):

1. **Extremos do período** — 6 linhas: maior/menor temperatura,
   maior/menor umidade, maior precipitação em 1 h, maior rajada de vento —
   cada uma com o **instante** em que ocorreu (algo que os marts diários
   não conseguem informar).
2. **Resumo diário** — uma linha por dia: temperatura mín/méd/máx, umidade
   mín/méd/máx, precipitação total, vento máximo; + uma linha `row-total`
   "Total do período" com os mesmos agregados sobre a janela inteira.

## Contexto
- `mart_climate__hourly_facts`: `observed_at` (TIMESTAMP UTC), `date`,
  `hour`, `city_name`, `mesoregion`, `temperature_c`,
  `relative_humidity_pct`, `wind_speed_kmh`, `precipitation_mm`. É a mart
  mais volumosa — **toda query filtra `city_name` + `date`** (nunca varre
  a tabela).
- `app/routers/horario.py` já tem `_cidades()` (cache, municípios COM dado
  horário — subconjunto do seed), `_require_city()` e `_max_date_for(city)`
  (âncora por município). Esta spec **reusa** essas 3 funções em vez de
  duplicar o cache.
- Front do `/horario` usa `xAxis: {type: "time"}` → renderiza em horário
  local do navegador (SC = UTC−3 fixo). Para bater com isso, o instante dos
  extremos é formatado em `America/Sao_Paulo` **no BigQuery**
  (`FORMAT_TIMESTAMP(..., 'America/Sao_Paulo')`) — o endpoint devolve a
  string pronta, o front não faz conversão de fuso.
- Padrão de tabela: `.data-table` + `web/src/table.ts::renderTable`
  (spec 021).

## Requirements (EARS)
- THE página SHALL declarar `Page(path="/relatorio-horario",
  page_id="relatorio-horario", menu_group="Relatórios", menu_position=12)`.
- Filtros: `#filtro-municipio` (populado de `/api/v1/horario/cidades`) e
  `#filtro-dias` (`number`, 3–30, default 7) — paridade com `/horario`.
- `GET /api/v1/relatorio-horario/dados?city=…&days=N`:
  - `_require_city(city)` (404 se não houver dado horário); âncora
    `_max_date_for(city)`; janela `date >= DATE_SUB(@max_date, INTERVAL
    @days DAY)`.
  - Query 1 (um scan): `MAX`/`MIN` de cada métrica + `MAX_BY`/`MIN_BY`
    `(observed_at, métrica)` para o instante, + `AVG` de temp/umidade e
    `SUM` de precip (para a linha de total do resumo diário). O instante
    sai como string via `FORMAT_TIMESTAMP('%d/%m/%Y %Hh', <ts>,
    'America/Sao_Paulo')`.
  - Query 2: `GROUP BY date` — mín/méd/máx de temp e umidade, `SUM` de
    precip, `MAX` de vento, `ORDER BY date`.
  - `max_date is None` → resposta vazia (sem erro).
- Resposta: `{ max_date, extremos: ExtremoHorario[6], dias: DiaHorario[],
  total: DiaHorario | null }`.
- THE template SHALL ter duas `<div class="data-table"><table hidden>`:
  `#tabela-extremos-horario` (Indicador · Valor · Quando) e
  `#tabela-resumo-horario` (Data · Temp. Mín/Méd/Máx (°C) · Umid.
  Mín/Méd/Máx (%) · Precip. Total (mm) · Vento Máx. (km/h)).
- THE `web/src/pages/relatorio-horario.ts` SHALL renderizar as duas com
  `renderTable`; a linha de total usa `variant: "total"` com rótulo
  "Total do período" na coluna Data.
- WHEN nenhum município está selecionado, THE página SHALL mostrar
  "Selecione um município" e não fazer fetch.
- THE `#horario-rel-caption` SHALL mostrar "Dados disponíveis até
  DD/MM/YYYY" a partir do `max_date` da resposta.

## Design

### Decisões de arquitetura
| Decisão | Alternativa | Motivo |
|---|---|---|
| Tabelas = **resumo diário** do dado horário (não a série crua) | Uma linha por hora | 3–30 dias de dado horário = 72–720 linhas; ilegível como tabela e fora do "formato dos relatórios" (que são agregados). O resumo diário é a forma tabular do que os 2 gráficos mostram. |
| Duas tabelas na mesma página (extremos + resumo) | Só a tabela de resumo com a linha de total | A linha de total já dá mín/máx/etc do período, mas **não** o instante. A tabela de extremos existe pelo "quando" — valor que só o grão horário fornece. |
| Instante formatado no BigQuery em `America/Sao_Paulo` | Devolver ISO UTC e formatar no front | O resto do site (`/horario`) mostra horário local; converter fuso no front exigiria `Date`/`Intl` (o `format.ts` evita `Date` de propósito). `FORMAT_TIMESTAMP` resolve no SQL, sem ambiguidade. |
| Reusar `_require_city` / `_max_date_for` / `_cidades` de `horario.py` | Reimplementar aqui | Duplicaria o cache de "municípios com dado horário". Import entre routers do mesmo app — pragmático (precedente: `relatorio_cidade` importa de `ref`). |
| Query 1 junta extremos + médias/somas do total | Query separada para o total do resumo | Mesmo `WHERE`, mesmo scan; o total do resumo diário é derivável da linha de extremos + `AVG`/`SUM`. |
| `MAX_BY`/`MIN_BY(observed_at, métrica)` | `ARRAY_AGG(... ORDER BY ... LIMIT 1)` | Ignora métrica `NULL` nativamente; mesma escolha da spec 022 (extremos). |

### Componentes afetados
- `api/app/main.py` — `import`, `Page` (pos 12), `include_router`.
- `api/app/routers/relatorio_horario.py` — novo.
- `api/app/schemas/relatorio_horario.py` — novo (`ExtremoHorario`,
  `DiaHorario`, `RelatorioHorarioResponse`).
- `api/app/templates/relatorio-horario.html` — novo.
- `web/src/pages/relatorio-horario.ts` — novo.
- `web/src/main.ts` — `import` + `DISPATCH`.
- `api/app/templates/home.html` — 1 `.link-card`.
- `api/tests/test_pages.py` — já parametrizado sobre `PAGES`, cobre a nova.

## Casos de borda
- **Município sem dado horário** → `_require_city` 404; o select só
  oferece municípios de `/api/v1/horario/cidades`, então só acontece por
  URL manual.
- **Janela sem observação** (`max_date` existe mas `days` cai antes do
  primeiro dado) → `extremos` com valores/instantes nulos ("—"), `dias`
  vazio, `total` nulo; a página mostra a mensagem de vazio.
- **Métrica toda `NULL` na janela** (ex.: sensor de vento sem dado) →
  `MAX` e `MAX_BY` vêm `NULL` → linha do indicador com "—".
- **Dia parcial** (o último dia tem só algumas horas) → entra no resumo
  com o que houver; a média é sobre as horas existentes.
- **Precipitação: "maior em 1 h" vs "total do dia"** → a tabela de
  extremos é o pico horário; o resumo diário e o total são `SUM`. Rótulos
  deixam explícito ("em 1 h" / "Total").
- **Horário de verão** → SC não observa DST desde 2019; `America/Sao_Paulo`
  = UTC−3 fixo no período coberto.

## Fora do escopo
- Série horária crua em tabela; export; paginação.
- Aba "Padrão 24h" do `/horario` (média por hora do dia) — não pedida.
- Comparar municípios / macrorregião no mesmo relatório (é 1 município).
- Gráfico (decisão do dono: relatórios são só tabela).
- Estado na URL / compartilhamento.

## Referências de código
- `api/app/routers/horario.py` — `_cidades`, `_require_city`,
  `_max_date_for`, `_HOURLY`.
- `api/app/routers/relatorio_extremos.py` — padrão `MAX_BY`/`MIN_BY` (spec 022).
- `web/src/pages/horario.ts` — filtros (município + dias) e as 2 abas que
  originam o relatório.
- `web/src/table.ts` — `renderTable`, `RowDef` (spec 021).
- `web/src/format.ts` — `formatarDataISO`.

## Ver também
- [[021-tabela-dados-padrao]] — padrão `.data-table` / `renderTable`.
- [[022-relatorios-submenu]] — os 4 relatórios anteriores do submenu.
- [[010-pagina-horario]] — a página cujos gráficos este relatório tabula.
- [[017-navbar-submenu-relatorios]] — o submenu "Relatórios".
