"""Exclusive local campaign binding and durable monotone launch state; no scheduler."""

from pathlib import Path

from nh_common import HERE, closed_native, config, digest, offline, private, read, save, sha


def specification(inner, stage, result, workspace, image_sha):
    c = config()
    if image_sha != c["image_sha256"]:
        raise ValueError("Original image identity required")
    paths = {
        key: str(Path(value))
        for key, value in {
            "inner": inner,
            "stage": stage,
            "result": result,
            "workspace": workspace,
        }.items()
    }
    for p in paths.values():
        if not Path(p).is_absolute() or any(x in p for x in (":", ",", "\n", "\r")):
            raise ValueError("Unsupported binding path")
    return {
        "schema": "a3.integration.binding.v1",
        "paths": paths,
        "archive_sha256": c["original_archive_sha256"],
        "manifest_sha256": c["original_manifest_sha256"],
        "image_sha256": image_sha,
        "integration_sha256": sha(Path(__file__).parent / "DESIGN-FREEZE.json"),
        "integration_files": {
            str(p.relative_to(HERE)): sha(p)
            for p in HERE.rglob("*")
            if p.is_file() and p.suffix in (".py", ".json")
        },
        "limits": c["limits"],
        "phase_seconds": c["phase_seconds"],
        "native_release": False,
        "all_prior_allowances_closed": True,
    }


def validate_binding(binding):
    c = config()
    required = {
        "schema",
        "paths",
        "archive_sha256",
        "manifest_sha256",
        "image_sha256",
        "integration_sha256",
        "integration_files",
        "limits",
        "phase_seconds",
        "native_release",
        "all_prior_allowances_closed",
    }
    if not required <= set(binding) or set(binding) - required - {
        "storage_evidence",
        "persistent_references",
        "runtime",
    }:
        raise ValueError("Complete closed binding schema required")
    if (
        binding["schema"] != "a3.integration.binding.v1"
        or digest(binding["limits"]) != digest(c["limits"])
        or digest(binding["phase_seconds"]) != digest(c["phase_seconds"])
        or binding["all_prior_allowances_closed"] is not True
        or binding["archive_sha256"] != c["original_archive_sha256"]
        or binding["manifest_sha256"] != c["original_manifest_sha256"]
        or binding["image_sha256"] != c["image_sha256"]
    ):
        raise ValueError("Original identities/limits changed")
    paths = binding["paths"]
    if not isinstance(paths, dict) or set(paths) != {"inner", "stage", "result", "workspace"}:
        raise ValueError("Complete binding paths required")
    for value in paths.values():
        if (
            not isinstance(value, str)
            or not Path(value).is_absolute()
            or any(x in value for x in (":", ",", "\n", "\r"))
        ):
            raise ValueError("Unsupported binding path")
    current = {
        str(p.relative_to(HERE)): sha(p)
        for p in HERE.rglob("*")
        if p.is_file() and p.suffix in (".py", ".json")
    }
    if binding["integration_files"] != current or binding["integration_sha256"] != sha(
        HERE / "DESIGN-FREEZE.json"
    ):
        raise ValueError("Integration source identity differs")
    if binding.get("native_release") is not False:
        raise ValueError("No native release")
    return digest(binding)


class Campaign:
    def __init__(self, root, binding):
        offline()
        self.root = private(root)
        self.binding = binding
        if not self.root.name.startswith("local-"):
            raise ValueError("Only a new local campaign namespace is permitted")
        self.key = validate_binding(binding)
        save(self.root / "binding.json", {"binding": binding, "sha256": self.key})
        self.append("prepared")

    def append(self, state):
        previous = sorted(self.root.glob("event-*.json"))
        allowed = {
            "prepared": "launching",
            "launching": "running",
            "running": "terminal",
            "terminal": "retained",
        }
        for i, p in enumerate(previous):
            row = read(p)
            if (
                p.name != f"event-{i:02d}.json"
                or row["binding_sha256"] != self.key
                or row["previous_sha256"] != (sha(previous[i - 1]) if i else None)
            ):
                raise RuntimeError("Campaign history changed")
            if (i == 0 and row["state"] != "prepared") or (
                i and allowed.get(read(previous[i - 1])["state"]) != row["state"]
            ):
                raise RuntimeError("Invalid campaign transition history")
        if previous:
            last = read(previous[-1])
            if last["binding_sha256"] != self.key or allowed.get(last["state"]) != state:
                raise RuntimeError("Stale, uncertain, terminal or repeated launch")
        elif state != "prepared":
            raise RuntimeError("Missing preparation")
        persisted = read(self.root / "binding.json")
        if persisted != {"binding": self.binding, "sha256": self.key}:
            raise RuntimeError("Binding changed")
        save(
            self.root / (f"event-{len(previous):02d}.json"),
            {
                "state": state,
                "binding_sha256": self.key,
                "previous_sha256": sha(previous[-1]) if previous else None,
            },
        )

    def launch_once(self, callback):
        self.append("launching")
        # Uncertain exceptions leave launching durable and never permit a repeat.
        value = callback(self.binding, self.key)
        last = read(sorted(self.root.glob("event-*.json"))[-1])["state"]
        if last == "launching":
            self.append("running")
        elif last != "running":
            raise RuntimeError("Unexpected launch result state")
        return value

    def submit(self, *a, **k):
        closed_native()


if __name__ == "__main__":
    closed_native()


def validate_target_binding(envelope, inner):
    key = validate_binding(envelope["binding"])
    if (
        envelope["sha256"] != key
        or sha(Path(inner) / "manifest.json") != envelope["binding"]["manifest_sha256"]
    ):
        raise ValueError("Exact target manifest/binding differs")
    return key


def require_native_admission(context):
    # No recognized issuer, new allowance, or authority backend exists in this
    # review. Neither local observations nor self-asserted labels can grant one.
    raise RuntimeError("Native admission HOLD: no recognized fresh authorization or site authority")


def validate_host_context(binding, context, result):
    paths = {
        "inner": str(context["original"]),
        "stage": str(context["inner"]),
        "workspace": str(context["workspace"]),
        "result": str(result),
    }
    if binding["paths"] != paths or Path(context["integration"]) != HERE:
        raise ValueError("Host mount sources differ from immutable binding")
    if sha(context["image"]) != binding["image_sha256"]:
        raise ValueError("Host image differs from immutable binding")
