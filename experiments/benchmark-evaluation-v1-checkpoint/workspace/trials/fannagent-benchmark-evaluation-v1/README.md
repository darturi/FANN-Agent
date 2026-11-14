# FANNAgent benchmark evaluation v1

The clean restart split is frozen following the November 10, 2026 reservation review:

| Role | Independent groups |
| --- | ---: |
| Development | 450 |
| Validation | 150 |
| Test | 275 |
| Excluded historical | 125 |

The 37 late “reserved” groups already have prior outcomes and remain development. The original 300 protected calibration/test groups were recovered using broker state, execution summaries, and saved outcome-identity checks. This conclusion is conditional on recorded local history.

Authoritative artifacts:

- [Reservation review](inventory/reservation-review.md) and [machine-readable evidence](inventory/reservation-audit.json).
- [Frozen split](reviews-small/splits/split-manifest.json), [seal](reviews-small/freeze/split-freeze.json), and [verification](reviews-small/splits/verification.json).
- [Restart procedure](reviews-small/protocol/restart-plan.md).
- Development-only exporter: `reviews-small/prepare_development.py`; exported inputs under `reviews-small/development/inputs/`.

The earlier 25/100 proposal is superseded and preserved under `inventory/snapshots/phase0-provisional/`. Inventory-root provisional files are historical; use the authoritative study split above.

Phase 1 protocol is finalized: see [study protocol](reviews-small/protocol/study-protocol.md) and [active seal](reviews-small/freeze/protocol-freeze-v2.json). All seven synthetic PostgreSQL smoke conditions and eight focused checks passed. Original-graph development qualification is pending the user-run Torch kit: [commands](reviews-small/kits/COMMANDS.txt), [runtime status](reviews-small/runtime/qualification-status.md). Next: collect and independently verify that return, reconcile provider usage, then run the fresh agent episode. Test outcomes remain unopened. At 275 zero-loss test groups the one-sided 95% upper loss-probability bound is approximately 1.0834%; no universal or 0.25 percentage point population recall guarantee follows.

November 11 update: [job22635567 verified](reviews-small/reports/native640-qualification-22635567.md), all 3,150 records and 7,940 forced outputs reconstructed. Native640 fails scientific adequacy in three filters. The user chose to retain all filters and strengthen the parent. Active next job: [parent sweep and requalification](reviews-small/protocol/parent-requalification-plan-v1.json), [commands](reviews-small/kits/PARENT-COMMANDS.txt). No agent calls dispatched.

November 11 stronger-parent follow-up: [job22643346 sweep verified](reviews-small/reports/parent-sweep-22643346.md), all15,750 observations. No native-only setting meets completeness; one votes743 query returns8/10 at8192. Recommended next: a common exact completion guard, qualified/measured identically for native and agent paths. No further grid expansion, provider call or holdout access.

Common-guard implementation/kit ready: [runtime](reviews-small/runtime-guard-v1/README.md), [prospective amendment](reviews-small/protocol/completion-guard-amendment-v1.md), [Torch commands](reviews-small/kits/GUARD-COMMANDS.txt). Seven unit checks and seven-condition native/no-op PostgreSQL guard smoke passed. Original-graph guard qualification, development timing and parent selection remain pending; no new jobs/model calls or holdout access.

November12: [guard return verified and parent640 selected](reviews-small/reports/guard-qualification-22684501.md),18.8723ms equal scalar mean, all recall/completeness gates pass. Fresh episode prepared with anonymized development evidence; paid dispatch was rejected by automatic approval review pending explicit payload/destination approval. [Disclosure/preview](reviews-small/development/agent-episode-v1/egress-review.json). No paid model call or holdout outcome access.

November12 final episode disposition: explicit external-payload approval recorded; fresh Anthropic call completed at$0.561208 and returned an empty policy list. The predeclared driver stopped on abstention; no further paid round or held-out outcome access. [Episode report](reviews-small/reports/agent-episode-v1-2026-11-12.md). Guarded native640 is retained; no new policy selected.

