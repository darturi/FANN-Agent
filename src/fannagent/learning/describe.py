from collections import defaultdict

from ..api import AgentError
from ..store import digest
from .models import FeedbackCorpus


def describe_corpus(corpus: FeedbackCorpus, *, maximum_examples: int = 10) -> dict:
    """Exact observed conflicts are diagnostics, not a proof that stopping is unlearnable."""
    if type(maximum_examples) is not int or not 1 <= maximum_examples <= 100:
        raise AgentError("maximum_examples must be between 1 and 100")
    states = defaultdict(list)
    for query in corpus.queries:
        for label in query.outcomes:
            checkpoint = query.checkpoints[label.checkpoint_index - 1]
            preserves = (
                label.valid
                and label.returned_count == query.effective_k
                and label.recall >= query.native_recall
            )
            states[digest(checkpoint.features)].append(
                {
                    "query_id": query.query_id,
                    "group": query.group,
                    "stratum": query.stratum,
                    "checkpoint_index": label.checkpoint_index,
                    "preserves_native": preserves,
                    "recall_delta": label.recall - query.native_recall,
                    "source_ref": label.source_ref,
                }
            )
    conflicts = [rows for rows in states.values() if len({r["preserves_native"] for r in rows}) > 1]
    return {
        "scope": "learning",
        "evidence_hash": corpus.evidence_hash,
        "queries": len(corpus.queries),
        "independent_groups": len({q.group for q in corpus.queries}),
        "measured_stop_outcomes": sum(len(q.outcomes) for q in corpus.queries),
        "checkpoint_states": sum(len(q.checkpoints) for q in corpus.queries),
        "qualified_features": corpus.qualified_features,
        "runtime_profile_hash": corpus.profile.fingerprint,
        "conflicting_native_preservation_states": len(conflicts),
        "conflict_examples": [rows[:10] for rows in conflicts[:maximum_examples]],
        "interpretation": (
            "Identical allowed observations have different measured native-preservation labels. "
            "This does not establish failure of the aggregate recall objective or policy class."
        ),
    }
