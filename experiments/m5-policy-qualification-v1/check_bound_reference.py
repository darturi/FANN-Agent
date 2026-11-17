"""Check compiled nominees against hash-verified M1 development labels before deployment."""

import collections
import hashlib
import json
import sys
import tarfile

from m5_design import ARMS, EXPECTED_STOPS, FILTERS, choose
from package_kit import KIT, RUNTIME, STUDY, sha, write


def run():
    sys.path.append(str(RUNTIME))
    from common import threshold
    from m5_experiment import filter_name, load_programs

    binding = json.loads((KIT / "binding.json").read_text())
    assert sha(KIT / "expected.jsonl") == binding["expected_sha256"]
    assert sha(KIT / "nominees.json") == binding["nominees_sha256"]
    archive = STUDY / "returns/qualification-23376796.tar.gz"
    assert sha(archive) == "8a180f046da12d943bea1bb9bea36b3839044876606c13beb1783e5f47bba53d"
    raw, compact = hashlib.sha256(), hashlib.sha256()
    with tarfile.open(archive) as tf:
        for line in tf.extractfile("results/timing/quality.jsonl"):
            raw.update(line)
            r = json.loads(line)
            compact.update(
                (
                    json.dumps(
                        {
                            "id": r["id"],
                            "checkpoints": r["checkpoints"],
                            "prefixes": r["prefixes"],
                            "results": {"native640": r["results"]["native640"]},
                        },
                        sort_keys=True,
                    )
                    + "\n"
                ).encode()
            )
    assert raw.hexdigest() == binding["M1_quality_sha256"]
    assert compact.hexdigest() == binding["expected_sha256"]
    queries = {
        q["id"]: q for q in map(json.loads, (KIT / "queries.jsonl").read_text().splitlines())
    }
    entries = load_programs(KIT)
    stops = {n: collections.Counter() for n in EXPECTED_STOPS}
    losses = collections.Counter()
    cases = 0
    for r in map(json.loads, (KIT / "expected.jsonl").read_text().splitlines()):
        q = queries[r["id"]]
        t = threshold(q)
        for name in EXPECTED_STOPS:
            cp = choose(entries[ARMS[name]], filter_name(t), r["checkpoints"])
            score = r["prefixes"][str(cp)]["recall"] if cp else r["results"]["native640"]["recall"]
            losses[name] += score < r["results"]["native640"]["recall"] - 1e-12
            stops[name][t] += bool(cp)
        cases += 1
    assert cases == 3150 and not any(losses.values())
    assert all(
        stops[name][t] == EXPECTED_STOPS[name].get(t, 0) for name in EXPECTED_STOPS for t in FILTERS
    )
    report = {
        "status": "passed",
        "existing_development_labels_checked": cases,
        "stop_counts": stops,
        "loss_cases": losses,
        "expected_sha256": binding["expected_sha256"],
        "nominees_sha256": binding["nominees_sha256"],
        "original_graph_M5_qualification_pending": True,
        "new_searches": 0,
        "provider_calls": 0,
        "validation_test_outcomes_opened": False,
    }
    write(RUNTIME / "checks/bound-reference-check.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    run()
