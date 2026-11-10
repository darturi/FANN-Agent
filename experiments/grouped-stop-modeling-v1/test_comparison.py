"""Synthetic correctness/leakage tests; no original-data modeling."""

import socket
import subprocess
import unittest

import common
import numpy as np
from common import digest, load_api
from compare import inner_assignment, select
from data import FILTERS, GRID, Data, outcomes, training_data
from models import (
    canonical_split,
    first_actions,
    fit,
    grid_scores,
    leaf_groups,
    shallow_policy,
    split_mask,
    verify_shared_interpreter,
)
from stats import Bootstrap, assess
from threadpoolctl import threadpool_limits


def fixture():
    groups = [f"g{g:02d}" for g in range(24)]
    meta = [
        {
            "query_id": g + "-" + f,
            "group": g,
            "stratum": f,
            "native_recall": 1.0,
            "native_work": 1000,
        }
        for g in groups
        for f in FILTERS
    ]
    names = {"static23": ["checkpoint_index", "frontier_distance_min"]}
    x = np.array([[[cp, i / 1000] for cp in GRID] for i in range(len(meta))], dtype=float)
    reached = np.ones((len(meta), 8), dtype=bool)
    labels = {
        k: np.zeros((len(meta), 9))
        for k in ["recall", "valid", "count", "activation", "reuse", "work"]
    }
    labels["recall"][:] = 1.0
    labels["valid"][:] = 1.0
    labels["count"][:] = 10
    labels["recall"][:, :2] = 0.5
    labels["activation"][:, :8] = np.array([6, 5, 4, 3, 2, 1, 0.5, 0.1])
    labels["reuse"][:, :8] = labels["activation"][:, :8]
    labels["activation"][:, 8] = -0.2
    labels["reuse"][:, 8] = -0.1
    labels["work"][:] = 100
    full = np.array([[cp, i / 1000] for i in range(len(meta)) for cp in range(1, 129)], dtype=float)
    return Data(
        meta,
        {g: i % 5 for i, g in enumerate(groups)},
        {"checkpoint_index": {"kind": "int"}, "frontier_distance_min": {"kind": "float"}},
        names,
        {"static23": x},
        {"static23": full},
        [(128 * i, 128 * (i + 1)) for i in range(len(meta))],
        reached,
        {"static23": labels},
    )


