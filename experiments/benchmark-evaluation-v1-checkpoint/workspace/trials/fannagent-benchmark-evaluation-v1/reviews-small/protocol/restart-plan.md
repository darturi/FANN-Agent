# Fresh policy-generation episode on the frozen Small Reviews split

Status: split and study protocol frozen; local all-filter module smoke passed; original-graph runtime qualification and provider episode pending. Authoritative protocol: `study-protocol.md`, `config.json`, and `../freeze/protocol-freeze-v2.json`. This plan records the authorized refactor and its data boundaries. It is not an executed episode or a completed statistical protocol.

## Fixed inputs and roles

Use `../freeze/split-freeze.json` and its pinned `../splits/split-manifest.json`: 450 development / 150 validation / 275 test / 125 excluded historical groups. Include six published scalar filters and an unfiltered control at k=10, subject to development-only runtime qualification. Any unsupported scope must be resolved before validation selection and test outcomes.

`../prepare_development.py` verifies the split and evidence hashes and exports 3,150 canonical semantic query requests under `../development/inputs/`. The field `totalvotes` must be mapped to the qualified engine schema explicitly. Do not directly run the historical `rb_plan.py` against the new workload: it pins 200 vectors, three predicates and the old schedule. Keep that historical experiment intact; adapt its qualified runtime behind a new split-aware input path.

Do not attach the private original study file, frozen full catalog, validation/test request values, held-out labels or held-out outcomes to the agent's generation context. Build the episode input bundle from the development allowlist. Validate imported traces/results against that allowlist before producing agent feedback. The exported semantic requests still require runtime normalization/formatter and exact-scoring qualification.

## Episode procedure

1. Finalize `study-protocol.md` and machine-readable episode configuration before searches/provider requests. Resolve recall floor and noninferiority inference, fixed-workload versus population claims, per-filter weighting/multiplicity, timing endpoint/control rules, baseline candidate grids, selection/ties/fallback, precision/replications, exact model/version and usage reconciliation. The test's zero-loss 95% upper loss-probability bound is about 1.0834%; do not claim that this alone establishes a 0.25 percentage point population recall margin.
2. Qualify the reused original-graph checkpoint/continuation/shared-lookup path and metadata mapping on development data across the intended predicates. Preserve prior modules, graph identities and historical results. Measure complete serving cost and setup separately.
3. Run a fresh agent invocation with development-only features, traces, exact/native outcomes and measured costs. Record the prompt, tools, model/version, every proposal, manual change, tokens and dollars. Use vector-group folds within development. Freeze up to three proposal rounds and a $15 ceiling in the final episode configuration after reconciling usage; these remain the roadmap's planning values until that configuration is complete. User authorization for the restart is already recorded; this does not require another routine approval step.
4. Tune native and simple baselines using the same development boundaries and a prespecified effort allowance. Keep the old checkpoint policy as a historical comparator; do not let it substitute for the requested new episode.
5. Before validation, freeze the complete proposal pool, baseline candidate pool and deterministic selection/scoring/tie rules. Evaluate that fixed pool in one bounded validation batch. Do not revise proposals or run further model rounds using validation feedback. Retain failed candidates and a negative-selection/native-fallback outcome if none qualifies.
6. Before test, freeze every selected policy and baseline, execution features, input identities, engine/graph/module versions, analysis, timing schedule and replication count. The 275 test groups may then support the one frozen comparison. No test-driven candidate revision belongs to this version.

## Evidence and delivery

Keep episode provenance under `development/`, validation selection under `validation/`, immutable policy/analysis seals under `freeze/`, and kits/returns/reports in their roadmap directories. Publish every selected candidate's outcome and preserve unsuccessful runs. The split is already frozen; subsequent changes require a versioned replacement with a reason and exposure ledger, never silent overwriting.

Completed in this refactor: reservation review, split/catalog freeze, input/export checks, roadmap update. No new policy-generation calls, ANN/exact searches, validation selections or remote allocations have run.
