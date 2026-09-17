"""Regression test for the second live-user-test food-delivery defect
report (Riyadh/King Saud University PRD) -- see
tests/regression/food_delivery_riyadh_v0_2_0rc2/README.md for the full
origin and what each fixture represents.

Deliberately tests observable decisions (contract fields, schema
enforcement, evidence classes, completion-state derivation), not prose --
per the project's own "avoid brittle tests that merely search for one
exact sentence" discipline.
"""

import copy
import json
from pathlib import Path

from groundspec.contract.serialization import load_document
from groundspec.contract.validator import validate_contract_dict
from groundspec.metaskill.completion import (
    claim_ledger_has_disclosed_material_limitations,
    derive_completion_state,
    evaluate_acceptance_criteria,
    has_deferred_high_value_open_questions,
    residual_risk_blocks_completion,
)

FIXTURES = Path(__file__).resolve().parents[1] / "regression" / "food_delivery_riyadh_v0_2_0rc2"


def _load(name: str) -> dict:
    return load_document(FIXTURES / name)


def _evidence(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --- 1. Unsupported material claims: no ledger entry, never PASS/PASS_WITH_CAVEATS ---


def test_defective_contract_predates_the_claim_ledger():
    contract = _load("contract_defective.toml")
    assert contract["contract_schema_version"] == "0.3.0"
    assert "claim_ledger" not in contract["status"]
    assert validate_contract_dict(contract) == []


def test_defective_evidence_reports_unmapped_material_claims():
    evidence = _evidence("evidence_defective.json")
    assert len(evidence["unmapped_material_claims"]) == 2
    assert any("budget" in c.lower() for c in evidence["unmapped_material_claims"])
    assert any(
        "platforms" in c.lower() or "competitor" in c.lower() for c in evidence["unmapped_material_claims"]
    )


def test_unmapped_material_claims_prevent_pass_and_pass_with_caveats():
    state = derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=False,
        budget_expired=False,
        acceptance_criteria_met=True,
        has_unmapped_material_claims=bool(_evidence("evidence_defective.json")["unmapped_material_claims"]),
    )
    assert state == "INCOMPLETE"


# --- 2. Riyadh silently promoted vs. confirmed ---


def test_defective_contract_names_the_city_with_no_open_question():
    contract = _load("contract_defective.toml")
    brief_text = (contract["brief"]["raw_user_brief"] + " " + contract["brief"]["goal"]).lower()
    assert "riyadh" in brief_text
    assert "king saud" in brief_text
    assert contract["scope"]["open_questions"] == []


def test_corrected_contract_confirms_the_city_via_an_answered_high_value_question():
    contract = _load("contract_corrected.toml")
    city_questions = [
        q
        for q in contract["scope"]["open_questions"]
        if "city" in q["question"].lower() or "campus" in q["question"].lower()
    ]
    assert city_questions, "expected an explicit city/campus open question"
    assert city_questions[0]["classification"] == "high_value"
    assert city_questions[0]["resolution_status"] == "answered"
    assert "riyadh" in city_questions[0]["answer"].lower()


# --- 3. Conditional ZATCA rule: generalized vs. properly qualified ---


def test_defective_contract_generalizes_the_zatca_rule_with_no_real_source():
    contract = _load("contract_defective.toml")
    fact = contract["status"]["verified_facts"][0]
    assert fact["evidence_label"] == "VERIFIED"
    statement = fact["statement"].lower()
    # The defect: stated as a flat, unconditional rule ("all ... must").
    assert "all food-delivery marketplaces" in statement
    assert "general knowledge" in fact["source"].lower()


def test_corrected_contract_preserves_zatca_conditions_as_secondary_support():
    contract = _load("contract_corrected.toml")
    ledger = contract["status"]["claim_ledger"]
    zatca = next(c for c in ledger if c["claim_id"] == "zatca-deemed-supplier")
    assert zatca["evidence_label"] == "SECONDARY_SOURCE_SUPPORTED"
    qualifiers = zatca["scope_and_qualifiers"].lower()
    assert "conditional" in qualifiers
    assert "resident" in qualifiers or "vat-registered" in qualifiers
    assert zatca["limitations"]
    assert "official" in zatca["limitations"].lower() or "confirmation" in zatca["limitations"].lower()


# --- 4. Secondary source can never claim primary/official authority ---


def test_promoting_a_secondary_source_to_primary_authority_is_schema_invalid():
    contract = _load("contract_corrected.toml")
    mutated = copy.deepcopy(contract)
    ledger = mutated["status"]["claim_ledger"]
    rider = next(c for c in ledger if c["claim_id"] == "rider-employment-status")
    rider["authority_level"] = "primary_official"
    issues = validate_contract_dict(mutated)
    assert len(issues) == 1
    assert issues[0].schema_rule == "enum"
    assert "authority_level" in issues[0].path


