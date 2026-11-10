"""Offline audit and proposal screening. This CLI has no backend or provider commands."""

import argparse
import json
from pathlib import Path

from rb_evidence import load_evidence, load_frozen
from rb_plan import INSTALLATIONS, READER_OPENS, SEARCHES, load_plan, require
from rb_stats import quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, help="Optional single composite policy JSON")
    args = parser.parse_args()
    candidate = None
    if args.candidate is not None:
        require(
            args.candidate.is_file()
            and not args.candidate.is_symlink()
            and args.candidate.stat().st_size <= 256 * 1024,
            "Invalid policy file",
        )
        candidate = json.loads(args.candidate.read_bytes())
        require(type(candidate) is dict, "Expected one composite policy object")
    plan = load_plan()
    frozen = load_frozen()
    evidence = load_evidence(plan, frozen, candidate)
    reports = {family: quality(plan, frozen, evidence, family) for family in evidence.policies}
    print(
        json.dumps(
            {
                "scope": "saved development replay only",
                "sessions": len(plan.sessions),
                "queries": len(plan.cases),
                "timing_slots": sum(1 for _ in plan.timed()),
                "proposed_ceiling": {
                    "searches": sum(SEARCHES.values()),
                    "readers": sum(READER_OPENS.values()),
                    "installations": sum(INSTALLATIONS.values()),
                },
                "policy_identities": evidence.identities,
                "saved_recall": reports,
                "measured_session_latency": None,
                "released": False,
            },
            indent=2,
            allow_nan=False,
        )
    )
    if candidate is not None and not reports["candidate"]["passes"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
