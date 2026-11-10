# B2b catalog serialization correction

Separate prospective repair of `exact-topk-v1`; original source/package/design/receipt/binding/reservation remain unchanged. See the [frozen addendum](../../../research/fannagent-exact-topk-v1-catalog-fix-design-2026-10-26.md) and original [scientific design](../../../research/fannagent-exact-topk-v1-design-2026-10-25.md).

PostgreSQL17 `to_jsonb(oid)` produces text. The original integer mock hid a false rejection of the correct graph ID. This correction expects the exact text `"264013"` and retains every other graph check, the unchanged catalog SQL, data/graph/module hashes and all scientific gates. Wrong IDs/types remain rejected. The first rejected raw catalog and timer are saved before failure; progress names initial catalog qualification.

Local tests are source-backed unit/mocked contract checks. A temporary PostgreSQL16 scalar fixture could not initialize under the sandbox shared-memory restrictions; no native runtime or ANN correctness is inferred. No benchmark/native search, fit, provider or Torch run is performed locally.

The original failed raw archive must first be collected, downloaded and independently reviewed. Corrected submission checks the pinned original package/binding/campaign/job, zero-search catalog failure, cleanup, protected source hashes, terminal FAILED accounting and collected archive checksum. A mismatch stops before submission. The original allowance remains consumed. This correction allows one separately named allocation with the original 4CPU/32GiB/2h,6,600s/40,230-search maxima; no retry.

```sh
cd /Users/danielarturi/Developer/JinyangLiWork
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python -m unittest discover \
  -s agent/experiments/exact-topk-v1-catalog-fix -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/exact-topk-v1-catalog-fix/experiment.py package
```

Commands will be released after raw review. Native semantic/catalog/plan/quality/A/A/economic gates remain unassessed. Retain original execution and prior scientific verdicts.
