"""Agent submission adapter for ordinary broad-policy artifacts.

The host supplies the evaluator and its evidence/budget scope. Programs contain
only causal runtime expressions; scripts that fit them remain offline.
"""

import json
from pathlib import Path

from fannagent.api.broad_policy import MAX_BYTES, canonical, policy_hash, validate

from .compiler import compile_programs

TOOL = {
    "type": "function",
    "name": "evaluate_broad_candidates",
    "description": (
        "Validate, compile and evaluate broad stopping policies. "
        "Submit inline policies or workspace JSON artifact paths."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "policies": {"type": "array", "items": {"type": "object"}, "maxItems": 20},
            "policy_paths": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        },
        "additionalProperties": False,
    },
}


class BroadPolicyTools:
    def __init__(self, workspace, registry, evaluator):
        self.workspace = Path(workspace).resolve(strict=True)
        self.registry = Path(registry)
        self.registry.mkdir(parents=True, exist_ok=True)
        self.evaluator = evaluator

    def evaluate_broad_candidates(self, arguments):
        if type(arguments) is not dict or not set(arguments) <= {"policies", "policy_paths"}:
            raise ValueError("invalid candidate submission")
        policies, paths = arguments.get("policies", []), arguments.get("policy_paths", [])
        if (
            type(policies) is not list
            or type(paths) is not list
            or not 1 <= len(policies) + len(paths) <= 20
        ):
            raise ValueError("submit one to twenty candidates")
        policies = list(policies)
        for name in paths:
            if type(name) is not str:
                raise ValueError("policy path must be text")
            path = (self.workspace / name).resolve(strict=True)
            if (
                not path.is_relative_to(self.workspace)
                or not path.is_file()
                or path.stat().st_size > MAX_BYTES
            ):
                raise ValueError("policy path escapes workspace or exceeds storage budget")
            policies.append(json.loads(path.read_text()))
        results = []
        for policy in policies:
            validate(policy)
            code, compiled = compile_programs(
                [{"arm": 60, "policy": policy, "force_continue": False}]
            )
            digest = policy_hash(policy)
            artifact = self.registry / (digest + ".json")
            artifact.write_text(canonical(policy) + "\n")
            (self.registry / (digest + ".inc")).write_text(code)
            metrics = self.evaluator(policy, compiled)
            results.append(
                {
                    "policy_hash": digest,
                    "artifact": str(artifact),
                    "metrics": metrics,
                    "table_bytes_upper_bound": compiled["bindings"][0]["table_bytes_upper_bound"],
                }
            )
        return {"schema": "fannagent.broad-evaluation.v3", "candidates": results}
