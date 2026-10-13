from decimal import Decimal
from types import SimpleNamespace

import pytest
from minisweagent.exceptions import FormatError

from fannagent.budget import Budget
from fannagent.config import ModelConfig
from fannagent.errors import AgentError
from fannagent.model import BudgetedModel
from fannagent.store import Store


def test_timeout_attempts_are_reserved_and_unknown_usage_is_not_free(tmp_path):
    config = ModelConfig(
        model="provider/test",
        ceiling_usd="1",
        input_usd_per_million="1",
        output_usd_per_million="2",
        input_token_bound=10000,
        output_token_limit=1000,
        pricing_revision="fixture",
        bound_verified=True,
        max_attempts=2,
    )
    budget = Budget(Store(tmp_path / "run", create=True), config)
    calls = []

    def dispatch(**kwargs):
        calls.append(kwargs)
        raise TimeoutError()

    model = BudgetedModel(config, budget, dispatch)
    with pytest.raises(AgentError, match="possible charge"):
        model.query([{"role": "user", "content": "hi"}])
    assert len(calls) == 2 and all(c["num_retries"] == 0 for c in calls)
    assert budget.summary()["uncertain_calls"] == 2
    assert Decimal(budget.summary()["committed_usd"]) == Decimal(".024")


def test_response_is_billed_before_parse_failure(tmp_path):
    config = ModelConfig(
        model="provider/test",
        ceiling_usd="1",
        input_usd_per_million="1",
        output_usd_per_million="2",
        input_token_bound=10000,
        output_token_limit=1000,
        pricing_revision="fixture",
        bound_verified=True,
    )
    budget = Budget(Store(tmp_path / "run", create=True), config)
    response = SimpleNamespace(
        model_dump=lambda **kw: {"usage": {"prompt_tokens": 100, "completion_tokens": 50}},
        choices=[],
    )
    model = BudgetedModel(config, budget, lambda **kw: response)
    with pytest.raises(FormatError):
        model.query([{"role": "user", "content": "hi"}])
    assert Decimal(budget.summary()["committed_usd"]) == Decimal(".0002")


def test_unknown_usage_retains_maximum_and_response(tmp_path):
    config = ModelConfig(
        model="provider/test",
        ceiling_usd="1",
        input_usd_per_million="1",
        output_usd_per_million="2",
        input_token_bound=10000,
        output_token_limit=1000,
        pricing_revision="fixture",
        bound_verified=True,
    )
    budget = Budget(Store(tmp_path / "run", create=True), config)
    response = SimpleNamespace(model_dump=lambda **kw: {"usage": None}, choices=[])
    with pytest.raises(AgentError, match="usage unavailable"):
        BudgetedModel(config, budget, lambda **kw: response).query(
            [{"role": "user", "content": "hi"}]
        )
    assert budget.summary()["uncertain_calls"] == 1
    assert Decimal(budget.summary()["committed_usd"]) == Decimal(".012")
    with budget.store.connect() as db:
        assert (
            db.execute("SELECT COUNT(*) FROM artifacts WHERE kind='model_response'").fetchone()[0]
            == 1
        )
