# Daylight hours — ajustar threshold do teste `accepted_range`

## Tipo
[x] Spec retroativa — investigação de falha recorrente no `dbt test` do
weather-pipeline.

## Status
[x] implementado e validado — `max_value` ajustado para `14.05` em
`dbt/models/marts/schema/mart_climate.yml:203-210`. Validado contra BigQuery
de produção via overlay do código local sobre a imagem/credenciais de
produção (`dbt deps` + `dbt test --select mart_climate__daily_facts`, target
prod): 22/22 testes passaram, incluindo
`dbt_utils_accepted_range_mart_climate__daily_facts_daylight_hours__14_05__10`
(antes `__14__10`, 139 falhas). Fix ainda não publicado via push/deploy —
validação rodou sobre overlay temporário, não sobre a imagem em produção
atual.

## Resumo
O teste `dbt_utils.accepted_range` em `daylight_hours`
(`mart_climate__daily_facts`) falha recorrentemente com 139 violações. A causa
raiz é threshold sem folga suficiente para a variação sazonal real em
municípios de latitude mais extrema cobertos pelo pipeline — não um bug de
cálculo.

## Contexto
Achado herdado de investigação realizada no repositório `infra` (sem spec
numerada associada), confirmado nesta sessão via consulta direta ao
BigQuery: o teste
`dbt_utils_accepted_range_mart_climate__daily_facts_daylight_hours__14__10`
falha com 139 linhas de `daylight_hours` fora do range configurado `[10, 14]`
horas (`dbt/models/marts/schema/mart_climate.yml:203-208`).

## Investigação

### Todas as 139 violações são de teto, nenhuma de piso
As 139 linhas fora do range têm `daylight_hours > 14` — zero linhas com
`daylight_hours < 10`. Isso já é um sinal contra hipótese de erro de dado
disperso (ver Casos de borda).

### Concentradas em 6 municípios de latitude extrema, no solstício de verão
As violações concentram-se em 6 municípios com latitude entre ~-29.1° e
-29.3° (extremo sul da área coberta pelo pipeline), todas na janela de
16–27/dez — em torno do solstício de verão no hemisfério sul, quando dias são
fisicamente mais longos nas latitudes mais ao sul.

### Valor sempre idêntico: 14.0166... (14h01min), repetindo-se 2021–2025
O valor de `daylight_hours` nas violações não varia de forma dispersa — é
consistentemente `14.0166...` (14h01min), repetindo-se ano após ano
(2021–2025) para os mesmos municípios na mesma janela do calendário. Um erro
de cálculo ou de fuso horário produziria valores dispersos/inconsistentes
entre execuções; um valor determinístico que se repete ano a ano na mesma
época do calendário é a assinatura esperada de um fenômeno astronômico real
(comprimento do dia no solstício), não de um bug.

### Cálculo confirmado correto
`daylight_hours` é calculado em
`dbt/models/intermediate/int_weather__daily_enriched.sql` como
`sunset_at - sunrise_at` (via `TIMESTAMP_DIFF` no BigQuery), sem conversão de
fuso timezone-naive nem lógica suspeita — `sunrise_at`/`sunset_at` vêm da API
Open-Meteo já em UTC consistente, propagados sem transformação adicional
desde `stg_weather__daily.sql`. Não há indício de bug de timezone ou de
fonte de dado incorreta.

## Requirements (EARS)

### Funcionais
- THE system SHALL ajustar `max_value` do teste `dbt_utils.accepted_range` em
  `dbt/models/marts/schema/mart_climate.yml:203-208` de `14` para `14.05`
  (folga acima do valor máximo real observado, `14.0166...`, sem abrir mão da
  capacidade do teste de pegar um valor genuinamente anômalo).
- THE system SHALL adicionar um comentário no `mart_climate.yml` acima do
  teste ajustado, documentando o motivo do novo `max_value` e citando esta
  spec (`002-daylight-hours-threshold`), para que uma futura revisão do
  threshold não precise refazer a investigação.

### Não-funcionais
- O ajuste SHALL preservar a capacidade do teste de detectar valores
  fisicamente implausíveis (`min_value` permanece `10` — nenhuma violação de
  piso foi observada, sem evidência para alterá-lo).
- O ajuste NÃO SHALL exigir mudança em `int_weather__daily_enriched.sql` ou em
  qualquer lógica de cálculo — a investigação confirmou que o cálculo está
  correto; a mudança é só de calibração do teste.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Ajustar `max_value` para `14.05` | Investigar/corrigir cálculo de `daylight_hours` (hipótese de bug) | Descartada — cálculo confirmado correto (ver Investigação); valor determinístico e repetido ano a ano é assinatura de fenômeno real, não de bug |
| Ajustar `max_value` para `14.05` | Remover o teste `accepted_range` inteiramente | Perderia a capacidade de detectar um valor genuinamente implausível (ex. `daylight_hours` de 20h indicaria erro real); manter o teste com folga adequada é mais seguro que removê-lo |

### Componentes afetados
- `dbt/models/marts/schema/mart_climate.yml:203-208` — `max_value` do teste
  `dbt_utils.accepted_range` em `daylight_hours`, mais comentário de contexto.

## Casos de borda
Por que a hipótese de bug de cálculo foi descartada: um bug de cálculo ou de
fuso horário tipicamente produz valores dispersos e inconsistentes entre
execuções/datas — não é isso que os dados mostram. Aqui, (a) nenhuma violação
de piso (só teto), (b) o valor é único e determinístico (`14.0166...`,
não uma faixa de valores diferentes), e (c) o padrão se repete identicamente
nos mesmos municípios e na mesma janela do calendário em 5 anos consecutivos
(2021–2025). Essa combinação — sem dispersão, mas com repetição
determinística ano a ano — é o padrão esperado de dia mais longo do ano em
latitude específica, não de erro de dado.

## Fora do escopo
- Qualquer mudança no `int_weather__daily_enriched.sql` ou na fonte do dado —
  cálculo confirmado correto, sem necessidade de alteração.
- Aplicar o ajuste de threshold em si — fica para depois desta spec ser
  aprovada; este documento só formaliza o requirement.
- Qualquer mudança no infra (deploy, cron, compose) — fora do escopo deste
  repositório; acompanhar via specs 018 e 041 do projeto `infra` (ambas ainda
  não implementadas na data desta spec).

## Referências de código
`dbt/models/marts/schema/mart_climate.yml`,
`dbt/models/intermediate/int_weather__daily_enriched.sql`,
`dbt/models/staging/stg_weather__daily.sql`.

## Ver também
- [[001-atualizar-docs-arquitetura]] — spec independente, sem sobreposição de
  escopo.
