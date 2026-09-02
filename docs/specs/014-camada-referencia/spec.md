# Camada de referência compartilhada — endpoints `/api/v1/ref/*` e `web/src/labels.ts`

## Tipo
[x] Nova feature (infraestrutura transversal da migração FastAPI) —
consolida decisões que já apareceram, repetidas, nas specs de página
007/008/009/012/013.

## Status
[x] proposta — nenhum código de `api/` ou `web/` escrito. Esta spec fixa
os contratos de dado de referência que as specs de página passam a
**consumir**, não a redefinir.

## Resumo
Definir, num único lugar, os endpoints JSON de **dado de referência** que
várias páginas migradas precisam (lista de municípios, lista de
mesorregiões, data mínima/máxima por tabela) e o módulo TypeScript
compartilhado de **rótulos e cores** (`web/src/labels.ts`). Cada contrato
é especificado aqui uma vez; as specs de página referenciam
`[[014-camada-referencia]]` em vez de reescrever a mesma query e o mesmo
endpoint.

## Contexto
Origem do achado: ao escrever as 7 specs de página da migração
(007–013, ver [[006-arquitetura-frontend-fastapi]]), o mesmo punhado de
consultas apareceu repetido em quase todas:

- **Lista de mesorregiões** (`SELECT DISTINCT mesoregion FROM locations
  WHERE mesoregion IS NOT NULL ORDER BY mesoregion`) — hoje repetida
  literalmente em `1_Temperatura.py`, `2_Precipitacao.py`, `3_Alertas.py`
  e `6_Comparativo.py`.
- **Lista de municípios** (`SELECT city_name FROM locations ORDER BY
  city_name`) — repetida em `6_Comparativo.py` e `7_Relatorio_Cidade.py`;
  `5_Cidades.py` usa uma variante com metadados.
- **`MAX(date)` / `MIN(date)` de uma mart** — o helper `max_date()` /
  `min_date()` de `streamlit/utils/bigquery.py` é chamado em praticamente
  toda página, para ancorar o filtro de período no dado real (regra do
  `CLAUDE.md`, seção "filtros de data ancoram no dado real").
- **Traduções de enum** (`ALERT_TYPE_PT`, `SEVERITY_PT`, `CLASS_LABELS_PT`
  em `streamlit/utils/labels.py`) + **mapas de cor/ícone** que hoje estão
  *duplicados* como constantes locais em `2_Precipitacao.py`,
  `3_Alertas.py` e `5_Cidades.py` (ex.: `CLASS_COLORS` aparece idêntico em
  duas páginas).

Sem uma camada compartilhada, cada spec de página reimplementaria a mesma
query e o mesmo endpoint — duplicação de código e risco de divergência
(uma página ordenando a lista diferente da outra, uma âncora de data
calculada de um jeito numa página e de outro em outra).

## Investigação
O que cada spec de página já propôs individualmente (a consolidar aqui):

| Spec | Endpoints de referência citados | Rótulos compartilhados citados |
|---|---|---|
| [[007-pagina-temperatura]] | `/api/v1/ref/mesorregioes`, `/api/v1/ref/daily-meta` | — |
| [[008-pagina-precipitacao]] | `/api/v1/ref/mesorregioes`, `/api/v1/ref/daily-meta` | `CLASS_LABELS_PT` + cores por classe (`web/src/labels.ts`) |
| [[009-pagina-alertas]] | `/api/v1/ref/mesorregioes`, `/api/v1/ref/alerts-meta` | `ALERT_TYPE_PT`, `SEVERITY_PT` + cor/ícone por severidade |
| [[011-pagina-cidades]] | (usa `/api/v1/cidades/lista` próprio, com metadados) | `CLASS_LABELS_PT`, `CLASS_COLORS`, `ALERT_TYPE_PT`, `SEVERITY_PT` |
| [[012-pagina-comparativo]] | `/api/v1/ref/cidades`, `/api/v1/ref/mesorregioes` | faixas Seco→Extremo (mesmo vocabulário de `CLASS_LABELS_PT`) |
| [[013-pagina-relatorio-cidade]] | `/api/v1/ref/cidades` (+ `/limites` próprio, agora absorvido por `daily-meta`) | — |

Fontes de dado atuais (`streamlit/`):

