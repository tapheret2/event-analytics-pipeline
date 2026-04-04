-- =============================================================================
-- Staging: stg_events
-- =============================================================================
-- Bridge between Silver layer and Gold layer dbt models.
-- Standardizes column names and applies final business logic filters.
-- =============================================================================

WITH source AS (
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
        COALESCE(product_price, 0)::DECIMAL(12,2)   AS product_price,
        COALESCE(quantity, 0)                         AS quantity,
        COALESCE(revenue, 0)::DECIMAL(12,2)          AS revenue,
        COALESCE(cashback_amount, 0)::DECIMAL(12,2)  AS cashback_amount,
        COALESCE(device_type, 'unknown')              AS device_type,
        COALESCE(browser, 'unknown')                  AS browser,
        COALESCE(country, 'unknown')                  AS country,
        COALESCE(city, 'unknown')                     AS city,
        session_id,
        referrer,
        is_valid,
        quality_flags,
        cleaned_at
    FROM {{ source('silver', 'cleaned_events') }}
    WHERE is_valid = true
)

SELECT * FROM source
