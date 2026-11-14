CREATE FUNCTION fannagent.study_attach(regclass,regclass,integer,integer,integer) RETURNS integer
AS '$libdir/vector','fannbench_confirm_attach' LANGUAGE C STRICT VOLATILE PARALLEL UNSAFE;
CREATE FUNCTION fannagent.study_local_bind(regclass,integer,integer) RETURNS integer
AS '$libdir/vector','fannbench_shadow_bind' LANGUAGE C STRICT VOLATILE PARALLEL UNSAFE;
CREATE FUNCTION fannagent.shadow_read(text) RETURNS text
AS '$libdir/vector','fannbench_shadow_read' LANGUAGE C STRICT VOLATILE PARALLEL UNSAFE;
CREATE FUNCTION fannagent.confirm_last() RETURNS integer
AS '$libdir/vector','fannbench_confirm_last' LANGUAGE C VOLATILE PARALLEL UNSAFE;

CREATE FUNCTION fannagent.diagnostic_reset() RETURNS void AS '$libdir/vector','fannbench_diagnostic_reset' LANGUAGE C VOLATILE PARALLEL UNSAFE;
CREATE FUNCTION fannagent.diagnostic_read() RETURNS text AS '$libdir/vector','fannbench_diagnostic_read' LANGUAGE C VOLATILE PARALLEL UNSAFE;
