"""Regression test for the exact v0.2.0rc1 Guided-mode food-delivery defect
report -- see tests/regression/food_delivery_v0_2_0rc1/README.md for the
full origin and what each fixture represents.

Deliberately tests observable decisions (contract fields, authorization
handling, evidence classes, completion-state derivation), not prose --
per the project's own "avoid brittle tests that merely search for one
exact sentence" discipline.
"""

import json
from pathlib import Path

from groundspec.contract.serialization import load_document
from groundspec.contract.validator import validate_contract_dict
from groundspec.metaskill.completion import (
    derive_completion_state,
    evaluate_acceptance_criteria,
    has_deferred_high_value_open_questions,
    residual_risk_blocks_completion,
)

FIXTURES = Path(__file__).resolve().parents[1] / "regression" / "food_delivery_v0_2_0rc1"


def _load(name: str) -> dict:
    return load_document(FIXTURES / name)


def _evidence(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --- 1. The self-review-as-verified-fact pattern: was valid, is now impossible ---


def test_defective_pattern_was_valid_under_schema_0_2_0():
    contract = _load("contract_defective.toml")
    assert contract["contract_schema_version"] == "0.2.0"
    assert validate_contract_dict(contract) == []


def test_identical_defective_pattern_is_rejected_under_schema_0_3_0():
    contract = _load("contract_defective.toml")
    contract["contract_schema_version"] = "0.3.0"
    issues = validate_contract_dict(contract)
    assert len(issues) == 1
    assert issues[0].path == "status.verified_facts.0.evidence_label"
    assert issues[0].schema_rule == "enum"


# --- 2. The corrected contract actually surfaces the required checklist ---


def test_corrected_contract_is_schema_valid():
    contract = _load("contract_corrected.toml")
    assert contract["contract_schema_version"] == "0.3.0"
    assert validate_contract_dict(contract) == []


def test_corrected_contract_covers_the_material_clarification_checklist():
    contract = _load("contract_corrected.toml")
    questions = contract["scope"]["open_questions"]
    all_text = " ".join(q["question"].lower() for q in questions)

    # Every dimension the report named as silently defaulted must appear
    # somewhere in the recorded open questions -- as a question, not buried
    # silently in an assumption.
    for keyword in ("campus", "marketplace", "persona", "payment", "language", "monetization"):
        assert keyword in all_text, f"missing required checklist dimension: {keyword}"

    blocking_or_high_value = [q for q in questions if q["classification"] in ("blocking", "high_value")]
    assert len(blocking_or_high_value) >= 5

    # At least one item was actually asked (answered), not everything deferred.
    assert any(q["resolution_status"] == "answered" for q in questions)
    # At least one high-value item was deferred under budget -- and it must
    # be recorded as an open_question, never silently missing.
    deferred_high_value = [
        q for q in questions if q["classification"] == "high_value" and q["resolution_status"] == "defaulted"
    ]
    assert deferred_high_value
    for q in deferred_high_value:
        assert q["default_applied"], "a deferred high-value item must state what was assumed instead"


def test_corrected_contract_stays_within_its_own_clarification_budget():
    contract = _load("contract_corrected.toml")
    asked = [q for q in contract["scope"]["open_questions"] if q["resolution_status"] == "answered"]
    assert len(asked) <= contract["budget"]["max_clarification_questions"]


def test_corrected_contract_records_the_authorization_boundary_verbatim():
    contract = _load("contract_corrected.toml")
    boundaries_text = " ".join(contract["routing"]["authorization"]["boundaries"]).lower()
    assert "no external action" in boundaries_text
    assert "network" in boundaries_text


def test_corrected_contract_bounds_the_research_needed_claim_correctly():
    contract = _load("contract_corrected.toml")
    claims = contract["status"]["unverified_claims"]
    research_needed = [c for c in claims if c.get("evidence_label") == "RESEARCH_NEEDED"]
    assert research_needed
    reason = research_needed[0]["reason"].lower()
    assert "does not exist" not in reason
    assert "no source exists" not in reason
    assert "not authorized" in reason or "could not be checked" in reason


def test_corrected_contract_no_self_review_leaks_into_verified_facts():
    contract = _load("contract_corrected.toml")
    real_labels = ("VERIFIED", "MEASURED", "SOURCE_VERIFIED", "USER_CONFIRMED", "HUMAN-REVIEWED")
    for fact in contract["status"]["verified_facts"]:
        assert fact["evidence_label"] in real_labels


# --- 3. Completion-state derivation: defective evidence cannot pass, corrected can ---


def _run_pipeline(contract: dict, evidence: dict) -> str:
    acceptance_eval = evaluate_acceptance_criteria(
        contract["acceptance"]["criteria"], evidence["acceptance_criteria_results"]
    )
    has_blocking = any(
        q["classification"] == "blocking" and q["resolution_status"] == "open"
        for q in contract["scope"]["open_questions"]
    )
    return derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=has_blocking,
        budget_expired=bool(contract["status"].get("budget_expired", False)),
        acceptance_criteria_met=acceptance_eval.must_criteria_met,
        authorization_boundary_violated=bool(evidence.get("authorization_violations")),
        unresolved_critical_risk_to_validity=residual_risk_blocks_completion(
            contract["status"]["residual_risks"]
        ),
        has_deferred_high_value_items=has_deferred_high_value_open_questions(
            contract["scope"]["open_questions"]
        ),
    )


def test_defective_evidence_can_never_produce_pass():
    contract = _load("contract_corrected.toml")
    evidence = _evidence("evidence_defective.json")
    state = _run_pipeline(contract, evidence)
    assert state not in ("PASS", "PASS_WITH_CAVEATS")
    assert state == "FAIL"  # the authorization violation alone forces this


def test_corrected_evidence_against_corrected_contract_yields_pass_with_caveats():
    # Not a plain PASS: the corrected fixture deliberately still has
    # deferred high-value items (persona/payments/language/monetization),
    # exactly the situation that must be caveated, not hidden -- two
    # independent forward tests of this exact policy reached a bare PASS
    # with six such defaults before this gate existed.
    contract = _load("contract_corrected.toml")
    evidence = _evidence("evidence_corrected.json")
    state = _run_pipeline(contract, evidence)
    assert state == "PASS_WITH_CAVEATS"


def test_critical_risk_gate_actually_engages_when_not_explicitly_excused():
    """The corrected fixture's critical risk is explicitly marked as NOT
    affecting validity (a deliberate, justified exception). Removing that
    exception (falling back to the conservative default) must flip the
    same otherwise-clean evidence from passing to FAIL -- proving the gate
    is load-bearing, not decorative."""
    contract = _load("contract_corrected.toml")
    del contract["status"]["residual_risks"][0]["affects_deliverable_validity"]
    evidence = _evidence("evidence_corrected.json")
    state = _run_pipeline(contract, evidence)
    assert state == "FAIL"


def test_weak_evidence_on_a_strong_evidence_criterion_yields_incomplete_not_pass():
    contract = _load("contract_corrected.toml")
    evidence = _evidence("evidence_corrected.json")
    evidence = dict(evidence)
    evidence["acceptance_criteria_results"] = dict(evidence["acceptance_criteria_results"])
    evidence["acceptance_criteria_results"]["no-unauthorized-network-access"] = {
        "met": True,
        "evidence_label": "MODEL-EVALUATED",
    }
    state = _run_pipeline(contract, evidence)
    assert state == "INCOMPLETE"
