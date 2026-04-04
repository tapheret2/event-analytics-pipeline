-- =============================================================================
-- Gold Model: daily_kpis
-- =============================================================================
-- Pre-aggregated daily KPI metrics for fast dashboard queries.
-- Includes DAU, WAU, revenue, cashback, conversion rate, and event counts.
-- =============================================================================

{{
    config(
        materialized='incremental',
        unique_key='event_date',
        incremental_strategy='delete+insert',
        tags=['kpi', 'reporting']
    )
}}

WITH daily_metrics AS (
    SELECT
        event_date,

        -- User metrics
        COUNT(DISTINCT user_id)                                  AS dau,
        COUNT(DISTINCT session_id)                               AS daily_sessions,

        -- Event counts by type
        COUNT(*)                                                 AS total_events,
        COUNT(*) FILTER (WHERE event_type = 'page_view')         AS page_views,
        COUNT(*) FILTER (WHERE event_type = 'click')             AS clicks,
        COUNT(*) FILTER (WHERE event_type = 'add_to_cart')       AS add_to_carts,
        COUNT(*) FILTER (WHERE event_type = 'purchase')          AS purchases,
        COUNT(*) FILTER (WHERE event_type = 'cashback_earned')   AS cashback_events,
        COUNT(*) FILTER (WHERE event_type = 'refund')            AS refunds,

        -- Revenue metrics
        COALESCE(SUM(revenue) FILTER (WHERE event_type = 'purchase'), 0)::DECIMAL(12,2) AS daily_revenue,
        COALESCE(SUM(cashback_amount) FILTER (WHERE event_type = 'cashback_earned'), 0)::DECIMAL(12,2) AS daily_cashback,
        COALESCE(SUM(ABS(revenue)) FILTER (WHERE event_type = 'refund'), 0)::DECIMAL(12,2) AS daily_refunds,

        -- Unique counts
        COUNT(DISTINCT user_id) FILTER (WHERE event_type = 'purchase') AS purchasing_users,
        COUNT(DISTINCT product_id) FILTER (WHERE event_type = 'purchase') AS products_sold,

        -- Device breakdown
        COUNT(DISTINCT user_id) FILTER (WHERE device_type = 'mobile')  AS mobile_users,
        COUNT(DISTINCT user_id) FILTER (WHERE device_type = 'desktop') AS desktop_users,
        COUNT(DISTINCT user_id) FILTER (WHERE device_type = 'tablet')  AS tablet_users

    FROM {{ ref('fact_events') }}

    {% if is_incremental() %}
        WHERE event_date >= (
            SELECT COALESCE(MAX(event_date) - INTERVAL '{{ var("lookback_days") }} days', '{{ var("min_date") }}')
            FROM {{ this }}
        )
    {% endif %}

    GROUP BY event_date
),

enriched AS (
    SELECT
        dm.*,

        -- Conversion rate: purchasers / viewers
        CASE
            WHEN dm.page_views > 0
            THEN ROUND(dm.purchases::NUMERIC / dm.page_views * 100, 4)
            ELSE 0
        END AS conversion_rate,

        -- Average order value
        CASE
            WHEN dm.purchases > 0
            THEN ROUND(dm.daily_revenue / dm.purchases, 2)
            ELSE 0
        END AS avg_order_value,

        -- Revenue per user
        CASE
            WHEN dm.dau > 0
            THEN ROUND(dm.daily_revenue / dm.dau, 2)
            ELSE 0
        END AS revenue_per_user,

        -- WAU (7-day rolling window of distinct users)
        (
            SELECT COUNT(DISTINCT f2.user_id)
            FROM {{ ref('fact_events') }} f2
            WHERE f2.event_date BETWEEN dm.event_date - INTERVAL '6 days' AND dm.event_date
        ) AS wau

    FROM daily_metrics dm
)

SELECT * FROM enriched
ORDER BY event_date
