"""Durable reservations cover crashes, unused slots and source charges."""

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(
    0, str(ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1")
)
from timing_followup import (  # noqa: E402
    WindowLedger,
    source_lines,
)


def test_reserves_before_queries_and_retains_uncertain_slots(tmp_path):
    ledger = WindowLedger(tmp_path, 100, window=8, cap=200)
    counter = Counter(total=100)
    ledger.reserve(counter, "ann")
    saved = json.loads((tmp_path / "reservation.json").read_text())
    assert saved["actual_total_at_reservation"] == 100
    assert saved["reserved_total"] == 108 >= counter["total"]
    assert ledger.reservations == 1
    for _ in range(7):
        ledger.reserve(counter, "ann")
    assert ledger.reservations == 1
    ledger.reserve(counter, "ann")
    assert ledger.reservations == 2
    ledger.finish(counter)
    final = json.loads((tmp_path / "reservation-final.json").read_text())
    assert final["actual_total"] == 109
    assert final["charged_total"] == 116
    assert final["unused_charged"] == 7


def test_source_charges_cannot_be_reset_or_exceed_global_cap(tmp_path):
    ledger = WindowLedger(tmp_path, 97, window=8, cap=100)
    with pytest.raises(ValueError, match="ceiling"):
        ledger.reserve(Counter(total=0), "ann")
    counter = Counter(total=97)
    for _ in range(3):
        ledger.reserve(counter, "ann")
    with pytest.raises(ValueError, match="ceiling"):
        ledger.reserve(counter, "ann")
    assert json.loads((tmp_path / "reservation.json").read_text())["reserved_total"] == 100


def test_only_declared_unterminated_final_record_can_be_interrupted(tmp_path):
    path = tmp_path / "prefixes.jsonl"
    path.write_text('{"id":"complete"}\n{"id":')
    with pytest.raises(ValueError, match="corrupt"):
        list(source_lines(path))
    assert list(source_lines(path, [path.name])) == [{"id": "complete"}]
    path.write_text('{"id":\n{"id":"later"}\n')
    with pytest.raises(ValueError, match="corrupt"):
        list(source_lines(path, [path.name]))
