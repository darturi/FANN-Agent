"""<=64-row consumer fixture adapter; no DB/producer/native integration path."""

import exact_codec as codec
import exact_vector as original
import integration


class FixtureIdentity(original.FixtureIdentity):
    def __init__(self, spec):
        if type(spec) is not integration.FixtureSpec:
            raise RuntimeError("Only the original bounded fixture specification is allowed")
        codec.verify_sources()
        super().__init__()
        self.spec = spec

    def canonical(self, value):
        if type(value) is list:
            return self.store.canonical(value)
        return self.store.canonical(codec.plain_row(value))

    def digest(self, payload):
        self.calls += 1
        if (
            original._ACTIVE is not self
            or self.calls != 1
            or type(payload) is not dict
            or set(payload) != {"rows", "fields"}
            or type(payload["rows"]) is not list
            or len(payload["rows"]) != self.spec.rows
            or type(payload["fields"]) is not list
            or self.store.canonical(payload["fields"]) != self.spec.fields_json
            or any(type(r["vector"]) is not codec.ExactVector for r in payload["rows"])
        ):
            raise RuntimeError("Exact memory fixture identity scope differs")
        self.record = self.stream.framed(payload, self.canonical)
        if self.record["digest"] != self.spec.identity:
            raise RuntimeError("Exact memory fixture identity mismatch")
        return self.record["digest"]


def construct(rows, fields, spec, profile=None):
    if (
        type(spec) is not integration.FixtureSpec
        or type(rows) is not list
        or len(rows) != spec.rows
        or not 1 <= len(rows) <= 64
    ):
        raise RuntimeError("No native-sized or unknown fixture construction allowed")
    from fannagent.snapshot import Snapshot

    with FixtureIdentity(spec):
        result = Snapshot(rows, fields, profile)
    return result


if __name__ == "__main__":
    raise RuntimeError("Offline fixture consumer only; no native release")
