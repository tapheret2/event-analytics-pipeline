-- =============================================================================
-- dbt Macros: Date Utilities
-- =============================================================================
-- Reusable SQL macros for common date operations across models.
-- =============================================================================

-- Get the start of the current week (Monday)
{% macro start_of_week(date_col) %}
    DATE_TRUNC('week', {{ date_col }})::DATE
{% endmacro %}

-- Get the start of the current month
{% macro start_of_month(date_col) %}
    DATE_TRUNC('month', {{ date_col }})::DATE
{% endmacro %}

-- Calculate the number of days between two dates
{% macro days_between(start_date, end_date) %}
    ({{ end_date }} - {{ start_date }})
{% endmacro %}

-- Determine if a date is a weekend
{% macro is_weekend(date_col) %}
    CASE
        WHEN EXTRACT(DOW FROM {{ date_col }}) IN (0, 6) THEN true
        ELSE false
    END
{% endmacro %}

-- Get a human-readable day name
{% macro day_name(date_col) %}
    TO_CHAR({{ date_col }}, 'Day')
{% endmacro %}

-- Safe division to prevent divide by zero
{% macro safe_divide(numerator, denominator, decimal_places=2) %}
    CASE
        WHEN {{ denominator }} > 0
        THEN ROUND({{ numerator }}::NUMERIC / {{ denominator }}, {{ decimal_places }})
        ELSE 0
    END
{% endmacro %}

-- Generate a date spine (useful for filling date gaps)
{% macro date_spine(start_date, end_date) %}
    SELECT generate_series(
        '{{ start_date }}'::DATE,
        '{{ end_date }}'::DATE,
        '1 day'::INTERVAL
    )::DATE AS date_day
{% endmacro %}
