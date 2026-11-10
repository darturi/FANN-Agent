"""Read only the pinned Reviews development inputs and reconstruct the frozen schedule."""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The sealed guest is mounted directly at /patch and keeps its inputs beside the code.
ROOT = HERE / "inputs" if (HERE / "inputs").is_dir() else HERE.parent.parent.parent
RESEARCH = "research/fannagent-controlled-reviews-batch-"
PILOT = Path("trials/torch-reviews-selective-agent-v1/runs/20261022T192817Z-66ed81d6")
PACKAGE = PILOT / "packages/pilot/torch-selective-agent-v1-pilot-20261022T192817Z-66ed81d6"
PILOT_BLOCK = PILOT / (
    "returned/pilot/reviews-selective-agent-v1-pilot-20261022T202240Z.j9ackcxc/blocks/block-0"
)
PINS = {
    f"{RESEARCH}study-design-2026-11-08.md": (
        "e7a4e1ebbc4c42ce3ce5df83ee52876dff5af78fe65f1edb8d3733560eecc1f8"
    ),
    f"{RESEARCH}manifest-2026-11-08.json": (
        "cd3b4d1344f7e15ec67c771cce8c427e1e96165db043c7397324d7e45ae68d63"
    ),
    f"{RESEARCH}workload-2026-11-08.md": (
        "a6f82a950a3b2dd108e59eccad1e7c24c9da403f4dcb2e1d188bbfd91512ca53"
    ),
}
PILOT_MANIFEST = "082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc"
SEED_ID = "a014a290966444a86614f1e5be1960dad2fb8684044e85e9df82899911062b0d"
PROFILES = ("light19", "static23", "progress34")
FILTERS = ("unfiltered", "votes32", "votes108")
CHECKPOINTS = (1, 2, 4, 8, 16, 32, 64, 128)
FAMILIES = ("native", "seed", "candidate")
ARMS = tuple(f"{family}-{label}" for family in FAMILIES for label in "AB")
WILLIAMS_ROW = (0, 1, 5, 2, 4, 3)
QUERY_COUNT = 600
SESSION_COUNT = 60
SESSION_LENGTH = 10
TIMING_EPOCHS = 2
SEED = 20261019
DRAWS = 10_000

