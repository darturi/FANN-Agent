"""Small independent trajectories for learning contract and replay tests."""

from fannagent.api import FeatureDefinition, RuntimeProfile
from fannagent.learning.models import (
    Checkpoint,
    FeedbackCorpus,
    LearningObjective,
    StopOutcome,
    TrainingEntitlement,
    TrainingQuery,
)
from fannagent.store import digest


def make_corpus(groups=6):
    profile = RuntimeProfile(
        name="learning-fixture/v1",
        features={
            name: FeatureDefinition(name=name, kind=kind)
            for name, kind in (
                ("work", "int"),
                ("signal", "float"),
                ("flag", "bool"),
                ("nullable", "float"),
                ("unqualified", "float"),
            )
        },
        checkpoint_interval=10,
        checkpoint_semantics="completed synthetic expansion",
        stopping_scope="fixture_search",
        work_unit="distances",
        collection_groups=("basic",),
    )
    inventory, queries = [], []
    for group in range(groups):
        for stratum in ("plain", "filtered"):
            entitlement = TrainingEntitlement(
                query_id=f"q{group}-{stratum}", group=str(group), stratum=stratum
            )
            checkpoints = [
                Checkpoint(
                    checkpoint_index=i,
                    features={"work": 10 * i, "signal": signal, "flag": i == 3, "nullable": 0.25},
                )
                for i, signal in enumerate((0.9, 0.5, 0.1), 1)
            ]
            outcomes = [
                StopOutcome(
                    checkpoint_index=i,
                    recall=recall,
                    returned_count=10,
                    valid=True,
                    actual_work=10 * i,
                    prefix_matches=True,
                    source_prefix_sha256=digest([group, stratum, i]),
                    source_ref=f"fixture:{group}:{stratum}:{i}",
                )
                for i, recall in ((1, 0.5), (3, 1.0))
            ]
            inventory.append(entitlement)
            queries.append(
                TrainingQuery(
                    **entitlement.model_dump(),
                    effective_k=10,
                    native_recall=1.0,
                    native_work=40,
                    checkpoints=checkpoints,
                    outcomes=outcomes,
                )
            )
    return FeedbackCorpus(
        profile=profile,
        qualified_features=["work", "signal", "flag", "nullable"],
        collection_groups=["basic"],
        work_feature="work",
        source_hashes={"fixture": digest([])},
        inventory=inventory,
        queries=queries,
        objective=LearningObjective(minimum_groups=2, bootstrap_samples=300),
    )


def stop_at(work):
    return {
        "name": f"stop-{work}",
        "root": {
            "if": {"op": "gte", "args": [{"feature": "work"}, {"int": work}]},
            "then": "stop",
            "else": "continue",
        },
    }
