"""Reviewed A2 controller; shared reservation forbids repeat allocation."""

import argparse
import json
from pathlib import Path

from pc_common import verify
from pc_control import collect, status, submit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["verify", "submit", "status", "collect"])
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    if args.command == "submit":
        if len(args.paths) != 2:
            parser.error("submit ORIGINAL_BUNDLE SOURCE_RESULTS_ROOT")
        submit(package, *[Path(p).resolve() for p in args.paths])
    elif args.paths:
        parser.error("verify/status/collect use the package binding; no paths")
    elif args.command == "verify":
        print(json.dumps(verify(package)["counts"], indent=2))
    elif args.command == "status":
        status(package)
    else:
        collect(package)


if __name__ == "__main__":
    main()
