"""Determines which rules in a resolved RuleSet apply to a given contract."""

from __future__ import annotations

from dataclasses import dataclass

from groundspec.rules.condition import evaluate
from groundspec.rules.precedence import QualifiedRule, RuleSet


@dataclass(frozen=True)
class AppliedRule:
    qualified: QualifiedRule
    applies: bool

    @property
    def severity(self) -> str:
        severity = self.qualified.rule["severity"]
        assert isinstance(severity, str)
        return severity


def evaluate_rule_set(rule_set: RuleSet, contract: dict[str, object]) -> list[AppliedRule]:
    return [
        AppliedRule(qualified=qr, applies=evaluate(qr.rule["applies_when"], contract))
        for qr in rule_set.active_rules
    ]


def applicable(applied: list[AppliedRule], *, severity: str | None = None) -> list[AppliedRule]:
    result = [a for a in applied if a.applies]
    if severity is not None:
        result = [a for a in result if a.severity == severity]
    return result
