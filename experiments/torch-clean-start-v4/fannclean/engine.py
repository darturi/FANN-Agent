"""Trusted acquisition/evaluation engine. Never imports empirical data from another run."""

import math
from pathlib import Path

from fannagent.api.broad_policy import FEATURES, validate

from .core import Ledger, Limits, canonical, digest, read, write


def empty():
    return {
        "schema": "fannagent.broad-stop.v3",
        "name": "native",
        "rationale": "No stopping program",
        "fuel": 16000000,
        "state_slots": 0,
        "programs": {},
    }


def capture_policy(points, features):
    root = ["available", ["feature", features[0]]]
    for feature in features[1:]:
        root = ["or", root, ["available", ["feature", feature]]]
    return {
        **empty(),
        "name": "requested-observations",
        "programs": {
            ("unfiltered" if t < 0 else f"votes{t}"): {
                "checkpoints": points,
                "root": root,
                "updates": {},
            }
            for t in (-1, 743, 527, 310, 192, 108, 32)
        },
    }


def bindings(payload):
    result = {"empty": (empty(), False)}
    if payload["kind"] in ("acquire", "profile"):
        result["capture"] = (capture_policy(payload["checkpoints"], payload["features"]), True)
    else:
        for i, policy in enumerate(payload["policies"]):
            validate(policy)
            result[f"candidate:{i}"] = (policy, False)
            result[f"matched:{i}"] = (policy, True)
    return result


def score(output, truth):
    ids = [r[0] for r in output]
    if len(ids) > 10 or len(set(ids)) != len(ids) or any(not math.isfinite(r[1]) for r in output):
        raise ValueError("invalid raw ANN output")
    return sum(i in {r[0] for r in truth} for i in ids) / min(10, len(truth)) if truth else 1.0


