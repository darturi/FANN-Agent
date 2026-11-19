"""Single explicit resume; clone verified immutable inputs without retransferring data."""

import argparse
import json
import shlex

from prepare_capture import WORK, sha
from remote import OPTIONS, TARGET, remote, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", choices=("v2", "v3"), default="v2")
    args = parser.parse_args()
    revision = args.revision
    record = WORK / ("benchmark-" + revision + "-submission.json")
    if record.exists():
        raise RuntimeError("resumed comparison already submitted")
    manifest_path = WORK / ("benchmark-" + revision + "-overlay-manifest.json")
    manifest = json.loads(manifest_path.read_text())
    overlay = WORK / ("broad-oracle-benchmark-" + revision + "-overlay.tar.gz")
    assert sha(overlay) == manifest["overlay_sha256"]
    prior = json.loads((WORK / "resume-accounting-20261119.json").read_text())
    parent = (
        "/scratch/dar579/fannagent-benchmark-evaluation-v1/broad-oracle-benchmark-"
        + revision
        + "-20261119"
    )
    stage = parent + "/broad-oracle-benchmark-" + revision
    remote(shlex.join(["mkdir", "-m700", parent]))
    run(
        [
            "scp",
            *OPTIONS,
            str(overlay),
            str(overlay.with_suffix(".gz.sha256")),
            str(manifest_path),
            TARGET + ":" + parent + "/",
        ]
    )
    script = (
        r"""
import hashlib,json,os,tarfile
from pathlib import Path
os.umask(0o077)
parent=Path(PARENT)
base=Path(BASE)
target=Path(STAGE)
def sha(p):
 with p.open("rb") as h:return hashlib.file_digest(h,"sha256").hexdigest()
m=json.loads((parent/MANIFEST).read_text())
assert sha(base/"binding.json")==m["base_binding_sha256"]
target.mkdir(mode=0o700)
changed=set(m["changed"])
assert all(Path(n).name==n for n in set(m["base_files"])|changed)
for name,digest in m["base_files"].items():
 assert sha(base/name)==digest,name
 if name not in changed:os.link(base/name,target/name)
archive=parent/OVERLAY
assert sha(archive)==m["overlay_sha256"]
with tarfile.open(archive) as h:
 members=h.getmembers()
 assert {p.name for p in members}==changed
 assert all(p.isfile() for p in members)
 h.extractall(target,filter="data")
assert sha(target/"binding.json")==m["new_binding_sha256"]
for name,digest in m["new_files"].items():assert sha(target/name)==digest,name
(parent/"clone-verification.json").write_text(json.dumps({"status":"verified","base_binding_sha256":m["base_binding_sha256"],"new_binding_sha256":m["new_binding_sha256"],"hardlinks":len(m["base_files"])-len(set(m["base_files"])&changed),"overlaid":sorted(changed)},indent=2)+"\n")
print("IMMUTABLE_INPUT_CLONE_VERIFIED",flush=True)
""".replace("PARENT", repr(parent))
        .replace("BASE", repr(manifest.get("base_stage", prior["prior_stage"])))
        .replace("STAGE", repr(stage))
        .replace("MANIFEST", repr(manifest_path.name))
        .replace("OVERLAY", repr(overlay.name))
    )
    with (WORK / ("benchmark-" + revision + "-launch.log")).open("x") as log:
        log.write(remote(shlex.join(["python3", "-c", script])))
        log.flush()
        command = "\n".join(
            [
                "set -euo pipefail",
                "cd " + shlex.quote(stage),
                "sha256sum -c SHA256SUMS > input-verification.log",
                "bash submit-benchmark.sh --submit > launch.log 2>&1",
                "cat job-id",
            ]
        )
        output = remote(shlex.join(["bash", "-c", command]))
        log.write(output)
        job = output.strip()
        assert job.isdigit()
    probe = json.loads(remote(shlex.join(["cat", stage + "/.startup-preflight/check.json"])))
    assert probe["status"] == "oracle_native_startup_preflight_passed"
    value = {
        "stage": stage,
        "job_id": job,
        "input_binding_sha256": manifest["new_binding_sha256"],
        "overlay_sha256": sha(overlay),
        "full_local_archive_sha256": sha(WORK / ("broad-oracle-benchmark-" + revision + ".tar.gz")),
        "native_preflight": probe,
        "explicit_user_resume": True,
        "prior_cancelled_job_id": "23648495",
        "revision": revision,
        "prior_failed_job_id": manifest.get("prior_failed_job_id"),
    }
    record.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value))


if __name__ == "__main__":
    main()