```python
# streamlit/utils/bigquery.py
def max_date(table): ...   # SELECT MAX(date) AS max_date FROM {tbl(table)}
def min_date(table): ...   # SELECT MIN(date) AS min_date FROM {tbl(table)}
```
```sql
-- mesorregiões (repetido em 4 páginas)
SELECT DISTINCT mesoregion FROM `<seeds>.locations`
WHERE mesoregion IS NOT NULL ORDER BY mesoregion
-- municípios (repetido em 2 páginas, + variante com metadados na 5)
SELECT city_name FROM `<seeds>.locations` ORDER BY city_name
```
```python
# streamlit/utils/labels.py — traduções canônicas
ALERT_TYPE_PT   = {"cold_anomaly": "Anomalia de Frio", "precip_anomaly": "Anomalia de Precipitação",
                   "heat_anomaly": "Anomalia de Calor", "heavy_rain": "Chuva Forte"}
SEVERITY_PT     = {"critical": "Crítica", "high": "Alta", "medium": "Média", "low": "Baixa"}
CLASS_LABELS_PT = {"dry": "Seco", "light": "Leve", "moderate": "Moderado",
                   "heavy": "Forte", "extreme": "Extremo"}
```
```python
# duplicado como constante local em 2_Precipitacao.py E 5_Cidades.py
CLASS_COLORS = {"dry": "#78909C", "light": "#4FC3F7", "moderate": "#0288D1",
                "heavy": "#1565C0", "extreme": "#4A148C"}
# 3_Alertas.py
SEV_COLORS = {"critical": "#D32F2F", "high": "#F57C00", "medium": "#FBC02D", "low": "#388E3C"}
SEV_ICON   = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
```

## Requirements (EARS)

### Funcionais — endpoints de referência
- THE system SHALL expor `GET /api/v1/ref/mesorregioes`, retornando a lista
  de mesorregiões distintas do seed `locations` (`mesoregion IS NOT NULL`,
  ordenada alfabeticamente). Este é o **único** lugar onde essa query é
  definida; as specs de página que precisam do filtro de mesorregião
  consomem este endpoint.
- THE system SHALL expor `GET /api/v1/ref/cidades`, retornando a lista de
  `city_name` do seed `locations` ordenada alfabeticamente — **só os
  nomes**, sem metadados. WHEN uma página precisa de metadados por
  município (latitude, longitude, altitude, mesorregião), ela SHALL usar um
  endpoint próprio (`/api/v1/cidades/lista`, definido em
  [[011-pagina-cidades]]), não este.
- THE system SHALL expor `GET /api/v1/ref/daily-meta`, retornando
  `min_date` e `max_date` de `mart_climate__daily_facts`.
- THE system SHALL expor `GET /api/v1/ref/alerts-meta`, retornando
  `min_date` e `max_date` de `mart_climate__alerts`.
- WHERE uma página ancora um filtro de período no dado real, THE âncora
  SHALL vir de `/api/v1/ref/daily-meta` ou `/api/v1/ref/alerts-meta`
  conforme a tabela consultada — nunca de `CURRENT_DATE()` (regra do
  `CLAUDE.md` e da [[006-arquitetura-frontend-fastapi]]).
- THE endpoint `/api/v1/ref/daily-meta` SHALL substituir o
  `/api/v1/relatorio-cidade/limites` que [[013-pagina-relatorio-cidade]]
  havia proposto isoladamente (mesmo dado: `min_date` + `max_date` de
  `daily_facts`).
- IF `mart_climate__daily_facts` ou `mart_climate__alerts` estiver vazia,
  THE endpoint `*-meta` correspondente SHALL retornar `min_date` e
  `max_date` nulos (não erro), e a página consumidora SHALL degradar com a
  sua própria mensagem de "sem dados".

### Funcionais — módulo `web/src/labels.ts`
- THE frontend SHALL ter um módulo único `web/src/labels.ts` exportando:
  - `ALERT_TYPE_PT`, `SEVERITY_PT`, `CLASS_LABELS_PT` — cópia fiel dos
    dicionários de `streamlit/utils/labels.py` (mesmas chaves, mesmos
    valores em português).
  - `CLASS_COLORS`, `SEV_COLORS`, `SEV_ICON` — cópia fiel dos mapas de
    cor/ícone hoje duplicados nas páginas Streamlit.
- WHEN uma página migrada exibe `alert_type`, `severity` ou
  `precipitation_class`, THE rótulo/cor/ícone SHALL vir de
  `web/src/labels.ts` — nenhuma spec de página SHALL redefinir esses
  dicionários localmente.
