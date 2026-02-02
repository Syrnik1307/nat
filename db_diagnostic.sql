-- ==========================================
-- EMERGENCY DATABASE DIAGNOSTIC SCRIPT
-- Run as: sudo -u postgres psql -f /tmp/db_diagnostic.sql
-- ==========================================

\echo '=== 1. CONNECTION STATS ==='
SELECT 
    count(*) as active_connections,
    (SELECT setting::int FROM pg_settings WHERE name='max_connections') as max_conn,
    round(100.0 * count(*) / (SELECT setting::int FROM pg_settings WHERE name='max_connections'), 1) as pct_used
FROM pg_stat_activity;

\echo ''
\echo '=== 2. CONNECTIONS BY STATE ==='
SELECT state, count(*) 
FROM pg_stat_activity 
GROUP BY state 
ORDER BY count(*) DESC;

\echo ''
\echo '=== 3. IDLE IN TRANSACTION (DANGEROUS) ==='
SELECT pid, usename, state, query_start, now() - query_start as duration, 
       left(query, 80) as query_preview
FROM pg_stat_activity 
WHERE state = 'idle in transaction' 
  AND now() - query_start > interval '1 second'
ORDER BY duration DESC
LIMIT 10;

\echo ''
\echo '=== 4. LONG RUNNING QUERIES (>5 sec) ==='
SELECT pid, usename, state, now() - query_start as duration,
       left(query, 100) as query_preview
FROM pg_stat_activity 
WHERE state = 'active'
  AND now() - query_start > interval '5 seconds'
ORDER BY duration DESC
LIMIT 10;

\echo ''
\echo '=== 5. BLOCKING LOCKS ==='
SELECT 
    blocked.pid AS blocked_pid,
    blocked.usename AS blocked_user,
    blocking.pid AS blocking_pid,
    blocking.usename AS blocking_user,
    left(blocked.query, 60) AS blocked_query,
    left(blocking.query, 60) AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
LIMIT 10;

\echo ''
\echo '=== 6. CONNECTIONS BY CLIENT (IP) ==='
SELECT client_addr, count(*) as conn_count
FROM pg_stat_activity 
WHERE client_addr IS NOT NULL
GROUP BY client_addr
ORDER BY conn_count DESC
LIMIT 5;

\echo ''
\echo '=== 7. CONNECTIONS BY APPLICATION ==='
SELECT application_name, count(*) as conn_count
FROM pg_stat_activity 
GROUP BY application_name
ORDER BY conn_count DESC;
