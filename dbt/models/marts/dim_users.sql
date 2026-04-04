-- =============================================================================
-- Gold Model: dim_users
-- =============================================================================
-- User dimension table. Aggregates user-level attributes and behavioral
-- metrics. Assigns user segments based on activity patterns.
-- =============================================================================

{{
    config(
        materialized='table',
        tags=['dimension', 'core']
    )
}}

WITH user_events AS (
    SELECT
        user_id,
        MIN(event_date)                                          AS first_seen_date,
        MAX(event_date)                                          AS last_seen_date,
        COUNT(DISTINCT event_date)                               AS active_days,
        COUNT(*)                                                 AS total_events,
        COUNT(*) FILTER (WHERE event_type = 'page_view')         AS page_views,
        COUNT(*) FILTER (WHERE event_type = 'click')             AS clicks,
        COUNT(*) FILTER (WHERE event_type = 'add_to_cart')       AS cart_additions,
        COUNT(*) FILTER (WHERE event_type = 'purchase')          AS purchases,
        COUNT(*) FILTER (WHERE event_type = 'cashback_earned')   AS cashback_events,
        COUNT(*) FILTER (WHERE event_type = 'refund')            AS refunds,
        COALESCE(SUM(revenue) FILTER (WHERE event_type = 'purchase'), 0)    AS total_revenue,
        COALESCE(SUM(cashback_amount) FILTER (WHERE event_type = 'cashback_earned'), 0) AS total_cashback,
        COUNT(DISTINCT session_id)                               AS total_sessions,
        COUNT(DISTINCT product_id)                               AS unique_products_viewed,

        -- Most common attributes (mode)
        MODE() WITHIN GROUP (ORDER BY device_type)               AS primary_device,
        MODE() WITHIN GROUP (ORDER BY browser)                   AS primary_browser,
        MODE() WITHIN GROUP (ORDER BY country)                   AS country,
        MODE() WITHIN GROUP (ORDER BY city)                      AS city

    FROM {{ ref('stg_events') }}
    GROUP BY user_id
),

user_segments AS (
    SELECT
        *,
        -- Calculate days since first/last seen
        CURRENT_DATE - first_seen_date                           AS account_age_days,
        CURRENT_DATE - last_seen_date                            AS days_since_last_active,

        -- Conversion rate
        CASE
            WHEN page_views > 0
            THEN ROUND(purchases::NUMERIC / page_views * 100, 2)
            ELSE 0
        END                                                      AS conversion_rate,

        -- Average order value
        CASE
            WHEN purchases > 0
            THEN ROUND(total_revenue / purchases, 2)
            ELSE 0
        END                                                      AS avg_order_value,

        -- User segment classification
        CASE
            WHEN purchases >= 10 AND active_days >= 15 THEN 'power_user'
            WHEN purchases >= 3 AND active_days >= 5   THEN 'regular'
            WHEN purchases >= 1                        THEN 'casual_buyer'
            WHEN page_views >= 10                      THEN 'window_shopper'
            WHEN CURRENT_DATE - last_seen_date > 30    THEN 'churned'
            ELSE 'new_user'
        END                                                      AS user_segment,

        -- Lifecycle stage
        CASE
            WHEN CURRENT_DATE - first_seen_date <= 7   THEN 'new'
            WHEN CURRENT_DATE - last_seen_date <= 7    THEN 'active'
            WHEN CURRENT_DATE - last_seen_date <= 30   THEN 'at_risk'
            ELSE 'dormant'
        END                                                      AS lifecycle_stage

    FROM user_events
)

SELECT * FROM user_segments
