"""PLAN-bound login/allocated-host admission; original science is unchanged."""

import hashlib
import json
import os
import pwd
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "integration"))
import ni_control as C
import site_trust as T
from nh_common import digest, read, save, sha

PROJECT = "torch_pr_288_courant"


def stable_configuration(text):
    values = {}
    for line in text.splitlines():
        m = re.fullmatch(
            r"\s*(AuthType|ClusterName|SlurmctldPort|SlurmctldHost\[[0-9]+\])\s*=\s*(\S.*?)\s*",
            line,
        )
        if m:
            if m[1] in values:
                raise ValueError("Duplicate stable identity")
            values[m[1]] = m[2]
    if not {"AuthType", "ClusterName", "SlurmctldPort"} <= values.keys() or not any(
        k.startswith("SlurmctldHost[") for k in values
    ):
        raise ValueError("Incomplete stable identity")
    if values["AuthType"] not in ("auth/munge", "auth/slurm"):
        raise ValueError("Unknown authentication")
    return values


def stable_client(proof):
    return {"path": proof["path"], "sha256": proof["sha256"], "policy_sha256": digest(T.POLICY)}


def assoc_accounts(text, cluster, user):
    result = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split("|")
        if len(fields) != 6:
            raise ValueError("Strict association fields required")
        c, u, account, partition, qos, default = fields
        if c == cluster and u == user and partition in ("", "cs"):
            if not re.fullmatch("[A-Za-z0-9_-]+", account):
                raise ValueError("Unsafe account")
            result.add(account)
    return sorted(result)


def query_accounting(client, user):
    binary = T.trusted_binary(C.shutil.which("sacctmgr") or "/opt/slurm/bin/sacctmgr")
    argv = [
        binary["path"],
        "--readonly",
        "-n",
        "-P",
        "show",
        "associations",
        "where",
        "user=" + user,
        "format=Cluster,User,Account,Partition,QOS,DefaultQOS",
    ]
    text = C.bounded_command(argv, timeout=10)
    if T.trusted_binary(binary["path"]) != binary:
        raise RuntimeError("Accounting client changed")
    partition = client.query("--oneliner", "show", "partition", "cs")
    return {"associations": text, "partition_cs": partition, "client": binary, "argv": argv}


def site_check(package):
    plan = C.verify(package)
    client = C.SiteClient(C.shutil.which("scontrol") or "/usr/bin/scontrol")
    proof = client.probe()
    configuration = client.query("show", "config")
    stable = stable_configuration(configuration)
    if stable["AuthType"] != proof["authentication"]:
        raise RuntimeError("Authentication race")
    identity = {
        "client": stable_client(proof["client"]),
        "version": proof["version"],
        "authentication": proof["authentication"],
        "configuration": stable,
    }
    user = pwd.getpwuid(os.getuid()).pw_name
    accounting = query_accounting(client, user)
    accounts = assoc_accounts(accounting["associations"], stable["ClusterName"], user)
    expected = plan.get("qualification_account")
    if expected != PROJECT:
        raise RuntimeError("Frozen intended project differs")
    account = {
        "configured": os.environ.get("TORCH_SLURM_ACCOUNT"),
        "intended": expected,
        "eligible_association_accounts": accounts,
        "intended_association_present": expected in accounts,
        "configured_matches_intended": os.environ.get("TORCH_SLURM_ACCOUNT") == expected,
        "partition_limits_require_review": True,
    }
    state = C.state_root(package)
    anchor = state / "site-check.json"
    if anchor.exists():
        if read(anchor)["identity"] != identity:
            raise RuntimeError("Stable authenticated site changed")
    else:
        save(anchor, {"identity": identity, "allocations": 0, "searches": 0})
    observation = {
        "identity": identity,
        "probe": proof,
        "configuration_response_sha256": hashlib.sha256(configuration.encode()).hexdigest(),
        "account": account,
        "accounting": accounting,
        "allocations": 0,
        "searches": 0,
    }
    save(state / ("site-observation-" + str(time.time_ns()) + ".json"), observation)
    print(
        json.dumps(
            {"site_check": observation, "allocations": 0, "searches": 0, "approval": "not issued"},
            indent=2,
        )
    )
    return observation


def submission_site_check(package):
    observation = site_check(package)
    a = observation["account"]
    if not a["intended_association_present"] or not a["configured_matches_intended"]:
        raise RuntimeError(
            "Intended current project association/account is not ready; no submission"
        )
    return observation


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: site_control.py COMMAND PACKAGE [original options]")
    package = Path(sys.argv[2]).resolve()
    plan = C.verify(package)
    here = Path(__file__).resolve()
    if here != package / "readiness/site_control.py" or sha(here) != plan.get(
        "admission_control_sha256"
    ):
        raise RuntimeError("Executing admission entry differs")
    if (
        sha(here.with_name("site_trust.py")) != plan.get("site_trust_sha256")
        or plan.get("site_trust_policy") != T.POLICY
    ):
        raise RuntimeError("Executing trust policy differs")
    T.install()
    C.site_check = submission_site_check
    if sys.argv[1] == "site-check":
        site_check(package)
        return
    C.main()


if __name__ == "__main__":
    main()
