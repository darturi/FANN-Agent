"""Synthetic native qualification, kept entirely outside the subsequent agent run."""

import argparse
import subprocess
from pathlib import Path

from .core import FILTERS, Limits, read, write
from .deploy import compile_request, package
from .engine import empty


def probes():
    policies = []
    settings = [
        (["ge", ["feature", "qualifying_count"], 1], {}, 0, 16000000),
        (["ge", ["state", 0], 1], {"0": ["add", ["state", 0], 1]}, 1, 16000000),
        (["gt", ["div", 1, 0], 0], {}, 0, 16000000),
        (["ge", ["feature", "qualifying_count"], 1], {}, 0, 1),
    ]
    for i, (root, updates, slots, fuel) in enumerate(settings):
        policies.append(
            {
                **empty(),
                "name": f"qualification-probe-{i}",
                "state_slots": slots,
                "fuel": fuel,
                "programs": {
                    "unfiltered" if t < 0 else f"votes{t}": {
                        "checkpoints": [1, 3, 9, 16],
                        "root": root,
                        "updates": updates,
                    }
                    for t in FILTERS
                },
            }
        )
    return policies


def setup(directory, engine, research_image, runtime_id):
    from psycopg import connect

    directory = Path(directory)
    pgdata, socket = directory / "snapshot", directory / "socket"
    socket.mkdir()
    subprocess.run(
        ["/opt/postgresql/bin/initdb", "-D", str(pgdata), "-A", "trust", "-U", "nobody"], check=True
    )
    ctl = ["/opt/postgresql/bin/pg_ctl", "-D", str(pgdata)]
    subprocess.run(
        ctl
        + [
            "-l",
            str(directory / "fixture-server.log"),
            "-o",
            f"-k {socket} -c listen_addresses='' -c max_parallel_workers_per_gather=0",
            "-w",
            "start",
        ],
        check=True,
    )
    try:
        with connect(f"host={socket} dbname=postgres user=nobody", autocommit=True) as c:
            c.execute("CREATE DATABASE torch_reviews")
        with connect(f"host={socket} dbname=torch_reviews user=nobody", autocommit=True) as c:
            c.execute("CREATE EXTENSION vector")
            c.execute("CREATE TABLE reviews(id bigint, total_votes bigint, embedding vector(8))")
            c.execute("""INSERT INTO reviews SELECT i,
                CASE WHEN i<=7 THEN 600 WHEN i<=200 THEN 400 WHEN i<=700 THEN 250
                WHEN i<=1500 THEN 150 WHEN i<=3000 THEN 50 ELSE 0 END,
                CASE WHEN i<=4096 THEN ARRAY[sin(i::float8),cos(i::float8/3),
                sin(i::float8/7),cos(i::float8/19),sin(i::float8/11),cos(i::float8/17),
                sin(i::float8/23),cos(i::float8/29)]::vector ELSE NULL END
                FROM generate_series(1,247286) i""")
            c.execute(
                "CREATE INDEX reviews_hnsw ON reviews USING hnsw(embedding vector_cosine_ops) "
                "WITH(m=16,ef_construction=64)"
            )
            c.execute("ANALYZE reviews")
    finally:
        subprocess.run(ctl + ["-m", "fast", "-w", "stop"], check=True)
    cases = [
        {
            "handle": f"synthetic-{g}-{t}",
            "group": f"synthetic-{g}",
            "role": "development",
            "filter": t,
            "vector": [0.3 + 0.03 * g, 0.1, 0.8, 0.4, 0.9, 0.2, 0.6, 0.5],
        }
        for g in range(2)
        for t in FILTERS
    ]
    marker = directory / "docker-runtime-id.txt"
    marker.write_text(runtime_id + "\n")
    stage = directory / "stage"
    package(
        stage,
        cases,
        engine,
        pgdata,
        marker,
        research_image,
        Limits(
            query_cap=10000,
            final_reserve=5000,
            wall_seconds=3600,
            discovery_seconds=1800,
            bootstrap_draws=256,
        ),
    )
    handles = [c["handle"] for c in read(stage / "private/cases.json")]
    from fannagent.api.broad_policy import FEATURES

    payloads = [
        {
            "kind": "profile",
            "handles": handles,
            "checkpoints": [1, 3, 9, 16],
            "features": list(FEATURES),
        },
        {"kind": "screen", "handles": handles, "policies": probes(), "blocks": 2},
    ]
    for i, payload in enumerate(payloads):
        target = stage / "private/builds" / f"{i + 1:032x}"
        write(target / "payload.json", payload)
        compile_request(stage, target, payload)
    write(
        directory / "setup.json",
        {
            "status": "compiled",
            "synthetic_only": True,
            "source_runtime_id": runtime_id,
            "requests": len(payloads),
        },
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--research-image", required=True)
    p.add_argument("--runtime-id", required=True)
    a = p.parse_args()
    setup(a.directory, a.engine, a.research_image, a.runtime_id)


if __name__ == "__main__":
    main()
