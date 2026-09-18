"""``groundspec pack test``: runs a pack's own ``tests/scenarios.toml``
fixtures against its ``completion-gates.toml`` conditions and its rules'
``applies_when`` conditions -- both already-safe, non-executable condition
evaluation, exactly as ``groundspec evaluate``/``groundspec audit`` already
use for a Task Contract. No pack-provided code ever runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from groundspec.packs.sdk.gates import evaluate_gates
from groundspec.packs.sdk.manifest import DomainPack
from groundspec.rules.condition import evaluate as evaluate_condition


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    passed: bool
    evaluation_kind: str
    failures: tuple[str, ...]


def run_pack_tests(pack: DomainPack) -> list[ScenarioResult]:
    results = []
    gate_pairs = [(pack.pack_id, g) for g in pack.completion_gates]
    for scenario in pack.scenarios:
        failures: list[str] = []

        triggered = {
            t.gate_id
            for t in evaluate_gates(
                gate_pairs, contract=scenario.given_contract_fragment, evidence=scenario.given_evidence
            )
        }
        for gate_id in scenario.expect_gates_triggered:
            if gate_id not in triggered:
                failures.append(f"expected gate {gate_id!r} to trigger, but it did not")
        for gate_id in scenario.expect_gates_not_triggered:
            if gate_id in triggered:
                failures.append(f"expected gate {gate_id!r} to NOT trigger, but it did")

        if pack.rules is not None:
            rules_by_id = {r["id"]: r for r in pack.rules.rules}
            for rule_id in scenario.expect_rules_apply:
                rule = rules_by_id.get(rule_id)
                if rule is None:
                    failures.append(f"rule {rule_id!r} not found in this pack")
                elif not evaluate_condition(rule["applies_when"], scenario.given_contract_fragment):
                    failures.append(f"expected rule {rule_id!r} to apply, but it did not")
            for rule_id in scenario.expect_rules_not_apply:
                rule = rules_by_id.get(rule_id)
                if rule is None:
                    failures.append(f"rule {rule_id!r} not found in this pack")
                elif evaluate_condition(rule["applies_when"], scenario.given_contract_fragment):
                    failures.append(f"expected rule {rule_id!r} to NOT apply, but it did")

        results.append(
            ScenarioResult(
                scenario_id=scenario.id,
                passed=not failures,
                evaluation_kind=scenario.evaluation_kind,
                failures=tuple(failures),
            )
        )
    return results
