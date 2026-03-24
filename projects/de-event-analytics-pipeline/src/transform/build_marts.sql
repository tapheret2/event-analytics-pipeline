-- Staging
DROP TABLE IF EXISTS stg.events;
CREATE TABLE stg.events AS
SELECT
  event_time,
  user_id,
  event_name,
  country,
  device,
  revenue
FROM raw.events;

DROP TABLE IF EXISTS stg.users;
CREATE TABLE stg.users AS
SELECT
  user_id,
  MAX(country) AS country
FROM stg.events
WHERE user_id IS NOT NULL
GROUP BY user_id;

-- Fact purchases
DROP TABLE IF EXISTS marts.fact_purchases;
CREATE TABLE marts.fact_purchases AS
SELECT
  event_time,
  user_id,
  country,
  device,
  revenue
FROM stg.events
WHERE event_name = 'purchase';

-- Daily KPIs
DROP TABLE IF EXISTS marts.daily_kpis;
CREATE TABLE marts.daily_kpis AS
SELECT
  DATE(event_time) AS d,
  COUNT(DISTINCT user_id) FILTER (WHERE user_id IS NOT NULL) AS dau,
  SUM(revenue) FILTER (WHERE revenue IS NOT NULL) AS revenue
FROM stg.events
GROUP BY DATE(event_time)
ORDER BY d;
