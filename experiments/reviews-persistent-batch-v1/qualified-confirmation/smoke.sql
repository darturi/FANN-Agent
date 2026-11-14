-- Run after qualified-shadow/smoke.sql on the same fixture connection.
WITH traced AS (
    SELECT nullif(event, '')::jsonb AS e
    FROM regexp_split_to_table(:'shadow_trace', E'\n') AS event
), observations AS (
    SELECT (o->>'checkpoint')::int AS cp, (o->>'tenth_distance')::float8 AS tenth
    FROM jsonb_array_elements(:'observation'::jsonb) AS o
), features AS (
    SELECT o.*, (e->'features'->>'frontier_distance_min')::float8 - tenth AS gap
    FROM observations AS o
    JOIN traced AS t ON (e->>'index')::int = cp AND e->>'type' = 'checkpoint'
)
SELECT coalesce(min(cp) FILTER (WHERE cp = 32 AND gap >= 0.05), 0) AS expected_baseline,
       coalesce(min(cp) FILTER (WHERE
          (cp = 16 AND gap >= 0.02 AND tenth <= 0.44) OR
          (cp = 32 AND gap >= 0.025 AND tenth <= 0.38) OR
          (cp = 64 AND gap >= 0.05)), 0) AS expected_candidate
FROM features \gset
\echo EXPECTED_LIVE_STOPS :expected_baseline :expected_candidate

BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL enable_seqscan = off;
SET LOCAL hnsw.ef_search = 1000;
SELECT fannagent.confirm_bind('reviews','reviews_fixture_graph',1);
SELECT count(*) FROM (
    SELECT embedding <=> '[0.3,0.1,0.8,0.4,0.9,0.2,0.6,0.5]' AS distance
    FROM reviews WHERE id <= 16000 AND total_votes >= 108 ORDER BY distance LIMIT 10
) AS q;
SELECT fannagent.confirm_last() = :'expected_baseline'::int AS ok \gset
\if :ok
\else
SELECT 1/0;
\endif
COMMIT;

BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL enable_seqscan = off;
SET LOCAL hnsw.ef_search = 1000;
SELECT fannagent.confirm_bind('reviews','reviews_fixture_graph',2);
SELECT count(*) FROM (
    SELECT embedding <=> '[0.3,0.1,0.8,0.4,0.9,0.2,0.6,0.5]' AS distance
    FROM reviews WHERE id <= 16000 AND total_votes >= 108 ORDER BY distance LIMIT 10
) AS q;
SELECT fannagent.confirm_last() = :'expected_candidate'::int AS ok \gset
\if :ok
\echo LIVE_CONFIRMATION_DECISIONS_MATCH_SHADOW
\else
SELECT 1/0;
\endif
COMMIT;
