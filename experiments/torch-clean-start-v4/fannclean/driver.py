"""Container entrypoints. No provider, prior-run data, or scheduler client."""

import argparse
import shutil
from pathlib import Path

from .core import read
from .deploy import compile_request
from .engine import Engine
from .postgres import Postgres


def main():
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=("compile", "execute"))
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--identity")
    a = p.parse_args()
    payload = read(a.directory / "payload.json")
    if a.operation == "compile":
        compile_request(a.root, a.directory, payload)
    else:

        def factory(bindings, request_dir):
            shutil.copyfile(a.directory / "module.json", request_dir / "module.json")
            return Postgres(a.root, bindings, request_dir)

        Engine(a.root, factory).process(a.identity, payload)


if __name__ == "__main__":
    main()
