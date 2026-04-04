-- =============================================================================
-- Gold Model: fact_events
-- =============================================================================
-- Core fact table containing enriched event data. Uses incremental
-- materialization to only process new events since the last run.
-- =============================================================================

{{
    config(
        materialized='incremental',
        unique_key='event_id',
        incremental_strategy='delete+insert',
        tags=['fact', 'core']
    )
}}

WITH events AS (
    SELECT
        event_id,
        user_id,
        event_type,
        event_timestamp,
        event_date,
        event_hour,
        page_url,
        product_id,
        product_name,
        product_category,
        product_price,
        quantity,
        revenue,
        cashback_amount,
        device_type,
        browser,
        country,
        city,
        session_id,
        referrer,

        -- Derived: time-based dimensions
        EXTRACT(DOW FROM event_date)::INTEGER       AS day_of_week,
        EXTRACT(MONTH FROM event_date)::INTEGER     AS event_month,
        EXTRACT(YEAR FROM event_date)::INTEGER      AS event_year,
        CASE
            WHEN EXTRACT(DOW FROM event_date) IN (0, 6) THEN true
            ELSE false
        END                                          AS is_weekend,

        -- Derived: session-level attributes
        CASE
            WHEN event_hour BETWEEN 6 AND 11 THEN 'morning'
            WHEN event_hour BETWEEN 12 AND 14 THEN 'lunch'
            WHEN event_hour BETWEEN 15 AND 18 THEN 'afternoon'
            WHEN event_hour BETWEEN 19 AND 22 THEN 'evening'
            ELSE 'night'
        END                                          AS time_of_day,

        -- Derived: revenue flags
        CASE WHEN revenue > 0 THEN true ELSE false END   AS is_revenue_event,
        CASE WHEN cashback_amount > 0 THEN true ELSE false END AS is_cashback_event

    FROM {{ ref('stg_events') }}

    {% if is_incremental() %}
        WHERE event_date >= (
            SELECT COALESCE(MAX(event_date) - INTERVAL '{{ var("lookback_days") }} days', '{{ var("min_date") }}')
            FROM {{ this }}
        )
    {% endif %}
)

SELECT * FROM events
