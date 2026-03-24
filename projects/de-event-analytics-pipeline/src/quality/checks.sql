-- Checks should return 0 rows when OK.

-- 1) raw.events event_name not null
SELECT * FROM raw.events WHERE event_name IS NULL;

-- 2) purchases revenue not null
SELECT * FROM raw.events WHERE event_name='purchase' AND revenue IS NULL;

-- 3) referential integrity: stg.events user_id in stg.users (excluding null user_id)
SELECT e.*
FROM stg.events e
LEFT JOIN stg.users u ON u.user_id = e.user_id
WHERE e.user_id IS NOT NULL AND u.user_id IS NULL;
