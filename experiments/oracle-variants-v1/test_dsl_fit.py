"""Compare the optimizer with exhaustive legal-rule masks on a small truth table."""

import itertools
import unittest

from dsl_fit import FEATURES, POINTS, fit_filter, gain, replay


def fixture():
    counts = {16: [1, 2, 3, None, 5], 32: [5, 4, 3, 2, 1], 64: [1, 1, 2, 2, 3]}
    distances = {
        16: [0.1, 0.2, 0.3, None, 0.5],
        32: [0.5, 0.4, 0.3, 0.2, 0.1],
        64: [0.1, 0.2, 0.3, 0.4, None],
    }
    safe = {
        16: [True, False, True, False, False],
        32: [False, True, False, True, False],
        64: [True, False, True, True, True],
    }
    rows = []
    for i in range(5):
        rows.append(
            {
                "id": "synthetic-" + str(i),
                "filter": -1,
                "role": "test",
                "native_recall": 0.8,
                "native_layer0_work": 12800,
                "observations": {
                    str(cp): {
                        FEATURES[0]: counts[cp][i],
                        FEATURES[1]: distances[cp][i],
                        FEATURES[2]: None,
                        FEATURES[3]: None,
                    }
                    for cp in POINTS
                },
                "actions": {
                    str(cp): {"recall": 0.8 if safe[cp][i] else 0.7, "layer0_work": cp * 64}
                    for cp in POINTS
                },
            }
        )
    return rows


def clause_masks(rows, cp):
    literals = []
    for name in FEATURES:
        values = sorted(
            {
                r["observations"][str(cp)][name]
                for r in rows
                if r["observations"][str(cp)][name] is not None
            }
        )
        for op, value in itertools.product(("<=", ">="), values):
            mask = 0
            for i, row in enumerate(rows):
                x = row["observations"][str(cp)][name]
                if x is not None and (x <= value if op == "<=" else x >= value):
                    mask |= 1 << i
            literals.append(mask)
    all_rows = (1 << len(rows)) - 1
    masks = {0, all_rows}  # absent clause and unconditional stop
    for count in range(1, 5):
        for selected in itertools.combinations(literals, count):
            mask = all_rows
            for literal in selected:
                mask &= literal
            masks.add(mask)
    return masks


def brute(rows):
    best = 0
    for masks in itertools.product(*(clause_masks(rows, cp) for cp in POINTS)):
        saved, valid = 0, True
        for i, row in enumerate(rows):
            for cp, mask in zip(POINTS, masks, strict=True):
                if mask & (1 << i):
                    if row["actions"][str(cp)]["recall"] < row["native_recall"]:
                        valid = False
                    else:
                        saved += gain(row, cp)
                    break
        if valid:
            best = max(best, saved)
    return best


class FitTests(unittest.TestCase):
    def test_exact_rule_language_and_first_stop(self):
        rows = fixture()
        policy, certificate = fit_filter(rows, "unfiltered", seconds=30)
        saved, _ = replay(policy, rows)
        self.assertEqual(saved, brute(rows))
        self.assertEqual(saved, certificate["work_saved_upper_bound"])
        self.assertTrue(certificate["work_optimality_proven"])
        self.assertFalse(certificate["latency_optimality_proven"])

    def test_unreached_actions_and_empty_policy(self):
        rows = fixture()
        for row in rows:
            row["actions"] = {}
            row["observations"] = {}
        policy, certificate = fit_filter(rows, "unfiltered", seconds=10)
        self.assertEqual(replay(policy, rows)[0], 0)
        self.assertTrue(certificate["work_optimality_proven"])


if __name__ == "__main__":
    unittest.main()
