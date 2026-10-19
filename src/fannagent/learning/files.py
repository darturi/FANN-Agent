"""Bounded data-only input and exclusive output for the offline learning tools."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from ..api import AgentError
from ..store import canonical

MAX_FILE_BYTES = 128 * 2**20


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AgentError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value):
    raise AgentError(f"nonfinite JSON value: {value}")


def decode(content: bytes | str):
    try:
        return json.loads(content, object_pairs_hook=_object, parse_constant=_nonfinite)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AgentError(f"invalid learning JSON: {exc}") from None


def read_bytes(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
                raise AgentError("learning input is not a bounded regular file")
            content = handle.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise AgentError("learning input exceeds size bound")
        return content
    except OSError as exc:
        raise AgentError(f"cannot read learning input: {exc}") from None


def read_json(path: Path):
    return decode(read_bytes(path))


def write_new(path: Path, value):
    content = canonical(value) + b"\n"
    try:
        with path.open("xb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise AgentError(f"cannot create learning output: {exc}") from None
