CREATE EXTENSION vector;
CREATE TABLE reviews(id bigint, total_votes bigint, embedding vector(8));
INSERT INTO reviews
SELECT i, CASE WHEN i <= 49498 THEN 108 ELSE 0 END,
       ARRAY[sin(i::float8),cos(i::float8 / 3),sin(i::float8 / 7),cos(i::float8 / 19),sin(i::float8 / 11),cos(i::float8 / 17),sin(i::float8 / 23),cos(i::float8 / 29)]::vector
FROM generate_series(1,247286) AS i;
CREATE INDEX reviews_fixture_graph ON reviews USING hnsw(embedding vector_cosine_ops) WITH (m=32) WHERE id <= 16000;
CREATE SCHEMA fannagent;
CREATE FUNCTION fannagent.bind_target(regclass,text,text,regclass) RETURNS oid
AS '$libdir/vector', 'fannagent_bind_target' LANGUAGE C STRICT VOLATILE;
CREATE FUNCTION fannagent.shadow_bind(regclass) RETURNS integer
AS '$libdir/vector', 'fannbench_shadow_bind' LANGUAGE C STRICT VOLATILE;
CREATE FUNCTION fannagent.shadow_read(text) RETURNS text
AS '$libdir/vector', 'fannbench_shadow_read' LANGUAGE C STRICT VOLATILE;
CREATE FUNCTION fannagent.begin_execution(text,text,bigint,text,integer,integer,text,bigint,text,text,text,boolean,bigint)
RETURNS text AS '$libdir/vector', 'fannbench_begin_execution' LANGUAGE C VOLATILE;
CREATE FUNCTION fannagent.complete(text,integer)
RETURNS text AS '$libdir/vector', 'fannbench_last_execution' LANGUAGE C VOLATILE;
-- Bind vector SQL and the observer to the same loaded module path.
CREATE FUNCTION fannagent.take_trace(text) RETURNS text
AS '$libdir/vector', 'fannagent_take_trace' LANGUAGE C STRICT VOLATILE;
SELECT fannagent.bind_target('reviews','id','embedding','reviews_fixture_graph');
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT fannagent.shadow_bind('reviews');
SET LOCAL enable_seqscan = off;
SET LOCAL hnsw.ef_search = 1000;
SELECT fannagent.begin_execution('policy_noop',NULL,NULL,'shadowfixture',10,1,'checkpoints',1048576,
'research','research','basic,distances,query_context,queue,work',false,108);
SELECT array_agg(id ORDER BY distance,id)::text AS shadow_ids FROM (
    SELECT id, embedding <=> '[0.3,0.1,0.8,0.4,0.9,0.2,0.6,0.5]' AS distance
    FROM reviews WHERE id <= 16000 AND total_votes >= 108 ORDER BY distance LIMIT 10
) q \gset
SELECT (fannagent.complete('shadowfixture',10)::jsonb)->>'checkpoint_count';
SELECT fannagent.shadow_read('shadowfixture')::jsonb AS observation \gset
SELECT :'observation' AS observations;
SELECT jsonb_array_length(:'observation'::jsonb) = 3
  AND (:'observation'::jsonb->0->>'checkpoint')::int = 16
  AND (:'observation'::jsonb->1->>'checkpoint')::int = 32
  AND (:'observation'::jsonb->2->>'checkpoint')::int = 64
  AND (:'observation'::jsonb->2->>'top10_new_since_previous')::int BETWEEN 0 AND 10
  AND (:'observation'::jsonb->0->>'qualifying_count')::int >= 10
  AND (:'observation'::jsonb->1->>'qualifying_count')::int >= 10 AS valid \gset
\if :valid
\echo NATIVE_SHADOW_FIXTURE_PASSED
\else
SELECT 1/0;
\endif
SELECT fannagent.take_trace('shadowfixture') AS shadow_trace \gset
SELECT
    max((e->>'target')::bigint) FILTER (WHERE e->>'index' = '16') AS budget16,
    max((e->>'target')::bigint) FILTER (WHERE e->>'index' = '32') AS budget32,
    max((e->>'target')::bigint) FILTER (WHERE e->>'index' = '64') AS budget64
