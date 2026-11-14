# Common completion guard: implementation and qualification kit

The same `guarded_request` function wraps native and policy SQL execution. It validates count/shape, replaces a short response with exact filtered top-k, and returns both the initial and final identities. It never appends guessed neighbors, hides corrupt output behind fallback, uses cached truth as serving data, or special-cases query IDs/filters. `min(k,eligible_count)` handles small/empty eligible populations.

All persistent ANN/policy/exact connections import one exported repeatable-read snapshot from a keeper holding a SHARE lock. Exact readers force sequential scanning and use the same vector/predicate with deterministic distance/ID ordering. Connection/snapshot/map setup and warmups are separate from request time. The request timer includes construction, initial ANN/policy/continuation, initial decode/check, exact fallback when triggered, final decode and validation. Heavy truth/eligibility checks and raw logging run outside the timer. Initial/final outputs, fallback decisions and all timing components remain in raw records.

## Fixed experiment

The authoritative plan is `../protocol/completion-guard-plan-v1.json`. All450 development groups, all six scalar filters plus unfiltered, and the unchanged effort grid640/1000/2048/4096/8192 are included. No provider calls or validation/test inputs are present.

1. Qualify guarded native versus the identical agent execution path set to always continue, at every request/grid point:15,750 paired quality rows. Verify each initial output against the prior native sweep and each final output against verified exact references. A fresh exact query is always executed by serving fallback; old truth is only an external verifier.
2. Time native-A/native-B/noop-A/noop-B across two mirrored balanced epochs:126,000 measured requests, plus2,800 warmups. Use the fixed four-label Williams row, seed, rotated filter order and reversed effort order. Both A/B labels use the same guard and shared exact reader. Save every output and compare it to the qualified identity.
3. Select the adequate common native-guard setting with the lowest observed equal-six-filter request mean; within1% choose larger effort. Unfiltered remains a control. A/B ratios and no-stop overhead are development diagnostics on one allocation, not confirmatory causal latency claims. Save all candidate means and quality findings, including failures.
4. Recompute exact truth and qualify capture/forced-prefix/stop/continue semantics at the selected parent for all3,150 requests. Apply the common guard to historical policies and forced-stop probes. Verify local/shared features on ten groups/filter. These policies are probes, not a new generated agent. Future agent proposals must use the same guard and pass their own replay/live-policy qualification.
5. Verify data/index integrity, cleanup, resource events and the attempt ledger. Reconstruct the quality,126,000 timings, selection, and selected-parent policy output/scoring checks locally after return.

Budget:4 physical CPUs,48GiB,8 hours,225,000 ANN/exact attempts including warmups and qualification. The planned maximum observed-data attempt count is below this cap, including both branches of the guard. No automatic effort-grid expansion or statistical resubmission is allowed. No adequate guarded parent yields a preserved negative disposition rather than an agent call.

## Local evidence

- Seven unit checks passed: no fallback for complete output; short-result replacement and matching predicate/vector; empty/fewer-than-k populations; corruption rejection; failed exact completion; cap-before-fallback dispatch; timer accounting.
- Real PostgreSQL synthetic8-dimensional smoke passed all seven conditions on native and no-stop policy connections, with both forced-short (`ef_search=2`, fixture only) and full (`8192`) responses. It verifies shared exported snapshot import, exact completion, output/guard parity, checkpoint/forced-stop parity and wrong-map rejection. This is not original-graph qualification or performance evidence.
- The unchanged extended-effort C module is reused from the prior sealed parent kit. Only Python serving/orchestration code changes in this stage. No historical engine, graph or result is overwritten.
- Python/shell syntax and the sealed inherited package's all-development query-vector inventory are checked before delivery.

## Delivery and completion

Active kit: `../kits/guard-qualification-v1.tar.gz`; instructions: `../kits/GUARD-COMMANDS.txt`. Keep old native-only results as valid negatives. The guard is a researcher-designed common hybrid baseline component, not an agent-generated improvement and not unmodified native execution. Recall requirements remain unchanged; a complete result can still have low recall. No readiness/benefit claim is made until the actual Torch return is independently verified. The selected parent and common guard must be pinned in the subsequent agent/policy comparison freeze.