- WHERE um valor de enum não existe no dicionário, THE apresentação SHALL
  cair no valor cru (paridade com o `.map(...).fillna(<cru>)` do Streamlit).
- WHERE a tradução precisa acontecer no servidor (ex.: a tabela de alertas
  recentes de [[009-pagina-alertas]], que devolve o rótulo já pronto no
  JSON), THE backend SHALL usar a mesma fonte canônica — um
  `api/utils/labels.py` adaptado de `streamlit/utils/labels.py`. `labels.ts`
  e `api/utils/labels.py` SHALL ter os mesmos pares chave→valor.

### Não-funcionais
- THE rotas `/api/v1/ref/*` SHALL ser síncronas (`def`), reusando o
  cliente BigQuery de `api/utils/bigquery.py`.
- THE respostas de `/api/v1/ref/mesorregioes` e `/api/v1/ref/cidades`
  SHALL ser cacheáveis em processo (as listas mudam só quando o seed
  `locations` muda — raramente); um `@lru_cache` ou equivalente é
  suficiente, sem invalidação automática exigida nesta spec.
- THE respostas de `*-meta` NÃO SHALL ser cacheadas com TTL longo — a
  `max_date` muda a cada run do pipeline (1x/dia); um cache curto
  (minutos) ou nenhum cache.
- THE nomes exatos dos 4 endpoints (`mesorregioes`, `cidades`,
  `daily-meta`, `alerts-meta`) SHALL ser tratados como contrato — mudar um
  nome exige atualizar as specs de página que o citam.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Um router `api/routers/ref.py` com os 4 endpoints | Cada página expõe seu próprio endpoint de referência | Evita 4× a mesma query espalhada; garante ordenação/filtro idênticos entre páginas. |
| `/api/v1/ref/cidades` devolve só nomes; metadados ficam em `/api/v1/cidades/lista` | Um único endpoint "gordo" de municípios com tudo | 5 das 6 páginas que listam municípios só querem o nome para um `<select>`; carregar lat/lon/altitude/meso para todas seria desperdício. A página que precisa (Cidades) tem endpoint dedicado. |
| `daily-meta` / `alerts-meta` devolvem `min` **e** `max` | Só `max` (que é o uso mais comum) | [[013-pagina-relatorio-cidade]] precisa de `min_date` para o seletor de intervalo; devolver os dois evita um segundo endpoint. Absorve o `/limites` que a 013 havia proposto. |
| `labels.ts` (frontend) + `api/utils/labels.py` (backend) espelhados | Só backend traduzir tudo, frontend nunca | A maioria das páginas traduz no cliente ao desenhar o gráfico; forçar tudo no backend inflaria os payloads e acoplaria cada endpoint a apresentação. Onde o backend já monta tabela (009), ele traduz — usando a mesma fonte. |
| Cor/ícone no frontend (`labels.ts`), nunca no JSON dos endpoints | Endpoint devolver `color` / emoji | Cor e emoji são pura apresentação; não pertencem ao contrato de dado. |

### Componentes afetados
- `api/routers/ref.py` — **novo**. Os 4 endpoints `/api/v1/ref/*`, rotas
  síncronas, cache em processo nas duas listas.
- `api/utils/bigquery.py` — reusa `query()`, `tbl()`, `max_date()`,
  `min_date()` adaptados de `streamlit/utils/bigquery.py`.
- `api/utils/labels.py` — **novo**. Cópia de `streamlit/utils/labels.py`
  (fonte canônica das traduções no backend).
- `web/src/labels.ts` — **novo**. Dicionários de rótulo + mapas de
  cor/ícone, importado pelos módulos TS de página.
- Specs de página [[007-pagina-temperatura]], [[008-pagina-precipitacao]],
  [[009-pagina-alertas]], [[011-pagina-cidades]],
  [[012-pagina-comparativo]], [[013-pagina-relatorio-cidade]] — passam a
  **referenciar** esta spec para os contratos de referência/rótulo, em vez
  de os redefinir.
- [[006-arquitetura-frontend-fastapi]] — ganha um ponteiro para esta spec
  em "Ver também" e uma linha em Design reconhecendo a camada.

