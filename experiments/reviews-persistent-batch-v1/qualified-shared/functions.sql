CREATE FUNCTION fannagent.confirm_attach(regclass, regclass, integer) RETURNS integer
AS '$libdir/vector', 'fannbench_confirm_attach' LANGUAGE C STRICT VOLATILE PARALLEL UNSAFE;
