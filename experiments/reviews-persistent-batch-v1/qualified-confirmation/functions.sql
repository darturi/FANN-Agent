CREATE FUNCTION fannagent.confirm_bind(regclass, regclass, integer) RETURNS integer
AS '$libdir/vector', 'fannbench_confirm_bind' LANGUAGE C STRICT VOLATILE PARALLEL UNSAFE;
CREATE FUNCTION fannagent.confirm_last() RETURNS integer
AS '$libdir/vector', 'fannbench_confirm_last' LANGUAGE C VOLATILE PARALLEL UNSAFE;
