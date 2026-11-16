# M1 Torch kit: runtime, actual prefix labels and full serving costs

The starting state was committed first at `f96e02d`. This prepares one bounded original-graph
development allocation after verified M0 job23303080. The kit is **prepared, not run on Torch**.
Local synthetic results do not qualify original-graph semantics or establish performance.

Active kit: `trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/m1-runtime-qualification-v1.tar.gz`.
The full prospective [protocol](PROTOCOL.md) fixes450 development groups, all six scalar predicates
plus unfiltered, ef_search640, actual0..10 outputs, offline exact scoring only and no guard.
Validation/test remain unopened. No provider request or new agent policy is included.

The21 compiled v2 bindings cover the three historical transfer rules, matched continue-only
controls, partial/count and bare-prefix stops, bypass, dependency/null semantics and complete
feature/decision plan probes. With native and four legacy paths there are26 quality/work families
and23 timed families. Probe losses are reported; correct qualification does not require every
researcher fixed prefix to preserve recall. Historical transfer/native parity is required.

M1 rechecks all9,436 reached prefixes, including1,496 missing partial labels. The separate observer
module checks native graph work against M0, compatible-prefix/legacy/transfer graph parity,
all continue paths against native, per-query kernel CPU samples and compiler-derived heap-pass
masks. Instrumented times are excluded from the primary cost library.

Six timing blocks use four persistent backends pinned one per CPU. Every backend runs every
role in its block twice; each query/role sees all four CPUs once per mirrored cycle. Native and
applicable matched continue controls are paired within blocks, not pooled across unrelated
reader contexts. Four readers plus keeper fit the unchanged32-connection private server.

The frozen workload is984,396 attempts:899,346 in the timing/qualification phase and85,050 in
the observer phase, including781,200 measured requests,17,360 warmups and6,300 offline exact
references. The global cap is1,000,000; resources are four physical CPUs/48GiB/eight hours.
The6h15m/1h15m phase watchdogs leave staging headroom. No requeue or automatic retry is enabled.

`m1_verify.py` reconstructs every row, label, mask, source/module pin, role/CPU assignment,
timer/output and attempt. `m1_analyse.py` creates a paired complete-request cost library and
anonymous full-precision prefix evidence. Negative cost differences remain visible. The export
stays cost-unqualified until M2 validates/binds a surrogate; measured plan differences are not
pure operation timings or evidence of an unmeasured new rule's latency. M1 selects no policy.

Local checks include eight design/capability/source tests, timing and observer smokes on the
same synthetic8d graph across all seven conditions, an additional zero-result qualification,
and full verification/paired analysis of that actual synthetic return. Re-signed corrupt CPU,
order, missing-prefix, work-sample and wrong-module cases are rejected. Synthetic scope cannot
pass the production verifier. Loader-only checks use the actual frozen inherited package.
Full backend imports under both modules are mandatory on native Torch **before sbatch**.

The staging runtime/source manifests preserve failed local checks and all successful receipts.
The original search/runtime/kit freezes are unchanged. The deployment freeze binds the new kit,
profile, module/source hashes, workload, local readiness and pre-M1 checkpoint. Upload/submission,
status and collection instructions are in [COMMANDS.txt](COMMANDS.txt).

Rebuild preparation from the shared workspace using `build_runtime.py`, build both copied
engines in the pinned x86 image with `OPTFLAGS=` and the retained PG_CONFIG, then stage with
`package_kit.py`. Run `test_m1.py`, the synthetic M1 smoke phases and `check_local_return.py`.
Seal only after those pass using `seal_kit.py`. Each staging/sealing step requires a fresh path;
do not overwrite sealed inputs or failed evidence.

On return, verify the download hash and extract safely, run the packaged `m1_verify.py --results
RESULTS --kit KIT`, retain independent sacct completion evidence and both native preflight JSON
files, and run `m1_analyse.py` only after verification. Preserve negative or inconclusive timing
results without changing the frozen workload or opening protected data.
