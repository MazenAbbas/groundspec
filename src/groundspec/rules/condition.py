"""Safe, non-executable evaluation of a rule's ``applies_when`` condition.

This is deliberately not a general expression language. There is no eval,
no user-supplied code path, and no operator this module does not enumerate.
A condition is plain data (see the rule_pack JSON Schema for its grammar),
so a malicious rule pack cannot do anything beyond compare fields already
present in the Task Contract.
"""

from __future__ import annotations

from typing import Any

_MISSING = object()


class UnknownOperator(ValueError):
    pass


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def evaluate(condition: Any, contract: dict[str, Any]) -> bool:
    """Evaluate a condition against a (already schema-valid) contract dict.

    Missing-value behavior is explicit: ``exists`` is false and every other
    comparison operator is false when the path is absent, except
    ``not_exists`` which is true. A condition never raises for a missing
    path -- only for a condition shape it does not recognize.
    """
    if isinstance(condition, bool):
        return condition

    if "all" in condition:
        return all(evaluate(sub, contract) for sub in condition["all"])
    if "any" in condition:
        return any(evaluate(sub, contract) for sub in condition["any"])
    if "not" in condition:
        return not evaluate(condition["not"], contract)

    path = condition["path"]
    op = condition["op"]
    value = _get_path(contract, path)
    expected = condition.get("value", _MISSING)

    if op == "exists":
        return value is not _MISSING
    if op == "not_exists":
        return value is _MISSING
    if value is _MISSING:
        return False

    if op == "eq":
        return bool(value == expected)
    if op == "neq":
        return bool(value != expected)
    if op == "in":
        return value in expected
    if op == "not_in":
        return value not in expected
    if op == "contains":
        return isinstance(value, (list, str)) and expected in value
    if op == "gte":
        return bool(value >= expected)
    if op == "lte":
        return bool(value <= expected)
    if op == "gt":
        return bool(value > expected)
    if op == "lt":
        return bool(value < expected)

    raise UnknownOperator(f"unsupported condition operator: {op!r}")
