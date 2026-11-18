"""Check schedule balance, recall semantics and independent corruption rejection."""

import json
import math
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle_design import FAMILIES, qualifies, schedule, validate_output


def test_schedule_balances_each_query_across_readers_and_cycles():
    cases = [{"id": f"q-v{i}-votes32"} for i in range(11)]
    rows = list(schedule(cases, 6))
    cells = Counter((q["id"], r, cycle, family) for cycle, _, r, family, q in rows)
    assert len(rows) == 11 * 32
    assert set(cells.values()) == {1}
    assert all(
        Counter(family for _, _, rr, family, _ in rows if rr == r) == {f: 22 for f in FAMILIES}
        for r in range(4)
    )


def test_recall_is_not_normalized_by_returned_count():
    truth = [[i, 0.2] for i in range(10)]
    assert validate_output(truth[:7], set(range(20)), truth) == 0.7


def test_short_native_output_keeps_its_count_and_recall():
    native = [[i, 0.2] for i in range(8)]
    assert qualifies(native, 0.8, native, 0.8)
    assert not qualifies(native[:7], 0.8, native, 0.8)
    assert not qualifies(native, 0.7, native, 0.8)


@pytest.mark.parametrize("distance", [math.nan, math.inf, -math.inf, 3.0])
def test_invalid_distance_fails(distance):
    with pytest.raises(ValueError, match="invalid"):
        validate_output([[0, distance]], {0}, [[0, 0.1]])


def test_empty_population_requires_empty_answer():
    assert validate_output([], set(), []) == 1
    with pytest.raises(ValueError):
        validate_output([[1, 0.1]], set(), [])


def test_result_eligibility_and_duplicate_ids():
    with pytest.raises(ValueError):
        validate_output([[99, 0.1]], {1, 2}, [[1, 0.1], [2, 0.2]])
    with pytest.raises(ValueError):
        validate_output([[1, 0.1], [1, 0.1]], {1, 2}, [[1, 0.1], [2, 0.2]])


def test_dense_stops_need_not_be_powers_of_two():
    native = [[i, 0.1] for i in range(10)]
    recalls = [0.1, 0.9, 1.0, 0.7, 1.0]
    first = next(
        cp for cp, recall in enumerate(recalls, 1) if qualifies(native, recall, native, 1.0)
    )
    assert first == 3


def test_independent_verifier_detects_corrupted_raw_file(tmp_path):
    from analyse import verify

    kit, result = tmp_path / "kit", tmp_path / "result"
    kit.mkdir()
    result.mkdir()
    (kit / "queries.jsonl").write_text('{"id":"a"}\n')
    (kit / "query-roles.json").write_text('{"a":"test"}')
    (result / "receipt.json").write_text(json.dumps({"raw_sha256": {"quality.jsonl": "wrong"}}))
    (result / "quality.jsonl").write_text("corrupted")
    with pytest.raises(ValueError, match="changed raw evidence"):
        verify(result, kit, fixture=True)
