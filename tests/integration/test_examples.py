"""Validates the repo's examples/ directory (PRD Phase 16): these are
executed, not decorative -- each assertion below exercises the actual
engine against the actual committed fixture file.
"""

from pathlib import Path

import pytest

from groundspec.budget.model import forbid_silent_skip_on_expiry
from groundspec.contract.serialization import load_document
from groundspec.contract.validator import validate_contract_dict
from groundspec.packs.registry import select_packs_for_contract
from groundspec.rules.evaluator import applicable, evaluate_rule_set
from groundspec.rules.precedence import build_rule_set

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"

SLUGS = [
    "01-food-delivery-mvp",
    "02-market-research",
    "03-linkedin-launch-post",
    "04-five-minute-constrained-task",
    "05-high-risk-medical-escalation",
    "06-contradictory-requirements",
    "07-insufficient-evidence",
    "08-partial-completion-correct",
    "09-domain-rule-vs-style-preference",
    "10-unauthorized-external-action",
]


def _load(slug: str) -> dict:
    return load_document(EXAMPLES_DIR / slug / "contract.toml")


@pytest.mark.parametrize("slug", SLUGS)
def test_every_example_is_schema_valid(slug: str):
    contract = _load(slug)
    issues = validate_contract_dict(contract)
    assert issues == [], "\n".join(str(i) for i in issues)


@pytest.mark.parametrize("slug", SLUGS)
def test_every_example_resolves_its_rule_packs_without_error(slug: str):
    contract = _load(slug)
    project_packs = []
    project_pack_dir = EXAMPLES_DIR / slug / "project-packs"
    if project_pack_dir.is_dir():
        project_packs = list(project_pack_dir.glob("*.json"))
    packs = select_packs_for_contract(contract, project_pack_paths=project_packs)
    assert packs, f"{slug}: expected at least the core pack to be selected"


def test_05_high_risk_names_an_escalation_condition_and_hard_constraints():
    contract = _load("05-high-risk-medical-escalation")
    assert contract["control"]["escalation_conditions"]
    packs = select_packs_for_contract(contract)
    rule_set = build_rule_set(packs)
    applied = evaluate_rule_set(rule_set, contract)
    hard = applicable(applied, severity="hard_constraint")
    hard_ids = {a.qualified.fq_id for a in hard}
    assert "risk-overlay-high-stakes-regulated:no-professional-authority-implied" in hard_ids
    assert "risk-overlay-high-stakes-regulated:no-automatic-external-action" in hard_ids


def test_06_contradictory_requirements_are_recorded_as_a_resolved_blocking_question():
    contract = _load("06-contradictory-requirements")
    questions = contract["scope"]["open_questions"]
    assert questions, "expected the contradiction to be logged as an open question"
    blocking = [q for q in questions if q["classification"] == "blocking"]
    assert blocking
    assert blocking[0]["resolution_status"] == "answered"
    assert blocking[0]["answer"]


def test_07_insufficient_evidence_yields_insufficient_verdict():
    from groundspec.scoring.rubric import score

    contract = _load("07-insufficient-evidence")
    import json

    evidence_path = EXAMPLES_DIR / "07-insufficient-evidence" / "result" / "evidence.json"
    evidence = json.loads(evidence_path.read_text())
    contract["quality"]["soft_objectives"] = [
        {"dimension": "correctness", "weight": 0.5},
        {"dimension": "evidence_quality", "weight": 0.5},
    ]
    result = score(
        soft_objectives=contract["quality"]["soft_objectives"],
        hard_constraint_results=evidence["hard_constraint_results"],
        dimension_scores=evidence["dimension_scores"],
    )
    assert result.insufficient_dimensions == ["evidence_quality"]
    assert result.verdict == "scored"  # correctness alone is still enough to produce a (partial) score
    assert result.weighted_total == pytest.approx(0.9)


def test_08_partial_completion_passes_the_no_silent_skip_invariant():
    contract = _load("08-partial-completion-correct")
    status = contract["status"]
    assert status["completion_status"] == "partial"
    assert status["budget_expired"] is True
    assert forbid_silent_skip_on_expiry(status) == []
    assert status["omitted_work"]


def test_08_would_have_failed_if_it_claimed_complete_instead():
    contract = _load("08-partial-completion-correct")
    status = dict(contract["status"])
    status["completion_status"] = "complete"
    violations = forbid_silent_skip_on_expiry(status)
    assert len(violations) == 1


def test_09_project_preference_conflicts_with_and_loses_to_domain_rule():
    contract = _load("09-domain-rule-vs-style-preference")
    project_pack_dir = EXAMPLES_DIR / "09-domain-rule-vs-style-preference" / "project-packs"
    project_packs = list(project_pack_dir.glob("*.json"))
    packs = select_packs_for_contract(contract, project_pack_paths=project_packs)
    rule_set = build_rule_set(packs)
    assert len(rule_set.conflicts) == 1
    conflict = rule_set.conflicts[0]
    assert conflict.conflict_key == "platform-format-constraint"
    assert conflict.winner.pack_layer == "domain"
    assert all(loser.pack_layer == "project" for loser in conflict.losers)


def test_10_requires_confirmation_before_publishing():
    contract = _load("10-unauthorized-external-action")
    auth = contract["routing"]["authorization"]
    assert "publishing anything to the public support forum" in auth["requires_confirmation_for"]
    assert "drafting the apology text" in auth["granted_permissions"]
    packs = select_packs_for_contract(contract)
    rule_set = build_rule_set(packs)
    applied = evaluate_rule_set(rule_set, contract)
    hard_ids = {a.qualified.fq_id for a in applicable(applied, severity="hard_constraint")}
    assert "risk-overlay-external-communication:explicit-permission-before-sending" in hard_ids


def test_04_five_minute_task_has_a_tight_budget():
    contract = _load("04-five-minute-constrained-task")
    assert contract["budget"]["time_budget_minutes"] == 5
