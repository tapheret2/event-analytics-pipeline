-- =============================================================================
-- Gold Model: funnel_analysis
-- =============================================================================
-- Computes the e-commerce conversion funnel showing how users progress
-- from page_view → click → add_to_cart → purchase.
-- =============================================================================

{{
    config(
        materialized='table',
        tags=['funnel', 'reporting']
    )
}}

WITH funnel_stages AS (
    -- Define funnel stages in order
    SELECT 1 AS stage_order, 'page_view'    AS stage_name UNION ALL
    SELECT 2, 'click'                                     UNION ALL
    SELECT 3, 'add_to_cart'                               UNION ALL
    SELECT 4, 'purchase'                                  UNION ALL
    SELECT 5, 'cashback_earned'
),

-- Count unique users who performed each event type (all time)
user_stage_counts AS (
    SELECT
        event_type,
        COUNT(DISTINCT user_id) AS unique_users,
        COUNT(*)                AS total_events
    FROM {{ ref('fact_events') }}
    GROUP BY event_type
),

-- Count unique users who reached each funnel stage
-- A user "reaches" stage N if they performed the event for stage N
funnel_counts AS (
    SELECT
        fs.stage_order,
        fs.stage_name,
        COALESCE(usc.unique_users, 0) AS unique_users,
        COALESCE(usc.total_events, 0) AS total_events
    FROM funnel_stages fs
    LEFT JOIN user_stage_counts usc ON fs.stage_name = usc.event_type
),

-- Calculate conversion rates
funnel_with_rates AS (
    SELECT
        fc.stage_order,
        fc.stage_name,
        fc.unique_users,
        fc.total_events,

        -- Previous stage users
        LAG(fc.unique_users) OVER (ORDER BY fc.stage_order) AS prev_stage_users,

        -- Overall conversion: from top of funnel (page_view)
        CASE
            WHEN FIRST_VALUE(fc.unique_users) OVER (ORDER BY fc.stage_order) > 0
            THEN ROUND(
                fc.unique_users::NUMERIC /
                FIRST_VALUE(fc.unique_users) OVER (ORDER BY fc.stage_order) * 100,
                2
            )
            ELSE 0
        END AS overall_conversion_rate,

        -- Step conversion: from previous stage
        CASE
            WHEN LAG(fc.unique_users) OVER (ORDER BY fc.stage_order) > 0
            THEN ROUND(
                fc.unique_users::NUMERIC /
                LAG(fc.unique_users) OVER (ORDER BY fc.stage_order) * 100,
                2
            )
            ELSE 100.00  -- First stage is always 100%
        END AS step_conversion_rate,

        -- Drop-off: users lost from previous stage
        COALESCE(
            LAG(fc.unique_users) OVER (ORDER BY fc.stage_order) - fc.unique_users,
            0
        ) AS dropoff_count

    FROM funnel_counts fc
)

SELECT
    stage_order,
    stage_name,
    unique_users,
    total_events,
    overall_conversion_rate,
    step_conversion_rate,
    dropoff_count,
    CASE
        WHEN prev_stage_users > 0
        THEN ROUND(dropoff_count::NUMERIC / prev_stage_users * 100, 2)
        ELSE 0
    END AS dropoff_rate

FROM funnel_with_rates
ORDER BY stage_order
