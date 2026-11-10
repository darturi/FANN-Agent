"""Regression checks for mount-name recovery; no database or experiments."""

import copy
import unittest

import recover_campaign_identity as recovery


def strict(left, right):
    if left != right:
        raise ValueError("Reports differ")


class RecoveryTests(unittest.TestCase):
    canonical = "reviews-native-effort-v1-20261025T014743Z.p_kspq5v"

    def fixture(self):
        record = {
            "campaign": "/home/dar579/torch-reviews-results/" + self.canonical,
            "package": "/home/dar579/torch-native-effort-frontier-v1",
            "jobs": {"block-0": "101", "block-1": "102"},
            "dispatch": {
                "block-0": {"status": "submitted", "job_id": "101"},
                "block-1": {"status": "submitted", "job_id": "102"},
            },
        }
        exits = [{"job_id": "101", "exit_code": 0}, {"job_id": "102", "exit_code": 0}]
        proof = recovery.identity_proof(self.canonical, record, exits, recovery.MANIFEST)
        local = {
            "campaign": self.canonical,
            "package_manifest_sha256": recovery.MANIFEST,
            "gate": {"status": "measurement_inconclusive"},
            "value": 1.0,
        }
        remote = {**copy.deepcopy(local), "campaign": "results"}
        return record, exits, proof, local, remote

    def test_only_proven_mount_name_is_reconciled_without_mutation(self):
        _, _, proof, local, remote = self.fixture()
        before = copy.deepcopy(remote)
        receipt = recovery.reconcile(local, remote, proof, strict)
        self.assertTrue(receipt["all_other_discrete_fields_exact"])
        self.assertEqual(remote, before)

    def test_other_report_values_and_gate_changes_still_reject(self):
        for mutate in (
            lambda r: r.update(value=2.0),
            lambda r: r["gate"].update(status="pass"),
            lambda r: r.update(extra="unexplained"),
        ):
            _, _, proof, local, remote = self.fixture()
            mutate(remote)
            with self.assertRaises(ValueError):
                recovery.reconcile(local, remote, proof, strict)

    def test_arbitrary_alias_and_package_mismatch_reject(self):
        for change in ({"campaign": "other"}, {"package_manifest_sha256": "bad"}):
            _, _, proof, local, remote = self.fixture()
            with self.assertRaises(ValueError):
                recovery.reconcile(local, {**remote, **change}, proof, strict)

    def test_submission_and_completion_must_bind_exact_campaign(self):
        for change in ("campaign", "jobs", "package"):
            record, exits, _, _, _ = self.fixture()
            record[change] = "other" if change != "jobs" else {}
            with self.assertRaises(ValueError):
                recovery.identity_proof(self.canonical, record, exits, recovery.MANIFEST)
        record, exits, _, _, _ = self.fixture()
        exits[1]["job_id"] = "999"
        with self.assertRaises(ValueError):
            recovery.identity_proof(self.canonical, record, exits, recovery.MANIFEST)


if __name__ == "__main__":
    unittest.main()
