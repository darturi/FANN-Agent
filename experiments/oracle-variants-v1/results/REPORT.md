# Hindsight oracle comparison

All results use the original 247,286-row cosine graph, k=10, native ef=640, and iterative scans off. Every reported policy preserves native Recall@10 on every case in its intended cohort. Each cohort's feasible policy was fitted using that cohort's outcomes. This is a hindsight capability diagnostic.

## All seven conditions

| Cohort | Native ms | Variant | Oracle ms | Savings | Conditional 95% interval |
| --- | ---: | --- | ---: | ---: | ---: |
| full_workload | 17.1000 | `oracle_ideal` | 5.4300 | 68.25% | [67.38%, 69.11%] |
| full_workload | 17.1000 | `oracle_constrained` | 7.6743 | 55.12% | [53.93%, 56.31%] |
| full_workload | 17.1000 | `oracle_feasible` | 14.0256 | 17.98% | [16.77%, 19.21%] |
| heldout_test | 16.9361 | `oracle_ideal` | 5.5001 | 67.52% | [65.81%, 69.20%] |
| heldout_test | 16.9361 | `oracle_constrained` | 7.6773 | 54.67% | [52.40%, 56.89%] |
| heldout_test | 16.9361 | `oracle_feasible` | 12.3300 | 27.20% | [24.89%, 29.55%] |

## Six filtered conditions (primary)

| Cohort | Native ms | Variant | Oracle ms | Savings | Conditional 95% interval |
| --- | ---: | --- | ---: | ---: | ---: |
| full_workload | 17.0622 | `oracle_ideal` | 5.9660 | 65.03% | [64.07%, 65.99%] |
| full_workload | 17.0622 | `oracle_constrained` | 8.3351 | 51.15% | [49.81%, 52.50%] |
| full_workload | 17.0622 | `oracle_feasible` | 14.8758 | 12.81% | [11.51%, 14.12%] |
| heldout_test | 16.9081 | `oracle_ideal` | 6.0522 | 64.21% | [62.29%, 66.06%] |
| heldout_test | 16.9081 | `oracle_constrained` | 8.3438 | 50.65% | [48.08%, 53.17%] |
| heldout_test | 16.9081 | `oracle_feasible` | 13.2543 | 21.61% | [18.97%, 24.29%] |

## Per-condition savings: full_workload

| Condition | Native ms | Ideal | Constrained | Feasible |
| --- | ---: | ---: | ---: | ---: |
| Unfiltered | 17.3265 | 87.22% | 78.59% | 48.49% |
| Votes ≥ 743 | 17.1684 | 64.18% | 49.92% | 0.96% |
| Votes ≥ 527 | 16.9055 | 54.14% | 37.20% | 2.61% |
| Votes ≥ 310 | 16.4473 | 52.97% | 36.46% | 7.07% |
| Votes ≥ 192 | 16.9217 | 62.79% | 48.56% | 11.27% |
| Votes ≥ 108 | 17.1939 | 72.21% | 60.13% | 20.23% |
| Votes ≥ 32 | 17.7366 | 82.62% | 73.02% | 33.63% |

## Per-condition savings: heldout_test

| Condition | Native ms | Ideal | Constrained | Feasible |
| --- | ---: | ---: | ---: | ---: |
| Unfiltered | 17.1037 | 87.21% | 78.49% | 60.34% |
| Votes ≥ 743 | 17.1145 | 63.16% | 49.98% | 5.17% |
| Votes ≥ 527 | 16.7957 | 52.99% | 37.46% | 5.80% |
| Votes ≥ 310 | 16.1032 | 49.78% | 32.45% | 12.12% |
| Votes ≥ 192 | 16.6538 | 61.91% | 47.61% | 20.23% |
| Votes ≥ 108 | 17.1459 | 72.41% | 60.53% | 33.48% |
| Votes ≥ 32 | 17.6357 | 83.27% | 73.75% | 51.06% |

## Meaning and limits

`oracle_ideal` chooses the earliest safe reached checkpoint separately per case. `oracle_constrained` restricts that hindsight lookup to 16/32/64/continue. Both receive free query-specific decisions outside the primary timer.

`oracle_feasible` is one ordinary policy per cohort, accepted by the agent's unchanged v2 parser and compiler and executed through the same compiled path. It uses only causal features and the bounded rule language. Feature collection and rule evaluation are included in request latency. The agent can hypothetically emit these artifacts; this experiment does not show that it can discover them from its usual feedback or generalize them to new queries.

The feasible optimizer maximizes captured layer-0 work saved and retains safe incumbents at its search limits. These are best-found expressible policies, not certified latency maxima. Earliest safe checkpoints likewise do not prove minimum wall time. The following bounds apply to traversal work only:

| Cohort | Best-found work saved | Work upper bound | Work optimum proven |
| --- | ---: | ---: | --- |
| full_workload | 19.20% | 45.05% | False |
| heldout_test | 26.99% | 42.15% | False |

Intervals bootstrap 20,000 query-vector clusters and retain paired conditions and readers. They are conditional on one allocation and fixed hindsight policies; the two cohorts overlap. Allocation and policy-selection uncertainty are omitted.

The empty/native 90% interval must fall entirely within [0.98, 1.02] in every condition to pass the timing-control criterion. Full control intervals, matched-continue costs and reader ratios are retained in `report.json`.

**full_workload:** descriptive estimate; timing equivalence controls inconclusive/outside band. Conditions failing the strict empty/native 90% interval equivalence criterion: ['-1', '527', '192', '108', '32']. Per-case recall losses: {'oracle_ideal': 0, 'oracle_constrained': 0, 'oracle_feasible': 0}. Result-count losses under the recall-only gate: {'oracle_ideal': 3, 'oracle_constrained': 2, 'oracle_feasible': 0}.

**heldout_test:** descriptive estimate; timing equivalence controls inconclusive/outside band. Conditions failing the strict empty/native 90% interval equivalence criterion: ['-1', '743', '527', '192', '108', '32']. Per-case recall losses: {'oracle_ideal': 0, 'oracle_constrained': 0, 'oracle_feasible': 0}. Result-count losses under the recall-only gate: {'oracle_ideal': 0, 'oracle_constrained': 0, 'oracle_feasible': 0}.

The test-fitted policy has 147 recall losses outside its fitted cohort; these transfer outcomes are retained.

The earlier `oracle_ideal` results retain their additional native-result-count constraint and historical allocation. The new recall-only gate changes three ideal choices in 7,000 cases. Historical evidence is preserved separately.

## Artifacts

Ordinary feasible policies and evaluator-only lookup policies are under `policies/`. `registry.json` distinguishes their schemas and records hashes. Compiler and fit certificates, the frozen timing protocol, full per-condition report, and allocation accounting accompany this file. The raw returns remain in the parent study directory.

New comparison aggregate allocated time: 9410 seconds. No provider calls or fresh exact queries were made.
