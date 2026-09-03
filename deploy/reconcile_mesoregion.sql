-- =============================================================================
-- Runbook: reconciliar `mesoregion` no histórico das marts após editar o seed
-- `dbt/seeds/locations.csv`.
-- =============================================================================
--
-- POR QUE ISTO EXISTE
-- ------------------
-- `mart_climate__daily_facts` e `mart_climate__hourly_facts` são
-- `materialized='incremental'` (merge por surrogate_key). `mesoregion` é uma
-- coluna DESNORMALIZADA nessas tabelas, copiada de `seeds.locations` via a view
-- `int_weather__daily_enriched` no momento em que cada linha é mesclada.
--
-- Consequência: um `dbt seed` + `dbt run` normal só reescreve as linhas da
-- JANELA DE INGESTÃO (2 dias). Todo o histórico anterior mantém o valor antigo
-- de `mesoregion` gravado. Sem esta reconciliação, uma cidade ficaria com a
-- macrorregião nova nas linhas recentes e a antiga no histórico ("split-brain")
-- — pior que o estado consistente-porém-errado de antes.
--
-- `dbt run --full-refresh` NÃO é opção (regra de ouro do CLAUDE.md: `weather_raw`
-- não retém histórico completo — full rebuild apaga anos de dados).
--
-- Este script faz um UPDATE pontual (DML, casado por `location_id`, só toca a
-- coluna `mesoregion`, não mexe em row count) que traz TODO o histórico para o
-- valor atual do seed. Depois disso, cada `dbt run` incremental mantém as
-- linhas novas corretas sozinho (a view re-junta `locations` a cada run). Só é
-- preciso rodar de novo se o seed `mesoregion` mudar outra vez.
--
-- QUANDO RODAR
-- ------------
-- Sempre que a coluna `mesoregion` de `dbt/seeds/locations.csv` mudar de valor
-- para qualquer município (não é preciso para linhas novas / novos municípios).
--
-- PRÉ-REQUISITO
-- ------------
-- O seed já recarregado no BigQuery com os valores novos:
--     cd /home/ubuntu/app_weather
--     git pull
--     DBT_TARGET=prod docker compose -f docker-compose.pipeline.yml run --rm dbt \
--         seed --select locations
--
-- Rodar os blocos abaixo no console do BigQuery (projeto weather-analytics-490113)
-- ou via `bq query --use_legacy_sql=false < deploy/reconcile_mesoregion.sql`.
-- =============================================================================


-- ── 0. Sanity: o seed tem as 8 macrorregiões esperadas ───────────────────────
SELECT mesoregion, COUNT(*) AS municipios
FROM `weather-analytics-490113.seeds.locations`
GROUP BY mesoregion
ORDER BY mesoregion;
-- Esperado: 8 linhas — Foz do Rio Itajaí / Nordeste, Grande Florianópolis,
-- Grande Oeste, Meio Oeste, Planalto Norte, Serra Catarinense, Sul Catarinense,
-- Vale do Itajaí.


-- ── 1. Snapshot ANTES (guarde estes números) ────────────────────────────────
SELECT
  (SELECT COUNT(*) FROM `weather-analytics-490113.marts.mart_climate__daily_facts`)  AS daily_rows,
  (SELECT COUNT(*) FROM `weather-analytics-490113.marts.mart_climate__hourly_facts`) AS hourly_rows,
  (SELECT COUNT(*) FROM `weather-analytics-490113.marts.mart_climate__alerts`)       AS alert_rows;


-- ── 2. Reconciliar daily_facts ──────────────────────────────────────────────
-- Só reescreve linhas onde o valor gravado difere do seed atual.
UPDATE `weather-analytics-490113.marts.mart_climate__daily_facts` d
SET d.mesoregion = s.mesoregion
FROM `weather-analytics-490113.seeds.locations` s
WHERE d.location_id = s.location_id
  AND d.mesoregion IS DISTINCT FROM s.mesoregion;


-- ── 3. Reconciliar hourly_facts ─────────────────────────────────────────────
-- `mesoregion` é chave de cluster desta tabela; o UPDATE reescreve os blocos
-- afetados (custo único, ~ um run de ingestão). Sem require_partition_filter,
-- o UPDATE sem filtro de data é permitido.
UPDATE `weather-analytics-490113.marts.mart_climate__hourly_facts` h
SET h.mesoregion = s.mesoregion
FROM `weather-analytics-490113.seeds.locations` s
WHERE h.location_id = s.location_id
  AND h.mesoregion IS DISTINCT FROM s.mesoregion;


-- ── 4. Rebuild de alerts ────────────────────────────────────────────────────
-- `mart_climate__alerts` é `materialized='table'` e lê `mesoregion` de
-- daily_facts. Rebuild é seguro (lê de uma mart, não do raw). Rodar via dbt:
--
--     DBT_TARGET=prod docker compose -f docker-compose.pipeline.yml run --rm dbt \
--         run --select mart_climate__alerts
--
-- (ou deixar o próximo run agendado do pipeline reconstruir — alerts é refeita
-- a cada run de qualquer forma.)


-- ── 5. Verificação DEPOIS ───────────────────────────────────────────────────
-- 5a. Row counts idênticos ao snapshot do passo 1 (UPDATE não cria/apaga linha):
SELECT
  (SELECT COUNT(*) FROM `weather-analytics-490113.marts.mart_climate__daily_facts`)  AS daily_rows,
  (SELECT COUNT(*) FROM `weather-analytics-490113.marts.mart_climate__hourly_facts`) AS hourly_rows,
  (SELECT COUNT(*) FROM `weather-analytics-490113.marts.mart_climate__alerts`)       AS alert_rows;

-- 5b. Só as 8 macrorregiões em cada mart, nenhuma órfã do esquema antigo:
SELECT 'daily'  AS mart, mesoregion, COUNT(*) AS linhas
FROM `weather-analytics-490113.marts.mart_climate__daily_facts`  GROUP BY mesoregion
UNION ALL
SELECT 'hourly' AS mart, mesoregion, COUNT(*) AS linhas
FROM `weather-analytics-490113.marts.mart_climate__hourly_facts` GROUP BY mesoregion
ORDER BY mart, mesoregion;

-- 5c. Spot-check: histórico inteiro de Joaçaba / Campos Novos agora é "Meio Oeste":
SELECT location_id, mesoregion, MIN(date) AS desde, MAX(date) AS ate, COUNT(*) AS dias
FROM `weather-analytics-490113.marts.mart_climate__daily_facts`
WHERE location_id IN ('joacaba', 'campos_novos', 'chapeco', 'blumenau', 'lages')
GROUP BY location_id, mesoregion
ORDER BY location_id;
-- Esperado: uma linha por location_id (não duas), com a macrorregião correta
-- cobrindo todo o range de datas.
