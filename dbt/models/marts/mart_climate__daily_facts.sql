{{
  config(
    materialized = 'incremental',
    unique_key = 'surrogate_key',
    incremental_strategy = 'merge',
    on_schema_change = 'sync_all_columns',
    schema = 'marts',
    partition_by = {
      "field": "date",
      "data_type": "date",
      "granularity": "month"
    },
    cluster_by = ["location_id", "year_month"]
  )
}}

-- INCREMENTAL POR NECESSIDADE, NÃO SÓ POR CUSTO: weather_raw guarda só uma
-- janela recente (ver ingest.py), então um full rebuild ('table') aqui
-- reconstruiria a tabela inteira a partir de uns poucos dias de raw,
-- destruindo o histórico acumulado. Já aconteceu uma vez em produção e foi
-- restaurado via BigQuery time travel — não reverter para 'table' sem
-- garantir que weather_raw.open_meteo_daily tenha o histórico completo de
-- novo. Lookback generoso (35d) dá margem para a rolling average de 30
-- dias em int_weather__daily_enriched.
with enriched as (
    select * from {{ ref('int_weather__daily_enriched') }}
    {% if is_incremental() %}
    where date >= (
        select date_sub(max(date), interval 35 day) from {{ this }}
    )
    {% endif %}
),

final as (
    select
        -- Chave única da linha
        {{ dbt_utils.generate_surrogate_key(['location_id', 'date']) }} as surrogate_key,

        -- Dimensão tempo
        date,
        CAST(extract(year from date) AS {{ dbt.type_int() }})     as year,
        CAST(extract(month from date) AS {{ dbt.type_int() }})    as month,
        CAST(extract(day from date) AS {{ dbt.type_int() }})      as day,
        {% if target.type == 'bigquery' %}
        FORMAT_DATE('%Y-%m', date)
        {% else %}
        to_char(date, 'YYYY-MM')
        {% endif %}                                                as year_month,
        CAST({% if target.type == 'bigquery' %}EXTRACT(DAYOFWEEK FROM date) - 1{% else %}extract(dow from date){% endif %} AS {{ dbt.type_int() }}) as day_of_week,
        case
            when {% if target.type == 'bigquery' %}EXTRACT(DAYOFWEEK FROM date) - 1{% else %}extract(dow from date){% endif %} in (0, 6)
            then true else false
        end                                                        as is_weekend,
        CAST(extract(quarter from date) AS {{ dbt.type_int() }})  as quarter,

        -- Dimensão localização
        location_id,
        city_name,
        state_name,
        country,
        region,
        mesoregion,
        latitude,
        longitude,
        altitude_m,

        -- Métricas de temperatura
        temp_max_c,
        temp_min_c,
        temp_avg_c,
        round(temp_max_c - temp_min_c, 2)                         as temp_amplitude_c,

        -- Anomalia de temperatura
        round(temp_avg_c - temp_avg_30d_c, 2)                     as temp_anomaly_c,
        temp_avg_30d_c,

        -- Precipitação
        precipitation_mm,
        rain_mm,
        precip_avg_30d_mm,
        round(precipitation_mm - precip_avg_30d_mm, 2)            as precip_anomaly_mm,
        case
            when precipitation_mm = 0     then 'dry'
            when precipitation_mm < 5     then 'light'
            when precipitation_mm < 20    then 'moderate'
            when precipitation_mm < 50    then 'heavy'
            else 'extreme'
        end                                                        as precipitation_class,

        -- Vento e UV
        wind_speed_max_kmh,
        uv_index_max,
        case
            when uv_index_max < 3  then 'low'
            when uv_index_max < 6  then 'moderate'
            when uv_index_max < 8  then 'high'
            when uv_index_max < 11 then 'very_high'
            else 'extreme'
        end                                                        as uv_risk_level,

        -- Horas de sol
        sunrise_at,
        sunset_at,
        daylight_hours,

        -- Metadados de pipeline
        _extracted_at,
        _loaded_at,
        current_timestamp                                          as _dbt_updated_at

    from enriched
)

select * from final
