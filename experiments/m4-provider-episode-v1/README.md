# Prepared M4 provider episode

The concrete [approval packet](APPROVAL.md) and [protocol](PROTOCOL.md) define the new
six-request/$15 episode. Generation is disabled pending explicit user approval. All six scalar
filters plus unfiltered remain fixed; exact search is scoring only; validation/test are unopened.

Full artifacts are in
`trials/fannagent-benchmark-evaluation-v1/reviews-small/m4-episode-v1/` relative to the workspace.
Compact provenance/qualification copies are kept in `receipts/`.

- `preflight.py` performs official-document GETs and one authenticated account model lookup.
  It never sends development evidence or calls Messages.
- `episode.py` prepares the compact first request and pending authorization specification once
  into a fresh directory. It binds the qualified uncertainty evidence and preserves M2's point
  precision failure.
- `rehearse.py` runs the real bound evidence with a scripted transport and a network prohibition.
- `transport.py` verifies actual approval/source hashes, frozen parameters and one-attempt HTTP
  behavior. It preserves signed thinking/progress content and never persists credential headers.
- `run_episode.py` dispatches only after actual matched user approval and fresh provider GETs.
  It retains one durable transcript, uncertain reservations and all candidate/tool identities.
- `freeze.py` seals the qualified packet once; it never authorizes or dispatches it.

The controller extension separates operational bytes from the conservative financial input-token
ceiling and permits Anthropic's signed progress blocks in unchanged assistant history. Research
tools, quotas, policy language, scoring, causal work estimates, support masks and interval shortlist
rules are unchanged. The prior controller bytes from commit `9e8518a` are retained in the packet.
The prior M3 source binding and receipts remain immutable; the actual-bound no-network rehearsal
and 85-test regression qualify this transport preparation. Actual paid generation remains untested.

Reproduce checks from the `agent` directory using its existing virtual environment:

```sh
.venv/bin/ruff check experiments/m4-provider-episode-v1 experiments/filtered-ann-protocol-v2/fannproto/controller.py
.venv/bin/python -m pytest experiments/filtered-ann-protocol-v2/tests experiments/m4-provider-episode-v1/tests -q
```

The frozen rehearsal and preparation paths must not be overwritten. Use a fresh versioned path
for any amendment. A later approval record must match the final package hash and contract;
`prepared/approval-specification.json` deliberately has pending status and cannot enable dispatch.
