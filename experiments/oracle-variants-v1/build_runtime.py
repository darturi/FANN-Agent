"""Use the unchanged agent compiler; replace only the compiled program pool."""

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "agent/src"))
sys.path.insert(0, str(HERE.parent / "filtered-ann-protocol-v2"))
from fannproto.compiler import compile_programs  # noqa: E402
from fannproto.policy import rule_hash, validate  # noqa: E402


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def prepare(policies, output):
    output.mkdir()
    programs = []
    for cohort, arm, matched in (("full_workload", 20, 30), ("heldout_test", 21, 31)):
        source = policies / ("oracle_feasible-" + cohort + ".json")
        policy = json.loads(source.read_text())
        validate(policy)
        shutil.copyfile(source, output / source.name)
        programs.extend(
            (
                {"arm": arm, "policy": policy, "force_continue": False},
                {"arm": matched, "policy": policy, "force_continue": True},
            )
        )
    empty = {
        "schema": "fannagent.filtered-ann.v2",
        "name": "oracle_comparison_empty",
        "rules": {},
        "rationale": "Empty-policy timing diagnostic.",
    }
    programs.append({"arm": 43, "policy": empty, "force_continue": False})
    code, compiled = compile_programs(programs)
    original = (
        ROOT
        / "trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1/engine"
    )
    capture = original.parents[1] / "oracle-variants-v1/capture-kit-v2"
    baseline = capture / "engine-sources.tar.gz"
    binding = json.loads((capture / "binding.json").read_text())
    if sha(baseline) != binding["files"][baseline.name]:
        raise ValueError("sealed baseline source archive differs")
    with tarfile.open(baseline) as handle:
        sealed = {
            m.name.removeprefix("engine/"): handle.extractfile(m).read()
            for m in handle.getmembers()
            if m.isfile()
        }
    present = {
        str(p.relative_to(original)): p.read_bytes()
        for p in original.rglob("*")
        if p.is_file() and p.suffix not in (".o", ".so", ".bc")
    }
    if present != sealed:
        raise ValueError("baseline engine differs from captured source archive")
    engine = output / "engine"
    shutil.copytree(original, engine, ignore=shutil.ignore_patterns("*.o", "*.so", "*.bc"))
    (engine / "src/compiled_v2.inc").write_text(code)
    changed = [
        str(p.relative_to(engine))
        for p in engine.rglob("*")
        if p.is_file() and p.read_bytes() != (original / p.relative_to(engine)).read_bytes()
    ]
    if changed != ["src/compiled_v2.inc"]:
        raise ValueError("unexpected engine changes: " + str(changed))
    (output / "compiled-programs.json").write_text(
        json.dumps(compiled, indent=2, sort_keys=True) + "\n"
    )
    certificate = {
        "unchanged_agent_validator": True,
        "unchanged_agent_compiler": True,
        "engine_changed_files": changed,
        "graph_algorithm_changed": False,
        "baseline_engine_archive_sha256": sha(baseline),
        "baseline_module_sha256": sha(capture / "oracle-module.so"),
        "compiler_sha256": sha(HERE.parent / "filtered-ann-protocol-v2/fannproto/compiler.py"),
        "policy_schema_sha256": sha(HERE.parent / "filtered-ann-protocol-v2/fannproto/policy.py"),
        "generation_toolspec_sha256": sha(
            HERE.parent / "filtered-ann-protocol-v2/fannproto/toolspec.py"
        ),
        "generation_controller_sha256": sha(
            HERE.parent / "filtered-ann-protocol-v2/fannproto/controller.py"
        ),
        "normal_generation_submission": "evaluate_candidates({policies: [policy]})",
        "discovery_feedback_or_nomination_claim": False,
        "compiled_source_hash": compiled["source_hash"],
        "rule_hashes": {str(p["arm"]): rule_hash(p["policy"]) for p in programs},
    }
    (output / "compiler-certificate.json").write_text(json.dumps(certificate, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.policies, args.output))
