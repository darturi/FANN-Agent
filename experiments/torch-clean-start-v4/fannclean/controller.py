"""Opus research tools: collect first, fit from own observations, confirm, then freeze."""

import re
import subprocess
import uuid
from pathlib import Path

from fannagent.api.broad_policy import validate

from .core import FILTERS, Limits, append_evidence, digest, read, write
from .search import stopping_review, structure

SYSTEM = """Discover a deployable broad-stop.v3 ANN stopping policy from a CLEAN START.
You initially have only static task/query handles and generic software. No prior-run
observations, labels, native work/latency summaries, fitted policies, thresholds,
agent conversations, scratch files or oracle artifacts are available. Acquire your
own evidence with acquire/profile_features; every native/exact operation is charged.
Only development queries may be used during discovery. Truth is private scoring only.
Never present unexecuted prefix labels as observations, interpolate labels, or
assume recall is monotone. Learned rules may generalize; keep their measured
validation scope explicit and treat unmeasured predictions as hypotheses.

Control the research strategy. Begin with a search plan: acquisition questions,
alternative hypothesis families, validation, feature cost, and allocation of budget.
Use representative groups across ALL seven conditions; select checkpoint schedules
from evidence rather than a fixed legacy grid. Update the plan after feedback.
Generic fit_policy supports threshold, linear and nonlinear interval/tree programs,
with grouped cross-validation. You may also implement other methods using offline
NumPy/Python. These helpers contain no benchmark-trained models or parameters.
Investigate cheap features and collector overhead measured in this run. Fit quality,
stop coverage and saved work are diagnostics; complete measured request latency is
the optimization target. Avoid a portfolio of only tiny threshold variants.

The deployment language has all 13 causal features, arithmetic/Boolean expressions,
checkpoints 1..4096, 32 query-local registers, 8MiB source, 131072 nodes, depth64,
4MiB tables, 16M query fuel. No IDs, labels, future features, I/O or index mutations
at runtime. Fault/fuel exhaustion continues native. Previous-frame features depend
on the preceding DECLARED checkpoint; never mix observations from other schedules.

Exploratory quality failures return per-case counterexamples and do not suppress
other candidates' feedback. Timings use independently randomized same-reader blocks
with adjacent randomized native pairs, matched continuation, clone and empty
controls. Failed controls mean INCONCLUSIVE, not a winning point estimate.
Request another predeclared block
batch or refine the strategy when justified by the remaining resources.

Before a policy can be frozen, confirm it on ALL development cases for zero native
recall AND count losses, with controlled timing showing improvement against native
and matched continuation. Normal finish requires multiple evaluation rounds and
distinct program structures plus a substantive stopping report. Use available budget
when a promising alternative remains; there is no fixed total candidate quota.
Resource exhaustion may end search incomplete or with abstention, never with an
invented qualified win. Inspect remaining query, dollar and time budgets regularly.
The frozen policy is evaluated once on protected cohorts; no final feedback is
returned to you. Never request or use a hindsight oracle during discovery.
"""


def spec(name, description, properties, required):
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


STR = {"type": "string"}
STRS = {"type": "array", "items": STR}
REPORT_KEYS = (
    "alternatives_considered",
    "acquisition_coverage",
    "cost_evidence",
    "why_more_search_not_worth_cost",
    "reason",
)
TOOLS = [
    spec("inspect_state", "Budgets, progress, hypotheses and candidate status.", {}, []),
    spec(
        "list_queries",
        "Static development handles only; no empirical information.",
        {"offset": {"type": "integer"}, "limit": {"type": "integer"}},
        [],
    ),
    spec(
        "plan_search",
        "Register or revise acquisition, hypotheses, validation and budget plans.",
        {"plan": STR},
        ["plan"],
    ),
    *[
        spec(
            name,
            description,
            {
                "handles": STRS,
                "checkpoints": {"type": "array", "items": {"type": "integer"}},
                "features": STRS,
            },
            ["handles", "checkpoints", "features"],
        )
        for name, description in [
            ("acquire", "Execute requested development observations and prefix labels."),
            (
                "profile_features",
                "Acquire evidence and measure the requested collector cost with controls.",
            ),
        ]
    ],
    spec(
        "fit_policy",
        "Fit a generic model using ONLY same-run observations; save a normal v3 artifact.",
        {
            "method": {"type": "string", "enum": ["threshold", "linear", "tree"]},
            "features": STRS,
            "checkpoints": {"type": "array", "items": {"type": "integer"}},
            "name": STR,
            "depth": {"type": "integer"},
            "min_leaf": {"type": "integer"},
            "costs": {"type": "object", "additionalProperties": {"type": "number"}},
        },
        ["method", "features", "checkpoints", "name"],
    ),
    spec(
        "research_python",
        "Offline NumPy/Python, 240 seconds, 2GiB; evidence/task/API read-only.",
        {"code": STR},
        ["code"],
    ),
    spec(
        "evaluate",
        "Exploratory per-case quality plus controlled timing; no all-or-nothing quality gate.",
        {"policy_paths": STRS, "handles": STRS, "blocks": {"type": "integer"}},
        ["policy_paths", "handles"],
    ),
    spec(
        "confirm",
        "Full development quality and larger independent timing order/panel.",
        {"candidate_id": STR, "blocks": {"type": "integer"}},
        ["candidate_id"],
    ),
    spec(
        "finish",
        "Freeze a confirmed winner, or abstain with an evidence-based stopping report.",
        {
            "candidate_id": {"type": ["string", "null"]},
            "report": {
                "type": "object",
                "properties": {k: STR for k in REPORT_KEYS},
                "required": list(REPORT_KEYS),
                "additionalProperties": False,
            },
        },
        ["candidate_id", "report"],
    ),
]


