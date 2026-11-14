CREATE FUNCTION fannagent.shadow_bind(regclass) RETURNS integer
AS '$libdir/vector', 'fannbench_shadow_bind' LANGUAGE C STRICT VOLATILE PARALLEL UNSAFE;

CREATE FUNCTION fannagent.shadow_read(text) RETURNS text
AS '$libdir/vector', 'fannbench_shadow_read' LANGUAGE C STRICT VOLATILE PARALLEL UNSAFE;

REVOKE ALL ON FUNCTION fannagent.shadow_bind(regclass), fannagent.shadow_read(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION fannagent.shadow_bind(regclass), fannagent.shadow_read(text) TO torch_reader;
