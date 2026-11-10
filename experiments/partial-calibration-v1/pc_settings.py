"""Explicit administrator/reader boundaries and numeric memory/build proof."""

import json

# Captured before_build torch_owner environment, independently verified failed raw.
ADMIN_ENVIRONMENT = {
    "default_transaction_read_only": "off",
    "jit": "on",
    "jit_above_cost": "100000",
    "jit_inline_above_cost": "500000",
    "jit_optimize_above_cost": "500000",
    "max_parallel_workers": "8",
    "max_parallel_workers_per_gather": "2",
    "max_worker_processes": "8",
    "min_parallel_index_scan_size": "64",
    "min_parallel_table_scan_size": "1024",
    "parallel_setup_cost": "1000",
    "parallel_tuple_cost": "0.1",
    "plan_cache_mode": "auto",
    "shared_buffers": "16384",
    "track_io_timing": "off",
    "work_mem": "4096",
}
READER_ENVIRONMENT = dict(
    plan_cache_mode="auto", jit="on", max_parallel_workers_per_gather="2", work_mem="16384"
)
ADMIN_MEMORY_BYTES = 4 * 1024**2
READER_MEMORY_BYTES = 16 * 1024**2
BUILD_SETTINGS = [64 * 1024**2, 0]
MEMORY_SQL = (
    "SELECT pg_size_bytes(current_setting('shared_buffers')),"
    "current_setting('max_connections')::int,"
    "pg_size_bytes(current_setting('work_mem')),"
    "current_setting('maintenance_work_mem'),"
    "current_setting('max_parallel_maintenance_workers')"
)
BUILD_SQL = (
    "SELECT pg_size_bytes(current_setting('maintenance_work_mem')),"
    "current_setting('max_parallel_maintenance_workers')::int"
)


def environment_for(user):
    if user == "torch_owner":
        return ADMIN_ENVIRONMENT
    if user == "torch_reader":
        return READER_ENVIRONMENT
    raise ValueError("Unknown catalog session role: " + str(user))


def validate_phase(user, phase):
    expected = (
        "torch_owner"
        if phase in {"before_build", "after_build", "final"}
        else "torch_reader"
        if phase in {"after_block_0", "after_block_1"}
        else None
    )
    if expected is None or user != expected:
        raise ValueError("Catalog phase/session role differs: " + str((phase, user)))


def validate_environment(env, user):
    expected = environment_for(user)
    differences = {
        k: dict(expected=v, actual=env.get(k))
        for k, v in expected.items()
        if type(env.get(k)) is not str or env[k] != v
    }
    if user == "torch_owner" and set(env) != set(expected):
        differences["field_names"] = dict(expected=sorted(expected), actual=sorted(env))
    if differences:
        raise ValueError(
            "Session environment differs for "
            + user
            + ": "
            + json.dumps(differences, sort_keys=True)
        )


def memory_record(mode, row):
    if (
        mode not in {"native640", "partial640"}
        or len(row) != 5
        or any(type(row[n]) is not int for n in [0, 1, 2])
        or row[:3] != (128 * 1024**2, 16, ADMIN_MEMORY_BYTES)
    ):
        raise ValueError("Private server/admin memory settings differ")
    return dict(
        copy=mode,
        shared_buffers_bytes=row[0],
        max_connections=row[1],
        admin_work_mem_bytes=row[2],
        reader_work_mem_bytes=READER_MEMORY_BYTES,
        work_mem_bound_bytes=max(row[2], READER_MEMORY_BYTES),
        maintenance_work_mem=row[3],
        parallel_maintenance_workers=row[4],
    )


def memory_proof(servers):
    if len(servers) != 2 or {r["copy"] for r in servers} != {"native640", "partial640"}:
        raise ValueError("Two distinct server memory records required")
    for r in servers:
        expected = memory_record(
            r["copy"],
            (
                r["shared_buffers_bytes"],
                r["max_connections"],
                r["admin_work_mem_bytes"],
                r["maintenance_work_mem"],
                r["parallel_maintenance_workers"],
            ),
        )
        if r != expected:
            raise ValueError("Memory proof scope/arithmetic differs")
    bound = (
        sum(
            r["shared_buffers_bytes"] + r["max_connections"] * 4 * r["work_mem_bound_bytes"]
            for r in servers
        )
        + 12 * 1024**3
    )
    if bound > 32 * 1024**3:
        raise ValueError("Two-copy memory bound exceeds allocation")
    return dict(servers=servers, conservative_bound_bytes=bound, measured_peak=False)


def inspect_memory(admins):
    from pc_trace import category

    records = []
    for mode, conn in admins.items():
        with category("observer"):
            row = conn.execute(MEMORY_SQL, prepare=False).fetchone()
        records.append(memory_record(mode, row))
    return memory_proof(records)