def check_arguments(schema, value):
    kinds = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": (int, float),
        "null": type(None),
    }
    declared = schema.get("type")
    declared = declared if isinstance(declared, list) else [declared]
    if declared != [None] and not any(
        type(value) in (kinds[t] if isinstance(kinds[t], tuple) else (kinds[t],)) for t in declared
    ):
        raise ValueError("tool argument has the wrong type")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("unsupported tool argument")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if not set(schema.get("required", ())) <= set(value):
            raise ValueError("missing tool arguments")
        if schema.get("additionalProperties") is False and not set(value) <= set(properties):
            raise ValueError("unexpected tool arguments")
        for k, v in value.items():
            check_arguments(properties.get(k, schema.get("additionalProperties", {})), v)
    if isinstance(value, list):
        for v in value:
            check_arguments(schema["items"], v)


class Workspace:
    def __init__(self, root, image, limits):
        self.root, self.image, self.limits = Path(root).resolve(), image, limits
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
            raise ValueError("research image must be pinned by digest")

    def execute(self, code, timeout=None):
        if not isinstance(code, str) or not 1 <= len(code.encode()) <= 65536:
            raise ValueError("bounded Python source required")
        identity = uuid.uuid4().hex
        directory = self.root.parent / "host/research" / identity
        directory.mkdir(parents=True)
        (directory / "source.py").write_text(code)
        args = [
            "docker",
            "run",
            "--pull=never",
            "--interactive",
            "--rm",
            "--cidfile",
            str(directory / "cid"),
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "128",
            "--memory",
            str(self.limits.research_memory_mib) + "m",
            "--cpus",
            "1",
            "--user",
            f"{__import__('os').getuid()}:{__import__('os').getgid()}",
            "--tmpfs",
            "/tmp:rw,nosuid,size=256m",
            "--workdir",
            "/workspace",
            "--mount",
            f"type=bind,src={self.root},dst=/workspace",
        ]
        for name in ("api", "evidence", "task.json"):
            args += ["--mount", f"type=bind,src={self.root / name},dst=/workspace/{name},readonly"]
        args += [
            "--env",
            "PYTHONPATH=/workspace/api",
            "--env",
            "OPENBLAS_NUM_THREADS=1",
            "--env",
            "OMP_NUM_THREADS=1",
            "--entrypoint",
            "python",
            self.image,
            "-B",
            "-",
        ]
        try:
            result = subprocess.run(
                args,
                input=code,
                text=True,
                capture_output=True,
                timeout=min(self.limits.research_seconds, timeout or self.limits.research_seconds),
            )
            answer = {
                "exit_code": result.returncode,
                "output": (result.stdout + result.stderr)[-16000:],
            }
        except subprocess.TimeoutExpired:
            if (directory / "cid").exists():
                subprocess.run(
                    ["docker", "rm", "-f", (directory / "cid").read_text().strip()],
                    capture_output=True,
                    timeout=30,
                )
            answer = {
                "exit_code": "timeout",
                "output": "Research timeout; completed files remain. No native action dispatched.",
            }
        write(directory / "receipt.json", answer)
        return answer

    def policy(self, name):
        path = (self.root / name).resolve(strict=True)
        if not path.is_relative_to(self.root / "policies") or path.stat().st_size > 8 * 1024**2:
            raise ValueError("bounded policy file must be under policies/")
        return validate(read(path))