### Contrato dos endpoints (resumo)
| Endpoint | Retorno | Fonte | Consumido por |
|---|---|---|---|
| `GET /api/v1/ref/mesorregioes` | lista ordenada de mesorregiões | seed `locations` | 007, 008, 009, 012 |
| `GET /api/v1/ref/cidades` | lista ordenada de `city_name` | seed `locations` | 012, 013 |
| `GET /api/v1/ref/daily-meta` | `{ min_date, max_date }` | `mart_climate__daily_facts` | 007, 008, 011, 012, 013 |
| `GET /api/v1/ref/alerts-meta` | `{ min_date, max_date }` | `mart_climate__alerts` | 009, 011 |

## Casos de borda
- **Seed `locations` vazio / inacessível** → `/api/v1/ref/mesorregioes` e
  `/api/v1/ref/cidades` retornam lista vazia; as páginas mostram o
  `<select>` vazio + a mensagem de erro que cada uma já define.
- **Mart vazia** → `*-meta` retorna `min_date`/`max_date` nulos; a página
  consumidora não deve montar janela de data com `null`.
- **`max_date` de `daily_facts` ≠ `max_date` de `alerts`** → esperado
  (tabelas atualizadas por passos diferentes do pipeline); por isso são
  dois endpoints, não um.
- **Divergência entre `labels.ts` e `api/utils/labels.py`** → risco real;
  mitigar com um teste que compara os pares chave→valor dos dois lados (a
  spec não obriga o teste, mas registra a recomendação).
- **Novo valor de enum na mart** (ex.: um `alert_type` novo) → cai no
  valor cru nos dois lados; atualizar os dicionários é uma mudança pontual
  aqui, não em N páginas.

## Fora do escopo
- **Endpoint de municípios com metadados** (`/api/v1/cidades/lista`) —
  pertence a [[011-pagina-cidades]], não a esta spec.
- **Cache distribuído / invalidação automática** das listas de referência
  — `@lru_cache` em processo basta para o volume atual (295 municípios, 6
  mesorregiões).
- **Internacionalização (i18n) real** — os rótulos são PT-BR fixos, como
  hoje; nenhuma infraestrutura de múltiplos idiomas.
- **Mudar a fonte das mesorregiões** de seed para uma tabela dbt — mantém
  o seed `locations` como fonte canônica, igual ao Streamlit.
- **Reescrever `streamlit/utils/`** — o código Streamlit permanece
  intacto até o corte final (fora do escopo da [[006-arquitetura-frontend-fastapi]]).

## Referências de código
- `streamlit/utils/bigquery.py` — `max_date()`, `min_date()`, `query()`,
  `tbl()`; base dos endpoints `*-meta`.
- `streamlit/utils/labels.py` — `ALERT_TYPE_PT`, `SEVERITY_PT`,
  `CLASS_LABELS_PT`; fonte canônica das traduções.
- `streamlit/pages/1_Temperatura.py`, `2_Precipitacao.py`, `3_Alertas.py`,
  `6_Comparativo.py` — cada um repete a query de mesorregiões.
- `streamlit/pages/6_Comparativo.py`, `7_Relatorio_Cidade.py` — repetem a
  query de municípios.
- `streamlit/pages/2_Precipitacao.py`, `5_Cidades.py` — `CLASS_COLORS`
  duplicado.
- `docs/specs/006-arquitetura-frontend-fastapi/spec.md` — arquitetura da
  migração.

## Ver também
- [[006-arquitetura-frontend-fastapi]] — spec fundacional; esta camada é
  uma peça da estrutura `api/` que ela descreve.
- [[007-pagina-temperatura]] — consome `ref/mesorregioes`, `ref/daily-meta`.
- [[008-pagina-precipitacao]] — consome `ref/mesorregioes`,
  `ref/daily-meta`, `labels.ts`.
- [[009-pagina-alertas]] — consome `ref/mesorregioes`, `ref/alerts-meta`,
  `labels.ts` + `api/utils/labels.py`.
- [[011-pagina-cidades]] — consome `ref/daily-meta`, `ref/alerts-meta`,
  `labels.ts`; tem endpoint próprio de municípios com metadados.
- [[012-pagina-comparativo]] — consome `ref/cidades`, `ref/mesorregioes`,
  `ref/daily-meta`.
- [[013-pagina-relatorio-cidade]] — consome `ref/cidades`,
  `ref/daily-meta` (que absorve o antigo `/limites`).
- [[010-pagina-horario]] — **não** consome esta camada (lista de cidades
  vem da própria `hourly_facts`, âncora de data é por município).
