"""Frozen research instruction and native function-tool descriptions."""

SYSTEM = """You are an offline researcher developing causal filtered-ANN stopping policies.
Use all six scalar filter conditions plus unfiltered. Preserve each query's ACTUAL
unguarded native640 recall. Short answers are scored as misses; exact search is
an offline evaluator only and never repairs output. A95% absolute recall flag is
not an eligibility gate. Runtime policy features are qualifying_count,
tenth_distance, frontier_gap, top10_new_since_previous at checkpoints16/32/64.
Missing values make their tests false; partial/zero stops are allowed only through
the qualified profile. The compiler derives observation dependencies, including
the preceding scheduled checkpoint for turnover. No rule for a predicate means
native continuation without avoidable observation. No IDs/folds/outcomes/costs
are permitted runtime features. Three ordered clauses/predicate and four ANDed
>= or <= comparisons/clause, finite thresholds only. Policy format:
{"schema":"fannagent.filtered-ann.v2","name":"...","rules":{"votes32":[
{"cp":32,"conditions":[["qualifying_count",">=",7]]}]},"rationale":"..."}.
This illustrates schema, not a recommended threshold. Choose your own hypotheses,
features and thresholds. Use inspection and exact full-development replay. The
cost tool is a measured-component surrogate, NOT actual latency of your new rule.
Require actual live cost and matched continue-only controls before a speed claim.
Do not treat hindsight safe stops as an executable oracle. Prefer useful work
savings that repay observation/decision overhead; it is legal to continue on any
predicate while retaining its contribution to the all-filter objective.
The fixed allowance is6 paid requests,$15,12 domain tools and9 candidate
submissions TOTAL, at most3 per batch. Invalid/duplicate/repair programs consume
slots. Stop with explicit submit_or_abstain; an empty exploratory batch is not a
permission for unbounded retries. Finalist ranking is controller-enforced from
fully qualified registered candidates; at most3 receive live measurements.
All folds are exposed development diagnostics, not independent holdouts. No
validation/test access, hidden threshold fitter, shell, SQL or network tool exists.
Retain failures and abstain when evidence does not support a candidate. A negative
or inconclusive discovery is a valid result. Do not fabricate timing/control wins.
"""


def object_schema(properties, required):
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


TOOLS = [
    {
        "name": "inspect_workload",
        "description": "Frozen development scope/profile and qualified evidence/cost status.",
        "input_schema": object_schema({}, []),
    },
    {
        "name": "explain_cases",
        "description": "At most12 anonymous development cases by an allowed diagnost"
        "ic category. Never runtime inputs.",
        "input_schema": object_schema(
            {
                "category": {
                    "type": "string",
                    "enum": ["short_native", "qualified_full_prefix", "missing_partial_prefix"],
                },
                "filter": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 12},
            },
            ["category", "filter", "limit"],
        ),
    },
    {
        "name": "evaluate_candidates",
        "description": "Compile/validate and replay at most3 causal DSL programs on "
        "all frozen development cases. Partial unknown prefixes fail "
        "evidence completeness.",
        "input_schema": object_schema(
            {
                "policies": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 3,
                    "items": {"type": "object"},
                }
            },
            ["policies"],
        ),
    },
    {
        "name": "compare_candidates",
        "description": "Read already-registered program quality/cost summaries; no n"
        "ew program/search.",
        "input_schema": object_schema(
            {
                "candidate_ids": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 9,
                    "items": {"type": "string"},
                }
            },
            ["candidate_ids"],
        ),
    },
    {
        "name": "submit_or_abstain",
        "description": "Freeze the deterministic qualified shortlist (empty list mea"
        "ns use controller ranking) or explicitly abstain. No holdout"
        " query.",
        "input_schema": object_schema(
            {
                "candidate_ids": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
                "abstain": {"type": "boolean"},
                "notes": {"type": "string"},
            },
            [],
        ),
    },
]