class Correctness(unittest.TestCase):
    def setUp(self):
        self.data = fixture()
        self.groups = sorted(self.data.folds)

    def test_group_indices_keep_filters_together(self):
        ix = self.data.indices(self.groups[:8])
        self.assertEqual(len(ix), 24)
        self.assertEqual({self.data.meta[i]["group"] for i in ix}, set(self.groups[:8]))
        with self.assertRaises(ValueError):
            self.data.indices(["unassigned"])

    def test_vector_weighting_and_target_penalties(self):
        x, y, w, ids, _ = training_data(self.data, "static23", self.groups[:16], 320.0)
        self.assertEqual(len(x), 16 * 3 * 8)
        self.assertAlmostEqual(float(w.sum()), 16.0)
        self.assertLess(y[0], -100.0)
        self.data.labels["static23"]["valid"][0, 0] = 0
        _, bad, _, _, _ = training_data(self.data, "static23", self.groups[:16], 320.0)
        self.assertAlmostEqual(float(y[0] - bad[0]), 1000.0)

    def test_first_action_is_earliest_not_best_future_score(self):
        s = np.array([[-1, 0.1, 99.0, -1, -1, -1, -1, -1], [-1.0] * 8])
        self.assertEqual(first_actions(s, 0).tolist(), [1, 8])

    def test_unreachable_outcome_is_rejected(self):
        self.data.reached[0, 7] = False
        with self.assertRaises(ValueError):
            outcomes(self.data, "static23", np.array([0]), [7])
        self.assertIsNone(outcomes(self.data, "static23", np.array([0]), [8])[0]["checkpoint"])

    def test_measured_continue_retains_its_negative_cost(self):
        r = outcomes(self.data, "static23", np.array([0]), [8])[0]
        self.assertEqual(r["activation_proxy_ms_saved"], -0.2)
        self.assertEqual(r["reuse_proxy_ms_saved"], -0.1)

    def test_float32_split_midpoints_match_prediction_rounding(self):
        for threshold in [-0.1, 0.0, 0.1, 1 / 3, 1.0, 2**25 + 3.0]:
            op, cut = canonical_split(threshold, "float")
            candidates = np.array(
                [
                    np.nextafter(cut, -np.inf),
                    cut,
                    np.nextafter(cut, np.inf),
                    threshold - 1,
                    threshold + 1,
                ]
            )
            wanted = candidates.astype(np.float32).astype(np.float64) <= threshold
            actual = split_mask({"feature": 0, "op": op, "cut": cut}, candidates[:, None])
            np.testing.assert_array_equal(actual, wanted)

    def test_integer_split_partition_and_boolean(self):
        for threshold in [0.5, 3.2, 2**25 + 3.0]:
            op, cut = canonical_split(threshold, "int")
            candidates = np.array([cut - 1, cut, cut + 1], dtype=float)
            wanted = candidates.astype(np.float32).astype(np.float64) <= threshold
            np.testing.assert_array_equal(
                split_mask({"feature": 0, "op": op, "cut": cut}, candidates[:, None]), wanted
            )
        self.assertEqual(canonical_split(0.5, "bool"), ("bool_false", None))

    def test_heldout_outcomes_cannot_change_fitted_model(self):
        train = self.groups[:16]
        a, _ = fit(self.data, "static23", "shallow_tree", train, 320.0)
        self.data.labels["static23"]["activation"][48:] = 9000
        self.data.labels["static23"]["recall"][48:] = 0
        b, _ = fit(self.data, "static23", "shallow_tree", train, 320.0)
        self.assertEqual(digest(a), digest(b))

    def test_group_pruning_and_shared_interpreter_parity(self):
        model, receipt = fit(self.data, "static23", "shallow_tree", self.groups[:16], 320.0)
        self.assertGreaterEqual(min(leaf_groups(model["trees"][0])), 8)
        held = self.data.indices(self.groups[16:])
        expected = first_actions(grid_scores(self.data, "static23", model, held), 0.0)
        raw = shallow_policy(model, 0.0)
        result = verify_shared_interpreter(self.data, "static23", raw, held, expected, load_api())
        self.assertEqual(result["cases"], 24)
        self.assertTrue(receipt["unpruned_sklearn_prediction_parity"])

    def test_forest_is_diagnostic_not_shallow_export(self):
        model, receipt = fit(self.data, "static23", "extra_trees", self.groups[:16], 320.0)
        self.assertEqual(receipt["individual_trees"], 64)
        self.assertGreaterEqual(min(min(leaf_groups(t)) for t in model["trees"]), 8)
        with self.assertRaises(ValueError):
            shallow_policy(model, 0.0)

    def test_inner_groups_disjoint_and_deterministic(self):
        train = self.groups[:20]
        assignment = inner_assignment(train, 0)
        self.assertEqual(assignment, inner_assignment(list(reversed(train)), 0))
        for fold in range(4):
            fit_groups = {g for g in train if assignment[g] != fold}
            val = {g for g in train if assignment[g] == fold}
            self.assertFalse(fit_groups & val)
            self.assertEqual(fit_groups | val, set(train))
            self.assertFalse((fit_groups | val) & set(self.groups[20:]))

    def test_selection_rejects_failed_candidate_and_uses_frozen_ties(self):
        def trial(risk, threshold, passes, utility):
            return {
                "risk": risk,
                "threshold_ms": threshold,
                "assessment": {"development_signal": passes, "utility_proxy_ms": utility},
            }

        self.assertIsNone(select([trial(20, 0, False, 100)]))
        choices = [
            trial(20, 0, True, 1),
            trial(80, 0.1, True, 1),
            trial(80, 0.5, True, 1),
            trial(1280, 0, False, 100),
        ]
        self.assertEqual(select(choices)["threshold_ms"], 0.5)

    def test_bootstrap_unit_and_invalid_outcomes(self):
        ix = self.data.indices(self.groups)
        rs = outcomes(self.data, "static23", ix, np.full(len(ix), 8))
        boot = Bootstrap(self.groups, samples=100)
        result = assess(rs, boot)
        self.assertEqual(result["overall"]["independent_vectors"], 24)
        self.assertFalse(result["development_signal"])
        with self.assertRaises(ValueError):
            assess(rs + rs[:1], boot)
        rs[0]["valid"] = False
        self.assertFalse(assess(rs, boot)["development_recall_pass"])

    def test_zz_offline_boundaries_block_network_subprocess_and_unassigned_evidence(self):
        common.offline_guard()
        with self.assertRaises(RuntimeError):
            socket.getaddrinfo("example.com", 443)
        with self.assertRaises(RuntimeError):
            subprocess.run(["true"], check=True)
        with self.assertRaises(RuntimeError):
            open(
                common.ROOT
                / "trials/torch-reviews-results/feature-data-ablation-v1"
                / "torch-feature-data-ablation-v1/inputs/evaluation.jsonl"
            )
        with self.assertRaises(RuntimeError):
            open(common.ROOT / "research/fannagent-p3a-evidence-audit-2026-10-24/audit.json", "w")


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        unittest.main()