FROM (
    SELECT nullif(event, '')::jsonb AS e
    FROM regexp_split_to_table(:'shadow_trace', E'\n') event
) events WHERE e->>'type' = 'checkpoint' \gset
COMMIT;
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL enable_seqscan = off;
SET LOCAL hnsw.ef_search = 1000;
SELECT array_agg(id ORDER BY distance,id)::text AS native_ids FROM (
    SELECT id, embedding <=> '[0.3,0.1,0.8,0.4,0.9,0.2,0.6,0.5]' AS distance
    FROM reviews WHERE id <= 16000 AND total_votes >= 108 ORDER BY distance LIMIT 10
) q \gset
SELECT :'shadow_ids' = :'native_ids' AS parity \gset
\if :parity
\else
SELECT 1/0;
\endif
SELECT fannagent.shadow_bind('reviews');
SELECT fannagent.begin_execution('fixed_budget',NULL,:'budget16','shadowforcedstop',10,1,
'checkpoints',1048576,'research','research','basic,distances,query_context,queue,work',false,108);
SELECT max(distance) AS forced_tenth FROM (
    SELECT embedding <=> '[0.3,0.1,0.8,0.4,0.9,0.2,0.6,0.5]' AS distance
    FROM reviews WHERE id <= 16000 AND total_votes >= 108 ORDER BY distance LIMIT 10
) q \gset
SELECT (fannagent.complete('shadowforcedstop',10)::jsonb)->>'checkpoint_count' AS stop_cp \gset
SELECT fannagent.take_trace('shadowforcedstop') AS forced_trace \gset
WITH expected AS (
    SELECT jsonb_agg(e->'features' ORDER BY (e->>'index')::int) AS prefix
    FROM (
        SELECT nullif(event, '')::jsonb AS e
        FROM regexp_split_to_table(:'shadow_trace', E'\n') event
    ) events WHERE e->>'type' = 'checkpoint' AND (e->>'index')::int <= 16
), actual AS (
    SELECT jsonb_agg(e->'features' ORDER BY (e->>'index')::int) AS prefix
    FROM (
        SELECT nullif(event, '')::jsonb AS e
        FROM regexp_split_to_table(:'forced_trace', E'\n') event
    ) events WHERE e->>'type' = 'checkpoint'
)
SELECT expected.prefix = actual.prefix AND :'stop_cp' = '16' AND
       abs(:'forced_tenth'::float8 - (:'observation'::jsonb->0->>'tenth_distance')::float8) < 1e-6
       AS same_tenth FROM expected, actual \gset
\if :same_tenth
\echo NATIVE_SHADOW_OUTPUT_AND_FORCED_STOP_CP16_PARITY_PASSED
\else
SELECT 1/0;
\endif
SELECT fannagent.begin_execution('fixed_budget',NULL,:'budget32','shadowforcedstop',10,1,
'checkpoints',1048576,'research','research','basic,distances,query_context,queue,work',false,108);
SELECT max(distance) AS forced_tenth FROM (
    SELECT embedding <=> '[0.3,0.1,0.8,0.4,0.9,0.2,0.6,0.5]' AS distance
    FROM reviews WHERE id <= 16000 AND total_votes >= 108 ORDER BY distance LIMIT 10
) q \gset
SELECT (fannagent.complete('shadowforcedstop',10)::jsonb)->>'checkpoint_count' AS stop_cp \gset
SELECT fannagent.take_trace('shadowforcedstop') AS forced_trace \gset
WITH expected AS (
    SELECT jsonb_agg(e->'features' ORDER BY (e->>'index')::int) AS prefix
    FROM (
        SELECT nullif(event, '')::jsonb AS e
        FROM regexp_split_to_table(:'shadow_trace', E'\n') event
    ) events WHERE e->>'type' = 'checkpoint' AND (e->>'index')::int <= 32
), actual AS (
    SELECT jsonb_agg(e->'features' ORDER BY (e->>'index')::int) AS prefix
    FROM (
        SELECT nullif(event, '')::jsonb AS e
        FROM regexp_split_to_table(:'forced_trace', E'\n') event
    ) events WHERE e->>'type' = 'checkpoint'
)
SELECT expected.prefix = actual.prefix AND :'stop_cp' = '32' AND
       abs(:'forced_tenth'::float8 - (:'observation'::jsonb->1->>'tenth_distance')::float8) < 1e-6
       AS same_tenth FROM expected, actual \gset
\if :same_tenth
\echo NATIVE_SHADOW_OUTPUT_AND_FORCED_STOP_CP32_PARITY_PASSED
\else
SELECT 1/0;
\endif
SELECT fannagent.begin_execution('fixed_budget',NULL,:'budget64','shadowforcedstop',10,1,
'checkpoints',1048576,'research','research','basic,distances,query_context,queue,work',false,108);
SELECT max(distance) AS forced_tenth FROM (
    SELECT embedding <=> '[0.3,0.1,0.8,0.4,0.9,0.2,0.6,0.5]' AS distance
    FROM reviews WHERE id <= 16000 AND total_votes >= 108 ORDER BY distance LIMIT 10
) q \gset
SELECT (fannagent.complete('shadowforcedstop',10)::jsonb)->>'checkpoint_count' AS stop_cp \gset
SELECT fannagent.take_trace('shadowforcedstop') AS forced_trace \gset
WITH expected AS (
    SELECT jsonb_agg(e->'features' ORDER BY (e->>'index')::int) AS prefix
    FROM (
        SELECT nullif(event, '')::jsonb AS e
        FROM regexp_split_to_table(:'shadow_trace', E'\n') event
    ) events WHERE e->>'type' = 'checkpoint' AND (e->>'index')::int <= 64
), actual AS (
    SELECT jsonb_agg(e->'features' ORDER BY (e->>'index')::int) AS prefix
    FROM (
        SELECT nullif(event, '')::jsonb AS e
        FROM regexp_split_to_table(:'forced_trace', E'\n') event
    ) events WHERE e->>'type' = 'checkpoint'
)
SELECT expected.prefix = actual.prefix AND :'stop_cp' = '64' AND
       abs(:'forced_tenth'::float8 - (:'observation'::jsonb->2->>'tenth_distance')::float8) < 1e-6
       AS same_tenth FROM expected, actual \gset
\if :same_tenth
\echo NATIVE_SHADOW_OUTPUT_AND_FORCED_STOP_CP64_PARITY_PASSED
\else
SELECT 1/0;
\endif
ROLLBACK;