class Engine:
    def __init__(self, root, factory):
        self.root, self.factory = Path(root), factory
        config = read(self.root / "config.json")
        self.run_id, self.limits = config["run_id"], Limits(**config["limits"])
        self.cases = {r["handle"]: r for r in read(self.root / "private/cases.json")}
        self.ledger = Ledger(
            self.root / "private/query-ledger.json", self.limits, self.run_id, checkpoint_every=64
        )

    def selection(self, payload):
        if payload["kind"] in ("confirm", "final"):
            return [
                r
                for r in self.cases.values()
                if payload["kind"] == "final" or r["role"] == "development"
            ]
        handles = payload["handles"]
        if (
            not isinstance(handles, list)
            or not 1 <= len(handles) <= 512
            or len(set(handles)) != len(handles)
        ):
            raise ValueError("one to 512 distinct development handles required")
        selected = [self.cases[h] for h in handles]
        if any(r["role"] != "development" for r in selected):
            raise ValueError("protected queries cannot be acquired during discovery")
        return selected

    def validate_request(self, payload):
        kind = payload.get("kind")
        if kind not in ("acquire", "profile", "screen", "confirm", "final"):
            raise ValueError("unknown action")
        expected = (
            {"kind", "handles", "checkpoints", "features"}
            if kind in ("acquire", "profile")
            else {"kind", "policies", "handles", "blocks"}
        )
        if set(payload) != expected:
            raise ValueError("unexpected request fields")
        cases = self.selection(payload)
        missing = sum(
            not (self.root / "private/cache" / (digest(c["handle"]) + ".json")).exists()
            for c in cases
        )
        conditions = {r["filter"] for r in cases}
        if kind in ("profile", "screen"):
            groups = {r["group"] for r in cases}
            conditions = {r["filter"] for r in cases}
            if len(groups) < 2 or len(cases) != len(groups) * len(conditions):
                raise ValueError(
                    "timing requires at least two groups with balanced requested conditions"
                )
        if kind in ("acquire", "profile"):
            cps, features = payload["checkpoints"], payload["features"]
            if (
                not isinstance(cps, list)
                or not 1 <= len(cps) <= 4096
                or cps != sorted(set(cps))
                or any(type(c) is not int or not 1 <= c <= 4096 for c in cps)
            ):
                raise ValueError("a sorted unique legal checkpoint schedule is required")
            if (
                not isinstance(features, list)
                or not features
                or len(set(features)) != len(features)
                or not set(features) <= set(FEATURES)
            ):
                raise ValueError("only declared causal features may be requested")
            return cases, 2 * missing + len(cases) * (1 + len(cps)) + (
                12 * len(cases) + 8 * len(conditions) if kind == "profile" else 0
            )
        policies = payload["policies"]
        if (
            not isinstance(policies, list)
            or not 1 <= len(policies) <= 4
            or kind in ("confirm", "final")
            and len(policies) != 1
        ):
            raise ValueError("one to four exploratory policies; one confirmation/final policy")
        for policy in policies:
            validate(policy)
        blocks = payload["blocks"]
        if type(blocks) is not int or not 2 <= blocks <= 6 or kind == "final" and blocks != 2:
            raise ValueError("predeclare two to six blocks; final has exactly two")
        if kind == "final":
            return cases, read(self.root / "config.json")["final_worst"]
        # At most native+truth, candidate+independent forced-prefix per candidate, then brackets.
        timed = min(len(cases), 96 * 7) if kind == "confirm" else len(cases)
        return cases, 2 * missing + len(cases) * 2 * len(policies) + blocks * timed * (
            5 + 2 * len(policies)
        ) + blocks * len(conditions) * (3 + 2 * len(policies))

    def process(self, identity, payload):
        from .timing import measure, summarize

        cases, worst = self.validate_request(payload)
        final = payload["kind"] == "final"
        frozen = self.root / "private/final-freeze.json"
        if frozen.exists() and not final:
            raise ValueError("final policy frozen; discovery closed")
        if final:
            if not frozen.exists() or read(frozen)["policy"] != payload["policies"][0]:
                raise ValueError("final request must match the host-frozen agent artifact")
            if (self.root / "private/final-started.json").exists():
                raise ValueError("final evaluation has already been attempted; no reruns")
            write(
                self.root / "private/final-started.json",
                {"request_id": identity, "run_id": self.run_id},
            )
        request_dir = self.root / "private/requests" / identity
        request_dir.mkdir(parents=True, exist_ok=False)
        write(request_dir / "request.json", {"run_id": self.run_id, "payload": payload})
        self.ledger.reserve(identity, worst, final)
        evidence, raw_quality, acquisition_diagnostics = [], [], []
        program_bindings = bindings(payload)
        if final:
            refs = read(self.root / "private/comparison.json")
            if refs["agent_freeze_sha256"] != digest(read(frozen)):
                raise ValueError("oracle comparison attached before/differently from freeze")
            for name in ("oracle_full", "oracle_test"):
                validate(refs[name])
                program_bindings[name] = (refs[name], False)
        with (
            self.ledger.checkpoint_on_exit(),
            self.factory(program_bindings, request_dir) as backend,
            (request_dir / "queries.jsonl").open("ab", buffering=262144) as journal,
        ):
            reference_memory = {}

            def query(case, family, reader=0, audit=False, checkpoint=None):
                ordinal = self.ledger.tick(identity, "exact" if family == "exact" else "ann")
                result = backend.execute(
                    case, family, reader=reader, audit=audit, checkpoint=checkpoint
                )
                if result["request_ns"] <= 0:
                    raise ValueError("invalid native timer")
                result["query_ordinal"] = ordinal
                # Preserve completed measurements even when a later query/cleanup fails.
                journal.write(
                    canonical(
                        {
                            "handle": case["handle"],
                            "family": family,
                            "reader": reader,
                            "forced_checkpoint": checkpoint,
                            "result": result,
                        }
                    )
                    + b"\n"
                )
                if ordinal % 64 == 0:
                    journal.flush()
                    __import__("os").fsync(journal.fileno())
                return result

            def baseline(case):
                if case["handle"] in reference_memory:
                    return reference_memory[case["handle"]]
                path = self.root / "private/cache" / (digest(case["handle"]) + ".json")
                if path.exists():
                    cached = read(path)
                    if cached["run_id"] != self.run_id:
                        raise ValueError("cross-run reference cache rejected")
                    producer = read(self.ledger.path)["requests"].get(cached.get("request_id"), {})
                    if (
                        cached.get("case_sha256") != digest(case)
                        or not producer
                        or not 0
                        < cached.get("native_ordinal", 0)
                        < cached.get("truth_ordinal", 0)
                        <= producer["actual"]
                    ):
                        raise ValueError("reference cache lacks same-run executed-query provenance")
                    reference_memory[case["handle"]] = cached
                    return cached
                native, truth = query(case, "native"), query(case, "exact")
                cached = {
                    "run_id": self.run_id,
                    "native": native["output"],
                    "truth": truth["output"],
                    "native_recall": score(native["output"], truth["output"]),
                    "request_id": identity,
                    "case_sha256": digest(case),
                    "native_ordinal": native["query_ordinal"],
                    "truth_ordinal": truth["query_ordinal"],
                    "native_request_ns": native["request_ns"],
                }
                write(path, cached)
                reference_memory[case["handle"]] = cached
                return cached

            def public(case, result, frame, ref, kind, label=None):
                values = frame.get("values", [])
                if len(values) != len(FEATURES):
                    raise ValueError("causal observation has the wrong schema")
                return {
                    "run_id": self.run_id,
                    "request_id": identity,
                    "query_ordinal": result["query_ordinal"],
                    "handle": case["handle"],
                    "group": case["group"],
                    "filter": case["filter"],
                    "kind": kind,
                    "checkpoint": frame["checkpoint"],
                    "features": dict(zip(FEATURES, values, strict=True)),
                    "label": label,
                    "native_recall": ref["native_recall"],
                    "native_request_ns": ref["native_request_ns"],
                    "collector_request_ns": result["request_ns"],
                    "diagnostic_single_query_timing_only": True,
                    "native_count": len(ref["native"]),
                    "observation_schedule": result.get(
                        "observation_schedule", payload.get("checkpoints")
                    ),
                    "fault": result.get("fault", False),
                    "exhausted": result.get("exhausted", False),
                    "policy_hash": result.get("policy_hash"),
                }

            if payload["kind"] in ("acquire", "profile"):
                for case in cases:
                    ref = baseline(case)
                    captured = query(case, "capture", audit=True)
                    if captured["output"] != ref["native"]:
                        raise ValueError("observation changed native output")
                    acquisition_diagnostics.append(
                        {
                            "handle": case["handle"],
                            "fault": captured.get("fault", False),
                            "exhausted": captured.get("exhausted", False),
                            "reached_frames": len(captured["frames"]),
                            "requested_checkpoints": len(payload["checkpoints"]),
                        }
                    )
                    for frame in captured["frames"]:
                        if frame.get("fault") or frame.get("exhausted"):
                            continue
                        stopped = query(case, "forced", checkpoint=frame["checkpoint"])
                        if stopped["checkpoint"] != frame["checkpoint"]:
                            raise ValueError("forced prefix did not reach its requested checkpoint")
                        label = {
                            "recall": score(stopped["output"], ref["truth"]),
                            "result_count": len(stopped["output"]),
                            "query_ordinal": stopped["query_ordinal"],
                            "request_ns": stopped["request_ns"],
                        }
                        label["safe"] = label["recall"] + 1e-12 >= ref["native_recall"]
                        label["count_preserving"] = label["result_count"] >= len(ref["native"])
                        evidence.append(public(case, captured, frame, ref, "acquisition", label))

                def families(_):
                    return ["capture", "clone", "empty"]
            else:
                expected = {}
                for case in cases:
                    ref = baseline(case)
                    families_for_case = [f"candidate:{i}" for i in range(len(payload["policies"]))]
                    if final:
                        families_for_case += ["oracle_full"] + (
                            ["oracle_test"] if case["role"] == "test" else []
                        )
                    for family in families_for_case:
                        actual = query(case, family, audit=True)
                        cp = actual["checkpoint"]
                        wanted = (
                            ref["native"]
                            if not cp
                            else query(case, "forced", checkpoint=cp)["output"]
                        )
                        if actual["output"] != wanted:
                            raise ValueError("compiled decision/output audit failed")
                        record = {
                            "run_id": self.run_id,
                            "request_id": identity,
                            "query_ordinal": actual["query_ordinal"],
                            "fault": actual.get("fault", False),
                            "exhausted": actual.get("exhausted", False),
                            "handle": case["handle"],
                            "group": case["group"],
                            "role": case["role"],
                            "filter": case["filter"],
                            "family": family,
                            "checkpoint": cp,
                            "recall": score(actual["output"], ref["truth"]),
                            "native_recall": ref["native_recall"],
                            "count": len(actual["output"]),
                            "native_count": len(ref["native"]),
                        }
                        raw_quality.append(record)
                        expected[case["handle"], family] = actual["output"]
                        if not final:
                            artifact = payload["policies"][int(family.split(":")[1])]
                            predicate = (
                                "unfiltered" if case["filter"] < 0 else f"votes{case['filter']}"
                            )
                            actual["observation_schedule"] = (
                                artifact["programs"].get(predicate, {}).get("checkpoints", [])
                            )
                        if (
                            not final
                            and actual["frames"]
                            and not record["fault"]
                            and not record["exhausted"]
                        ):
                            frame = actual["frames"][-1]
                            # Continuing to native does NOT label an earlier observed prefix safe.
                            prefix = (
                                actual
                                if cp
                                else query(case, "forced", checkpoint=frame["checkpoint"])
                            )
                            prefix_recall = score(prefix["output"], ref["truth"])
                            label = {
                                "query_ordinal": prefix["query_ordinal"],
                                "recall": prefix_recall,
                                "result_count": len(prefix["output"]),
                                "safe": prefix_recall + 1e-12 >= record["native_recall"],
                                "count_preserving": len(prefix["output"]) >= record["native_count"],
                            }
                            actual["policy_hash"] = digest(
                                payload["policies"][int(family.split(":")[1])]
                            )
                            evidence.append(
                                public(case, actual, actual["frames"][-1], ref, "evaluation", label)
                            )
                        elif not final and actual["frames"]:
                            evidence.append(
                                public(
                                    case,
                                    actual,
                                    actual["frames"][-1],
                                    ref,
                                    "resource_failure",
                                    None,
                                )
                            )

                def families(c):
                    return (
                        [
                            f
                            for i in range(len(payload["policies"]))
                            for f in (f"candidate:{i}", f"matched:{i}")
                        ]
                        + ["clone", "empty"]
                        + (
                            ["oracle_full"] + (["oracle_test"] if c["role"] == "test" else [])
                            if final
                            else []
                        )
                    )

            def timed(case, family, reader):
                result = query(case, family, reader)
                wanted = (
                    expected.get((case["handle"], family))
                    if family.startswith("candidate:") or family.startswith("oracle_")
                    else baseline(case)["native"]
                )
                if payload["kind"] == "profile":
                    wanted = baseline(case)["native"]
                if result["output"] != wanted:
                    raise ValueError("timed output changed; preserve all records and fail")
                return result

            timing = []
            if payload["kind"] != "acquire":
                screen = cases
                if payload["kind"] == "confirm":
                    gs = sorted(
                        {r["group"] for r in cases},
                        key=lambda g: digest([self.run_id, identity, g]),
                    )[:96]
                    screen = [r for r in cases if r["group"] in gs]
                timing = measure(
                    screen, families, timed, int(identity[:8], 16), payload.get("blocks", 2)
                )
            write(request_dir / "quality.json", raw_quality)
            write(request_dir / "timing.json", timing)
            journal.flush()
            __import__("os").fsync(journal.fileno())
        self.ledger.settle(identity, backend.cleanup_verified)
        result = {
            "run_id": self.run_id,
            "request_id": identity,
            "payload_sha256": digest(payload),
            "status": "complete",
            "evidence": [] if final else evidence,
            "quality": [] if final else raw_quality,
            "samples": [] if final else timing,
            "acquisition_diagnostics": acquisition_diagnostics,
            "timing": None
            if final or not timing
            else summarize(
                timing,
                self.limits.bootstrap_draws,
                self.limits.control_tolerance,
                int(identity[:8], 16),
            ),
            "full_quality": payload["kind"] == "confirm",
            "private_cleanup_verified": True,
            "ledger": read(self.ledger.path),
        }
        # Final outcomes and references stay private and cannot re-enter a model conversation.
        if final:
            result = {
                k: v
                for k, v in result.items()
                if k not in ("evidence", "quality", "timing", "samples")
            }
            result["final_complete"] = True
        write(request_dir / "response.json", result)
        return result