class Controller:
    def __init__(self, root, client, budget_status=lambda: {}):
        self.root, self.client = Path(root), client
        self.budget_status = budget_status
        config = read(self.root / "config.json")
        self.run_id, self.limits = config["run_id"], Limits(**config["limits"])
        self.path = self.root / "host/search.json"
        if self.path.exists():
            raise ValueError("fresh controller required; no imported conversations or search state")
        self.state = {
            "run_id": self.run_id,
            "plans": [],
            "rounds": [],
            "candidates": {},
            "receipts": {},
            "terminal": None,
            "observed_filters": [],
        }
        self.workspace = Workspace(
            self.root / "agent", read(self.root / "deployment.json")["research_image"], self.limits
        )
        write(self.path, self.state)

    def call(self, identity, name, args):
        signature = digest([name, args])
        if identity in self.state["receipts"]:
            prior = self.state["receipts"][identity]
            if prior["signature"] != signature or prior["status"] != "complete":
                raise ValueError("unknown/conflicting tool delivery; never redispatch")
            return prior["answer"]
        if self.state["terminal"]:
            raise ValueError("discovery already ended")
        self.state["receipts"][identity] = {"signature": signature, "status": "open"}
        write(self.path, self.state)
        try:
            tool = next((t for t in TOOLS if t["name"] == name), None)
            if tool is None:
                raise ValueError("unknown tool")
            check_arguments(tool["input_schema"], args)
            answer = self._call(name, args)
        except (ValueError, KeyError, FileNotFoundError) as error:
            answer = {"error": str(error)}
        self.state["receipts"][identity].update(status="complete", answer=answer)
        write(self.path, self.state)
        return answer

    def remote(self, payload):
        result = self.client.action(payload)
        if (
            result.get("status") == "rejected"
            and result.get("run_id") == self.run_id
            and result.get("payload_sha256") == digest(payload)
        ):
            raise ValueError("Native admission rejected before execution: " + result["error"])
        if (
            result.get("run_id") != self.run_id
            or result.get("payload_sha256") != digest(payload)
            or result.get("status") != "complete"
        ):
            raise RuntimeError("native result failed binding/settlement; stop without retry")
        append_evidence(self.root / "agent", self.run_id, result)
        self.state["observed_filters"] = sorted(
            set(self.state["observed_filters"])
            | {r["filter"] for key in ("evidence", "quality") for r in result.get(key, [])}
        )
        directory = self.root / "agent/evidence" / result["request_id"]
        for key in ("quality", "samples"):
            rows = result.get(key, [])
            write(
                directory / (key + ".json"),
                {"run_id": self.run_id, "request_id": result["request_id"], "records": rows},
            )
        return result

    def feedback(self, result):
        rows = result["quality"]
        failures = [
            r
            for r in rows
            if r["recall"] + 1e-12 < r["native_recall"]
            or r["count"] < r["native_count"]
            or r["fault"]
            or r["exhausted"]
        ]
        return {
            "quality_cases": len(rows),
            "quality_failure_cases": len(failures),
            "counterexamples": failures[:8],
            "timing": result["timing"],
            "complete_feedback_directory": "evidence/" + result["request_id"],
            "full_quality": result["full_quality"],
            "budgets": self.budget_status(),
        }

    def _call(self, name, args):
        if name == "inspect_state":
            return {
                "worker": self.client.status(),
                "model": self.budget_status(),
                "observed_conditions": self.state["observed_filters"],
                "unobserved_conditions": sorted(set(FILTERS) - set(self.state["observed_filters"])),
                "plans": self.state["plans"],
                "rounds": self.state["rounds"],
                "candidates": {
                    k: {x: v[x] for x in ("hash", "structure", "screened")}
                    for k, v in self.state["candidates"].items()
                },
            }
        if name == "list_queries":
            queries = read(self.root / "agent/task.json")["queries"]
            offset, limit = args.get("offset", 0), args.get("limit", 64)
            if (
                type(offset) is not int
                or type(limit) is not int
                or offset < 0
                or not 1 <= limit <= 256
            ):
                raise ValueError("invalid static handle page")
            return {"queries": queries[offset : offset + limit], "total": len(queries)}
        if name == "plan_search":
            if not isinstance(args["plan"], str) or len(args["plan"].strip()) < 80:
                raise ValueError(
                    "describe acquisition, distinct hypotheses, validation, cost and budget"
                )
            self.state["plans"].append(args["plan"])
            return {"registered": True}
        if not self.state["plans"]:
            raise ValueError("register an acquisition/search plan first")
        resources = self.client.status()
        if name != "finish" and (
            resources.get("status") != "running" or resources["discovery_seconds_remaining"] <= 60
        ):
            raise ValueError("discovery clock closed; no more research/evidence actions")
        if name in ("acquire", "profile_features"):
            result = self.remote({"kind": "acquire" if name == "acquire" else "profile", **args})
            return {
                "records_added": len(result["evidence"]),
                "evidence_file": "evidence/observations.jsonl",
                "timing": result["timing"],
                "budgets": result["ledger"],
                "acquisition_diagnostics": result["acquisition_diagnostics"],
            }
        if name == "research_python":
            return self.workspace.execute(
                args["code"], resources["discovery_seconds_remaining"] - 60
            )
        if name == "fit_policy":
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args["name"]):
                raise ValueError("simple artifact name required")
            path = "policies/" + args["name"] + ".json"
            metadata = "scratch/fit-" + uuid.uuid4().hex + ".json"
            settings = {"run_id": self.run_id, **{k: v for k, v in args.items() if k != "name"}}
            source = f"""import json
from pathlib import Path
from fit import fit
records = [json.loads(line) for line in Path("evidence/observations.jsonl").open()]
answer = fit(records, **{settings!r})
Path({path!r}).write_text(json.dumps(answer.pop("policy"), allow_nan=False))
Path({metadata!r}).write_text(json.dumps(answer, allow_nan=False))
"""
            receipt = self.workspace.execute(source, resources["discovery_seconds_remaining"] - 60)
            if receipt["exit_code"] != 0:
                return {"fit_failed": True, **receipt}
            self.workspace.policy(path)
            answer = read(self.root / "agent" / metadata)
            return {
                "policy_path": path,
                "validation": answer["validation"],
                "excluded_incompatible_schedule_records": answer.get(
                    "excluded_incompatible_schedule_records", 0
                ),
                "native_validation_required": True,
            }
        if name == "evaluate":
            paths = args["policy_paths"]
            if not 1 <= len(paths) <= 4:
                raise ValueError("one to four candidates per exploratory batch")
            policies = [self.workspace.policy(p) for p in paths]
            result = self.remote(
                {
                    "kind": "screen",
                    "policies": policies,
                    "handles": args["handles"],
                    "blocks": args.get("blocks", 2),
                }
            )
            ids = []
            for i, policy in enumerate(policies):
                cid = "c" + str(len(self.state["candidates"]) + 1)
                self.state["candidates"][cid] = {
                    "policy": policy,
                    "hash": digest(policy),
                    "structure": structure(policy),
                    "screened": True,
                    "screen_result": result,
                }
                ids.append(cid)
            self.state["rounds"].append(
                {"status": "complete", "request_id": result["request_id"], "candidate_ids": ids}
            )
            return {
                "candidate_ids": ids,
                **self.feedback(result),
                "evidence_file": "evidence/observations.jsonl",
            }
        if name == "confirm":
            candidate = self.state["candidates"][args["candidate_id"]]
            result = self.remote(
                {
                    "kind": "confirm",
                    "policies": [candidate["policy"]],
                    "handles": [],
                    "blocks": args.get("blocks", 2),
                }
            )
            candidate["confirmation"] = result
            self.state["rounds"].append(
                {
                    "status": "complete",
                    "request_id": result["request_id"],
                    "confirmation": args["candidate_id"],
                }
            )
            return self.feedback(result)
        if name == "finish":
            status = {**self.client.status(), **self.budget_status()}
            disposition = stopping_review(
                self.state, self.limits, args["candidate_id"], args["report"], status
            )
            policy = (
                self.state["candidates"][args["candidate_id"]]["policy"]
                if args["candidate_id"]
                else empty_policy()
            )
            self.state["terminal"] = disposition
            write(
                self.root / "host/freeze.json",
                {
                    "run_id": self.run_id,
                    "policy": policy,
                    "disposition": disposition,
                    "test_feedback_seen": False,
                },
            )
            return disposition
        raise ValueError("unknown tool")


def empty_policy():
    return {
        "schema": "fannagent.broad-stop.v3",
        "name": "native-outcome",
        "rationale": "No qualified winner; native continuation",
        "fuel": 16000000,
        "state_slots": 0,
        "programs": {},
    }