# --- 5. Missing direct URLs / supporting excerpts are schema-rejected ---


def test_removing_source_url_from_a_secondary_claim_is_schema_invalid():
    contract = _load("contract_corrected.toml")
    mutated = copy.deepcopy(contract)
    ledger = mutated["status"]["claim_ledger"]
    zatca = next(c for c in ledger if c["claim_id"] == "zatca-deemed-supplier")
    del zatca["source_url"]
    issues = validate_contract_dict(mutated)
    assert len(issues) == 1
    assert issues[0].schema_rule == "required"


def test_removing_excerpt_from_a_secondary_claim_is_schema_invalid():
    contract = _load("contract_corrected.toml")
    mutated = copy.deepcopy(contract)
    ledger = mutated["status"]["claim_ledger"]
    rider = next(c for c in ledger if c["claim_id"] == "rider-employment-status")
    del rider["excerpt_or_locator"]
    issues = validate_contract_dict(mutated)
    assert len(issues) == 1
    assert issues[0].schema_rule == "required"


# --- 6. Model-generated thresholds cannot masquerade as sourced benchmarks ---


def test_conversion_threshold_is_labeled_model_evaluated_not_source_backed():
    contract = _load("contract_corrected.toml")
    ledger = contract["status"]["claim_ledger"]
    threshold = next(c for c in ledger if c["claim_id"] == "conversion-target-threshold")
    assert threshold["evidence_label"] == "MODEL_EVALUATED"


def test_relabeling_the_threshold_as_source_backed_without_citation_is_schema_invalid():
    contract = _load("contract_corrected.toml")
    mutated = copy.deepcopy(contract)
    ledger = mutated["status"]["claim_ledger"]
    threshold = next(c for c in ledger if c["claim_id"] == "conversion-target-threshold")
    threshold["evidence_label"] = "SECONDARY_SOURCE_SUPPORTED"
    issues = validate_contract_dict(mutated)
    assert issues
    assert all(i.schema_rule == "required" for i in issues)


# --- 7. Completion-state derivation: defective can never pass, corrected caveats ---


def _run_pipeline(contract: dict, evidence: dict) -> str:
    acceptance_eval = evaluate_acceptance_criteria(
        contract["acceptance"]["criteria"], evidence["acceptance_criteria_results"]
    )
    has_blocking = any(
        q["classification"] == "blocking" and q["resolution_status"] == "open"
        for q in contract["scope"]["open_questions"]
    )
    claim_ledger = contract["status"].get("claim_ledger", [])
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
        has_unmapped_material_claims=bool(evidence.get("unmapped_material_claims")),
        has_disclosed_material_limitations=claim_ledger_has_disclosed_material_limitations(claim_ledger),
    )


def test_defective_evidence_can_never_produce_pass():
    contract = _load("contract_defective.toml")
    evidence = _evidence("evidence_defective.json")
    state = _run_pipeline(contract, evidence)
    assert state not in ("PASS", "PASS_WITH_CAVEATS")
    assert state == "INCOMPLETE"


def test_corrected_evidence_against_corrected_contract_yields_pass_with_caveats_never_bare_pass():
    contract = _load("contract_corrected.toml")
    evidence = _evidence("evidence_corrected.json")
    state = _run_pipeline(contract, evidence)
    assert state == "PASS_WITH_CAVEATS"


def test_removing_all_weak_labeled_material_claims_flips_the_same_evidence_to_a_bare_pass():
    """Proves the disclosed-material-limitations gate is load-bearing: strip
    the ledger down to only strong-evidence entries (drop the two
    RESEARCH_NEEDED, two SECONDARY_SOURCE_SUPPORTED, and one MODEL_EVALUATED
    entries) and the identical acceptance evidence now yields a bare PASS."""
    contract = copy.deepcopy(_load("contract_corrected.toml"))
    contract["status"]["claim_ledger"] = [
        c for c in contract["status"]["claim_ledger"] if c["evidence_label"] in ("MEASURED", "USER_CONFIRMED")
    ]
    assert contract["status"]["claim_ledger"] == []
    # Also drop the deferred high-value business-model question so it's not
    # a confound for this specific proof.
    contract["scope"]["open_questions"] = [
        q for q in contract["scope"]["open_questions"] if q["resolution_status"] == "answered"
    ]
    evidence = _evidence("evidence_corrected.json")
    state = _run_pipeline(contract, evidence)
    assert state == "PASS"


def test_critical_risk_gate_actually_engages_when_not_explicitly_excused():
    contract = _load("contract_corrected.toml")
    del contract["status"]["residual_risks"][0]["affects_deliverable_validity"]
    evidence = _evidence("evidence_corrected.json")
    state = _run_pipeline(contract, evidence)
    assert state == "FAIL"
