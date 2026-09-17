import pytest

from groundspec.rules.condition import UnknownOperator, evaluate

CONTRACT = {
    "routing": {"risk_overlays": ["informational", "security_sensitive"], "risk_level": "high"},
    "budget": {"time_budget_minutes": 30},
}


def test_leaf_eq():
    assert evaluate({"path": "routing.risk_level", "op": "eq", "value": "high"}, CONTRACT)
    assert not evaluate({"path": "routing.risk_level", "op": "eq", "value": "low"}, CONTRACT)


def test_leaf_contains():
    assert evaluate(
        {"path": "routing.risk_overlays", "op": "contains", "value": "security_sensitive"}, CONTRACT
    )


def test_missing_path_is_false_except_not_exists():
    cond_exists = {"path": "routing.nope", "op": "exists"}
    cond_not_exists = {"path": "routing.nope", "op": "not_exists"}
    cond_eq = {"path": "routing.nope", "op": "eq", "value": "x"}
    assert evaluate(cond_exists, CONTRACT) is False
    assert evaluate(cond_not_exists, CONTRACT) is True
    assert evaluate(cond_eq, CONTRACT) is False


def test_all_any_not():
    assert evaluate({"all": [True, {"path": "routing.risk_level", "op": "eq", "value": "high"}]}, CONTRACT)
    assert not evaluate({"all": [True, False]}, CONTRACT)
    assert evaluate({"any": [False, True]}, CONTRACT)
    assert evaluate({"not": False}, CONTRACT)


def test_numeric_comparisons():
    assert evaluate({"path": "budget.time_budget_minutes", "op": "gte", "value": 30}, CONTRACT)
    assert not evaluate({"path": "budget.time_budget_minutes", "op": "gt", "value": 30}, CONTRACT)


def test_unknown_operator_raises():
    with pytest.raises(UnknownOperator):
        evaluate({"path": "routing.risk_level", "op": "wat", "value": "x"}, CONTRACT)
