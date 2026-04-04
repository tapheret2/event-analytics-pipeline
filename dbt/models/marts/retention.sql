-- =============================================================================
-- Gold Model: retention
-- =============================================================================
-- Cohort-based retention analysis. Users are grouped by their first activity
-- date (cohort), then tracked for return visits at Day 1, 7, 14, and 30.
-- =============================================================================

{{
    config(
        materialized='table',
        tags=['retention', 'reporting']
    )
}}

WITH user_first_activity AS (
    -- Determine each user's first activity date (cohort date)
    SELECT
        user_id,
        MIN(event_date) AS cohort_date
    FROM {{ ref('fact_events') }}
    GROUP BY user_id
),

user_activity_dates AS (
    -- All distinct dates a user was active
    SELECT DISTINCT
        user_id,
        event_date AS activity_date
    FROM {{ ref('fact_events') }}
),

cohort_activity AS (
    -- Join user activity with their cohort date
    SELECT
        ufa.user_id,
        ufa.cohort_date,
        uad.activity_date,
        (uad.activity_date - ufa.cohort_date) AS days_since_signup
    FROM user_first_activity ufa
    INNER JOIN user_activity_dates uad ON ufa.user_id = uad.user_id
),

-- Weekly cohort aggregation
weekly_cohorts AS (
    SELECT
        DATE_TRUNC('week', cohort_date)::DATE AS cohort_week,
        COUNT(DISTINCT user_id) AS cohort_size,

        -- Day 0 (signup day) — always 100%
        COUNT(DISTINCT user_id) FILTER (WHERE days_since_signup = 0) AS retained_day_0,

        -- Day 1 retention
        COUNT(DISTINCT user_id) FILTER (WHERE days_since_signup = 1) AS retained_day_1,

        -- Day 3 retention
        COUNT(DISTINCT user_id) FILTER (WHERE days_since_signup = 3) AS retained_day_3,

        -- Day 7 retention (Week 1)
        COUNT(DISTINCT user_id) FILTER (WHERE days_since_signup = 7) AS retained_day_7,

        -- Day 14 retention (Week 2)
        COUNT(DISTINCT user_id) FILTER (WHERE days_since_signup = 14) AS retained_day_14,

        -- Day 30 retention (Month 1)
        COUNT(DISTINCT user_id) FILTER (WHERE days_since_signup = 30) AS retained_day_30,

        -- Week 1 retention (any activity in days 1-7)
        COUNT(DISTINCT user_id) FILTER (
            WHERE days_since_signup BETWEEN 1 AND 7
        ) AS retained_week_1,

        -- Week 2 retention (any activity in days 8-14)
        COUNT(DISTINCT user_id) FILTER (
            WHERE days_since_signup BETWEEN 8 AND 14
        ) AS retained_week_2,

        -- Week 3 retention (any activity in days 15-21)
        COUNT(DISTINCT user_id) FILTER (
            WHERE days_since_signup BETWEEN 15 AND 21
        ) AS retained_week_3,

        -- Week 4 retention (any activity in days 22-28)
        COUNT(DISTINCT user_id) FILTER (
            WHERE days_since_signup BETWEEN 22 AND 28
        ) AS retained_week_4

    FROM cohort_activity
    GROUP BY DATE_TRUNC('week', cohort_date)
)

SELECT
    cohort_week,
    cohort_size,

    -- Absolute retention counts
    retained_day_1,
    retained_day_3,
    retained_day_7,
    retained_day_14,
    retained_day_30,

    -- Retention rates (percentage)
    CASE WHEN cohort_size > 0 THEN ROUND(retained_day_1::NUMERIC / cohort_size * 100, 2) ELSE 0 END   AS retention_rate_day_1,
    CASE WHEN cohort_size > 0 THEN ROUND(retained_day_3::NUMERIC / cohort_size * 100, 2) ELSE 0 END   AS retention_rate_day_3,
    CASE WHEN cohort_size > 0 THEN ROUND(retained_day_7::NUMERIC / cohort_size * 100, 2) ELSE 0 END   AS retention_rate_day_7,
    CASE WHEN cohort_size > 0 THEN ROUND(retained_day_14::NUMERIC / cohort_size * 100, 2) ELSE 0 END  AS retention_rate_day_14,
    CASE WHEN cohort_size > 0 THEN ROUND(retained_day_30::NUMERIC / cohort_size * 100, 2) ELSE 0 END  AS retention_rate_day_30,

    -- Weekly band retention rates
    CASE WHEN cohort_size > 0 THEN ROUND(retained_week_1::NUMERIC / cohort_size * 100, 2) ELSE 0 END  AS retention_rate_week_1,
    CASE WHEN cohort_size > 0 THEN ROUND(retained_week_2::NUMERIC / cohort_size * 100, 2) ELSE 0 END  AS retention_rate_week_2,
    CASE WHEN cohort_size > 0 THEN ROUND(retained_week_3::NUMERIC / cohort_size * 100, 2) ELSE 0 END  AS retention_rate_week_3,
    CASE WHEN cohort_size > 0 THEN ROUND(retained_week_4::NUMERIC / cohort_size * 100, 2) ELSE 0 END  AS retention_rate_week_4

FROM weekly_cohorts
ORDER BY cohort_week