November12 compact/tool continuation: the user authorized the remaining two requests under the original cap. [Verified continuation](reviews-small/reports/agent-compact-continuation-2026-11-12.md) produced three distinct development-replay eligible policies among five distinct authored programs. All3,150 cases per program were checked; all six filters remain included, validation/test untouched. Three total requests cost$0.725544; no request remains. Leading prose in the final response required a recorded single-JSON-fence envelope recovery, with the original rejection retained. [Frozen eligible programs](reviews-small/development/agent-episode-v2-compact/eligible-policies.json) await compilation and live development qualification/timing; surrogate costs do not select a final policy.

November12 compiled-policy kit: all three eligible programs compiled unchanged; local C replay on9,450 cases, seven-condition PostgreSQL synthetic smoke, guard unit checks and synthetic return-verifier checks pass. [Runtime](reviews-small/runtime-agent-v1/README.md), [development amendment](reviews-small/protocol/agent-policy-qualification-amendment-v1.md), [Torch commands](reviews-small/kits/AGENT-COMMANDS.txt). Fixed job:3,150 qualification rows,50,400 timing requests,1,120 warmups;4 CPUs/48GiB/8 hours/160,000 attempts. Sealed archive agent-policy-qualification-v1.tar.gz is ready; original-graph qualification and actual serving-cost evidence remain pending. All six filters retained, validation/test untouched, no provider calls.

November13: [job22928562 verified](reviews-small/reports/agent-policy-qualification-22928562.md), all9,450 policy cases/50,400 timings/1,120 warmups/81,456 attempts. Three quality passes, zero recall losses. broad_c_fixed leads development at18.659077ms versus native19.274893ms (3.19% reduction), below the5% practical target and with A/B limitations. Development nominee only; all three eligible programs retained. Recommend prepare/seal complete comparators and one bounded validation batch; no holdouts opened and no further provider calls. [Disposition](reviews-small/freeze/agent-development-assessment-v1.json).

November13 primary redesign: user-directed removal of serving exact completion. Exact search is offline recall scoring only; short answers remain actual outputs and missing neighbors lower recall. The95% absolute recall floor is diagnostic, while zero individual losses vsraw native640 remains the preservation gate. [Revised protocol](reviews-small/protocol/study-protocol-unguarded-v1.md), [rescore/redesign](reviews-small/reports/unguarded-redesign-2026-11-13.md), [new Torch commands](reviews-small/kits/UNGUARDED-COMMANDS.txt). Native40/80/160/320/640 +noop +three unchanged policies;113,400 real unguarded timings, all six filters and450 development groups. Guarded reports remain historical hybrid evidence; unguarded timing pending. No new provider call or validation/test access.

November13: [unguarded job23045686 verified](reviews-small/reports/unguarded-development-23045686.md):28,350 quality outputs/113,400 timings/2,520 warmups/150,570 attempts;3,150 offline exact references and ZERO serving exact calls. All three policies preserve raw native recall; short outputs retained. Conservative is nominal leader at10.873694ms versus native64011.820408ms, but large A/B effects and a6.54% faster noop make performance attribution inconclusive. Recommend one bounded unchanged-policy reader/CPU/order diagnostic before validation. All six filters retained, no holdouts opened or new provider calls. [Disposition](reviews-small/freeze/unguarded-development-assessment-v1.json).

November13: [single reader/CPU/work diagnostic sealed](reviews-small/protocol/reader-attribution-v1.md), [commands](reviews-small/kits/ATTRIBUTION-COMMANDS.txt). Original-module630,000 timings use complete backend/CPU role crossover; separate15,750 work probes never contribute instrumented times. Fixed684,950 attempts,4 CPUs/48GiB/8h; all six filters retained, exact only offline, no holdouts or provider calls. Local schedule, two-module SQL/CPU smokes and full-size verifier/corruption/analysis checks pass. [Current agent performance disposition](reviews-small/reports/agent-performance-disposition-2026-11-13.md): recall preservation passes on development; robust net latency success is unestablished, and a1ms difference may be variation/context effects. Do not presume an agent win or failure from it. No new Torch job launched here.
