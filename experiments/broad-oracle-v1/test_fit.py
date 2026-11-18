"""Pure STOP leaves must separate failures, including zero-gain interactions."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_broad import FEATURES, frontier_tree, predict, tree  # noqa: E402


def test_interaction_tree_and_missing_values():
    x = np.zeros((5, len(FEATURES)))
    x[:, 1] = [1, 1, 2, 2, 3]
    x[:, 2] = [1, 2, 1, 2, 1]
    x[:, 3:] = np.nan
    y = np.array([False, True, True, False, False])
    root = tree(x, y, np.ones(5))
    assert [predict(root, [None if np.isnan(v) else v for v in row]) for row in x] == y.tolist()


def test_balanced_crossover_schedule():
    # One family per reader/rotation, four samples per family, spread across time.
    for ti in range(7):
        cells = [
            (5 * rotation + 3 * reader + ti) % 12 for rotation in range(12) for reader in range(4)
        ]
        assert all(cells.count(f) == 4 for f in range(12))
        for reader in range(4):
            assert len({(5 * r + 3 * reader + ti) % 12 for r in range(12)}) == 12
        for family in range(12):
            assert (
                sum(
                    (5 * r + 3 * reader + ti) % 12 == family
                    for r in range(6)
                    for reader in range(4)
                )
                == 2
            )


def test_frontier_tree_is_exact_on_hindsight_cohort_without_ids():
    x = np.zeros((101, len(FEATURES)))
    x[:, 8] = np.linspace(0.25, 0.75, len(x))
    y = np.arange(len(x)) % 3 == 0
    root = frontier_tree(x, y)
    assert [predict(root, row) for row in x] == y.tolist()
    assert "query" not in str(root) and "frontier_distance" in str(root)
    x[1, 8] = x[0, 8]
    assert frontier_tree(x, y) is None
