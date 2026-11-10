# A3 exact-vector offline prototype

The A3 remedy decision selects binary64 vector bytes with exact original integer
categories/values, plus canonical-identity and bounded JSON sample adapters.
This isolated prototype reuses the actual frozen Snapshot constructor and consumer
functions. All33 local checks pass; original A2 source/seal/evidence and128+128
native receipts remain unchanged.

It has no native producer, backend/controller or Torch commands. It does not
qualify target3.12.15, native memory, savings or full B2f. More than64 fixture rows
are rejected by its fixture identity scope. Internal vector type/mutability changes
explicitly; arbitrary list or third-party API equivalence is not claimed.

[Decision and next gates](../../../research/fannagent-startup-exact-vector-A3-decision-2026-10-30.md),
[pre-code freeze](../../../trials/torch-reviews-startup-exact-vector-v1/A3-FREEZE.json),
[guarded receipt](../../../trials/torch-reviews-startup-exact-vector-v1/local-checks.json).

The guarded runner creates local-checks.json exclusively to preserve evidence.
For repeatable consumer-only tests without overwriting it:

```sh
cd /Users/danielarturi/Developer/JinyangLiWork
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python -B -m unittest discover \
  -s agent/experiments/startup-exact-vector-v1 -p 'test_*.py' -v
```
