"""Scripted fixtures only. These receipts never authorize a paid episode."""

from copy import deepcopy
from decimal import Decimal

from fannagent.config import ModelConfig

from .evidence import Evidence
from .policy import FILTERS, PROFILE


def fixture_bundle():
    rows = []
    for group in range(5):
        for filter_ in FILTERS:
            rows.append(
                {
                    "group": group,
                    "fold": group,
                    "filter": filter_,
                    "native_recall": 0.7,
                    "native_count": 7,
                    "observations": {
                        "16": {
                            "qualifying_count": 7,
                            "tenth_distance": None,
                            "frontier_gap": None,
                            "top10_new_since_previous": None,
                        }
                    },
                    "proofs": {"16": {"recall": 0.7, "returned_count": 7}},
                    "costs": {
                        "search_ms": {"full": 10.0, "16": 1.0},
                        "count_only_ms": 0.01,
                        "ranked_ms": 0.1,
                        "turnover_ms": 0.01,
                        "decision_base_ms": 0.001,
                        "comparison_ms": 0.001,
                    },
                }
            )
    return {
        "schema": "filtered-ann-evidence.v2",
        "scope": "development",
        "runtime_profile": PROFILE.fingerprint,
        "rows": rows,
        "cost_status": "qualified",
        "cost_qualification_receipt_sha256": "0" * 64,
        "fixture_only": True,
    }


def fixture_evidence():
    return Evidence(fixture_bundle(), fixture=True)


def fixture_gates(evidence):
    return {
        "M0": {"status": "verified_attribution_resolved", "receipt_sha256": "0" * 64},
        "M1": {
            "status": "verified_original_graph",
            "runtime_profile": PROFILE.fingerprint,
            "receipt_sha256": "0" * 64,
        },
        "M2": {"evidence_hash": evidence.identity},
        "fixture_only": True,
    }


def fixture_config(**overrides):
    config = {
        "model": "scripted",
        "ceiling_usd": Decimal("15"),
        "allowance_usd": Decimal("0"),
        "input_usd_per_million": Decimal("2"),
        "output_usd_per_million": Decimal("10"),
        "input_token_bound": 50000,
        "output_token_limit": 6000,
        "bound_verified": True,
        "max_attempts": 1,
        "pricing_revision": "scripted-test-rates-not-a-real-provider-rate-card",
    }
    config.update(overrides)
    return ModelConfig(**config)


def fixture_policy():
    return {
        "schema": "fannagent.filtered-ann.v2",
        "name": "scripted_partial_count",
        "rules": {f: [{"cp": 16, "conditions": [["qualifying_count", "<=", 7]]}] for f in FILTERS},
        "rationale": "Synthetic rehearsal only, not a learned policy or study result.",
    }


class ScriptedTransport:
    automatic_retries = False

    def __init__(self, contents):
        self.contents = list(contents)
        self.requests = []

    def __call__(self, request):
        self.requests.append(deepcopy(request))
        content = self.contents.pop(0)
        if isinstance(content, BaseException):
            raise content
        return {
            "model": "scripted",
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "content": content,
        }


def request_for(campaign):
    from .toolspec import SYSTEM, TOOLS

    return {
        "model": campaign.model_config.model,
        "max_tokens": 6000,
        "system": SYSTEM,
        "tools": TOOLS,
        "messages": campaign.store.get("v2_messages")
        or [{"role": "user", "content": "Run the scripted protocol rehearsal."}],
    }
