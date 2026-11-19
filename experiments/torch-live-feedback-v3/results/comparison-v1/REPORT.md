# V3 agent versus broad feasible oracle

Job 23747524; frozen development-only agent outcome: **development_candidate_frozen**.

The saved broad oracle policies were rerun alongside the frozen agent on the same native baseline. All-seven-condition savings use ratios of mean request latency.

| Cohort | Agent savings | Broad oracle savings | Gap | Agent recall-loss cases | Strict controls |
|---|---:|---:|---:|---:|---|
| Test subset: 1,925 cases | -0.46% | 66.32% | 66.77 pp | 0 | Not established |
| Full workload: 7,000 cases | -1.78% | 64.87% | 66.66 pp | 0 | Not established |

A recall-loss count above zero means the agent did not preserve native quality on that cohort. Its measured latency is diagnostic. Failed control equivalence makes estimates descriptive, not certified speedups or numerical ceilings.

| Cohort / intended arm | Mean request latency | Conditional 95% savings interval | Recall-loss cases | Result-count-loss cases | Early stops |
|---|---:|---:|---:|---:|---:|
| Test / native | 12.4214 ms | [0.00%, 0.00%] | 0 | 0 | 0 |
| Test / agent | 12.4781 ms | [-1.59%, 0.67%] | 0 | 0 | 105 |
| Test / oracle_feasible | 4.1838 ms | [64.76%, 67.86%] | 0 | 0 | 1923 |
| Full / native | 12.4651 ms | [0.00%, 0.00%] | 0 | 0 | 0 |
| Full / agent | 12.6876 ms | [-2.42%, -1.12%] | 0 | 0 | 351 |
| Full / oracle_feasible | 4.3784 ms | [64.02%, 65.73%] | 0 | 3 | 6996 |

Oracle quality is assessed on its fitted cohort. The test-fitted oracle's behavior outside the test subset remains in the raw full-workload records, but is not the full-cohort oracle comparison. Result-count preservation is reported separately from recall preservation.

The JSON retains native/agent/oracle means, both seven-condition and six-filter aggregates, per-condition results, result-count losses, conditional intervals and control failures.

Model requests: 32; recorded spend $2.79781 under $15. Charged ANN reservations: 248800 / 300,000. Allocated seconds: 6049 / 21,600. Zero fresh exact queries and no automatic retries.

The agent used 450 development groups; the oracle used hindsight on its reported cohort. No final feedback reached the agent. The cohorts overlap, full includes development, and earlier oracle results informed this research design. Bootstrap intervals condition on one allocation and the fixed selected artifacts; they do not include discovery uncertainty.

Raw returns, model transcripts, offline fitting scripts and sealed inputs remain in the sibling trial directory outside Git.