SEARCHES = {
    "getter": 921,
    "exact": QUERY_COUNT,
    "native": QUERY_COUNT,
    "continue": QUERY_COUNT * len(PROFILES),
    "proof": QUERY_COUNT * 2,
    "timing": QUERY_COUNT * len(ARMS) * TIMING_EPOCHS,
}
INSTALLATIONS = {"getter": 921, "continue": 1800, "proof": 120, "timing": 480}
READER_OPENS = {"reference": 1, "proof": 120, "timing": 720}
PHASE_SECONDS = {"restore": 1500, "quality": 2700, "timing": 1800, "final": 600}
PHASE_SEARCHES = {
    "quality": ("getter", "exact", "native", "continue", "proof"),
    "timing": ("timing",),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def file_sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def pinned(path, expected):
    require(path.is_file() and not path.is_symlink(), f"Expected regular input: {path}")
    data = path.read_bytes()
    require(sha(data) == expected, f"Input digest changed: {path}")
    return data


def pinned_lines(path, expected):
    """Consume the complete iterator before treating its data as trusted."""
    require(path.is_file() and not path.is_symlink(), f"Expected regular input: {path}")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for line in handle:
            h.update(line)
            yield json.loads(line)
    require(h.hexdigest() == expected, f"Input digest changed: {path}")


def filter_of(query):
    predicate = query["filter"]
    if predicate is None:
        return "unfiltered"
    require(
        type(predicate) is dict
        and set(predicate) == {"field", "op", "value"}
        and predicate["field"] == "m_000000"
        and predicate["op"] == "gte"
        and type(predicate["value"]) is int
        and predicate["value"] in (32, 108),
        "Unexpected Reviews predicate",
    )
    return f"votes{predicate['value']}"


@dataclass(frozen=True)
class Case:
    query: dict
    group: str
    stratum: str

    @property
    def id(self):
        return self.query["id"]


@dataclass(frozen=True)
class Session:
    id: str
    block: int
    rotation: int
    cases: tuple[Case, ...]


@dataclass(frozen=True)
class Plan:
    sessions: tuple[Session, ...]
    seed: dict
    config: dict
    qualification: tuple[dict, ...]

    @property
    def cases(self):
        return {case.id: case for session in self.sessions for case in session.cases}

    def timed(self):
        for epoch in range(TIMING_EPOCHS):
            for session in self.sessions if epoch == 0 else reversed(self.sessions):
                shift = session.block + 2 * session.rotation
                order = [ARMS[(label + shift) % len(ARMS)] for label in WILLIAMS_ROW]
                for arm in order if epoch == 0 else reversed(order):
                    yield epoch, session, arm


def load_plan(root=ROOT):
    root = Path(root)
    pinned_inputs = {name: pinned(root / name, expected) for name, expected in PINS.items()}
    manifest = json.loads(pinned_inputs[f"{RESEARCH}manifest-2026-11-08.json"])
    package = root / PACKAGE
    pins = json.loads(pinned(package / "manifest.json", PILOT_MANIFEST))["files"]
    source = manifest["source"]
    require(
        source["package"] == str(PACKAGE)
        and source["manifest_sha256"] == PILOT_MANIFEST
        and source["queries_path"] == "inputs/queries.jsonl"
        and source["queries_sha256"] == pins["inputs/queries.jsonl"],
        "Development source binding changed",
    )
    cases = {}
    for row in pinned_lines(package / "inputs/queries.jsonl", source["queries_sha256"]):
        query = row["query"]
        case = Case(query, row["group"], filter_of(query))
        require(
            type(query["k"]) is int and query["k"] == 10 and case.id not in cases,
            "Unexpected or duplicate development query",
        )
        cases[case.id] = case

    sessions = []
    ids = set()
    vector_hashes = set()
    for b, block in enumerate(manifest["blocks"]):
        groups = {x["group_id"]: x["vector_sha256"] for x in block["vector_groups"]}
        require(len(groups) == 10 and len(set(groups.values())) == 10, "Duplicate block vector")
        require(not vector_hashes.intersection(groups.values()), "Vector crossed timing blocks")
        vector_hashes.update(groups.values())
        require(len(block["sessions"]) == 3, "Wrong session count in block")
        for r, record in enumerate(block["sessions"]):
            require(record["rotation"] == r, "Unexpected rotation")
            requests = []
            for i, request in enumerate(record["requests"]):
                case = cases[request["query_id"]]
                payload = {k: v for k, v in case.query.items() if k != "id"}
                vector = case.query["vector"]
                require(
                    request["position"] == i + 1
                    and request["vector_group"] == case.group
                    and request["filter_stratum"] == case.stratum == FILTERS[(i + r) % 3]
                    and request["request_sha256"] == digest(payload)
                    and len(vector) == 768
                    and groups[case.group] == sha(struct.pack("<768f", *vector))
                    and case.id not in ids,
                    f"Manifest request changed: {case.id}",
                )
                ids.add(case.id)
                requests.append(case)
            require(tuple(c.group for c in requests) == tuple(groups), "Batch vector order changed")
            sessions.append(Session(record["session_id"], b, r, tuple(requests)))
    require(
        len(sessions) == len({s.id for s in sessions}) == SESSION_COUNT
        and len(cases) == QUERY_COUNT
        and ids == set(cases)
        and len(vector_hashes) == 200,
        "Development session coverage changed",
    )
    candidates = json.loads(pinned(package / "candidates.json", pins["candidates.json"]))
    config = json.loads(pinned(package / "experiment.json", pins["experiment.json"]))
    qualification = tuple(
        pinned_lines(package / "inputs/qualification.jsonl", pins["inputs/qualification.jsonl"])
    )
    require(
        tuple(filter_of(row["query"]) for row in qualification) == FILTERS
        and all(row["query"] == cases[row["query"]["id"]].query for row in qualification),
        "Getter fixtures differ from sealed development inputs",
    )
    return Plan(tuple(sessions), candidates[SEED_ID]["policy"], config, qualification)
