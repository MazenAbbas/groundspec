"""Deterministic evaluation corpus for the Domain Pack SDK release, covering
the 15 named scenarios from the product spec. Each scenario tests an
observable invariant (a completion state, a triggered gate, a schema
rejection) through real code -- the actual product-management/data-science-ml
packs' real completion gates, not a re-description of them in prose, and
never a fabricated comparison score.

Every scenario is `evaluation_kind = "deterministic"`: pure condition-DSL
evaluation over synthetic contract/evidence fixtures. This corpus does not,
by itself, prove a live model would populate these evidence.json fields
correctly for a real request -- that is what the independent forward tests
in docs/forward-tests-v0.3.0rc1.md are for (see that document for which
scenarios were additionally run live). See docs/pack-authoring-guide.md's
"tests/scenarios.toml" section for the same evaluation_kind discipline
applied inside a pack itself.
"""

from __future__ import annotations

from groundspec.metaskill.completion import (
    derive_completion_state,
    evaluate_acceptance_criteria,
)
from groundspec.packs.sdk.discovery import discover_official
from groundspec.packs.sdk.gates import apply_pack_gates, evaluate_gates
from groundspec.packs.sdk.manifest import load_pack


def _load(pack_id: str):
    location = next(loc for loc in discover_official() if loc.pack_id_hint == pack_id)
    return load_pack(location.pack_dir, origin=location.origin)


def _final_state(evidence: dict[str, object], *, pack_ids: list[str], base_state: str = "PASS") -> str:
    gate_pairs = []
    for pack_id in pack_ids:
        pack = _load(pack_id)
        gate_pairs.extend((pack.pack_id, g) for g in pack.completion_gates)
    triggered = evaluate_gates(gate_pairs, contract={}, evidence=evidence)
    return apply_pack_gates(base_state, triggered)  # type: ignore[arg-type]


# 1. Customer-churn classification with post-outcome leakage.
def test_scenario_01_churn_leakage_fails():
    state = _final_state({"ds_unresolved_leakage_risk": True}, pack_ids=["data-science-ml"])
    assert state == "FAIL"


# 2. Fraud detection with severe class imbalance (accuracy hides the real cost structure).
def test_scenario_02_fraud_imbalance_metric_mismatch_incomplete():
    state = _final_state({"ds_metric_mismatched_to_objective": True}, pack_ids=["data-science-ml"])
    assert state == "INCOMPLETE"


# 3. Time-series forecasting where a random split would leak the future.
def test_scenario_03_time_series_random_split_leak_fails():
    # Same underlying gate as scenario 1 -- the point is that the mechanism
    # catches structurally identical defects regardless of the domain
    # narrative (customer churn vs. forecasting).
    state = _final_state({"ds_unresolved_leakage_risk": True}, pack_ids=["data-science-ml"])
    assert state == "FAIL"


# 4. Medical-image classifier requesting a production-ready claim.
def test_scenario_04_medical_image_production_claim_fails():
    state = _final_state(
        {"ds_high_stakes_missing_domain_review": True, "ds_production_claim_single_offline_score": True},
        pack_ids=["data-science-ml"],
    )
    assert state == "FAIL"


# 5. Gulf-food image classifier using uncertain image licenses.
def test_scenario_05_uncertain_image_license_incomplete():
    state = _final_state({"ds_dataset_provenance_unknown": True}, pack_ids=["data-science-ml"])
    assert state == "INCOMPLETE"


# 6. Arabic NLP classifier with dialect imbalance (a blended metric hides
#    per-dialect performance -- the same "metric doesn't match the actual
#    objective" defect class as scenario 2, applied to a different domain).
def test_scenario_06_arabic_dialect_imbalance_metric_mismatch_incomplete():
    state = _final_state({"ds_metric_mismatched_to_objective": True}, pack_ids=["data-science-ml"])
    assert state == "INCOMPLETE"


# 7. Recommendation system with user-level train/test overlap.
def test_scenario_07_recommender_user_level_overlap_fails():
    state = _final_state({"ds_unresolved_leakage_risk": True}, pack_ids=["data-science-ml"])
    assert state == "FAIL"


# 8. RAG system evaluated only by the same model that generated the answers
#    (a self-review masquerading as independent verification) -- this
#    exercises the pre-existing (v0.2.0rc2) evidence-adequacy mechanism,
#    not a data-science-ml-specific gate, to prove the two compose.
def test_scenario_08_rag_self_evaluation_is_inadequate_not_pass():
    criteria = [{"id": "rag-accuracy", "priority": "must", "verification_method": "automated_test"}]
    results = {"rag-accuracy": {"met": True, "evidence_label": "MODEL-EVALUATED"}}
    result = evaluate_acceptance_criteria(criteria, results)
    assert result.must_criteria_met is None
    assert result.inadequate_evidence_ids == ["rag-accuracy"]
    state = derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=False,
        budget_expired=False,
        acceptance_criteria_met=result.must_criteria_met,
    )
    assert state == "INCOMPLETE"


# 9. Small toy regression task where a simple, lightweight workflow is
#    sufficient -- a clean positive control: no gate should ever trigger on
#    an honest, complete, unexceptional evidence.json.
def test_scenario_09_toy_regression_clean_run_passes():
    state = _final_state({}, pack_ids=["data-science-ml"])
    assert state == "PASS"


# 10. Existing Python service adding a prediction endpoint (software +
#     data-science-ml composed together) -- a clean run across both packs'
#     gates stays PASS; composing two packs must never by itself force a
#     caveat.
def test_scenario_10_prediction_endpoint_multi_pack_clean_run_passes():
    state = _final_state({}, pack_ids=["software", "data-science-ml"])
    assert state == "PASS"


# 11. PRD with an unspecified launch city, properly disclosed as a deferred
#     high-value item (not silently defaulted) -- exercises the existing
#     core schema-0.4.0 mechanism (has_deferred_high_value_items), composed
#     with product-management's own gates all clean.
def test_scenario_11_prd_unspecified_city_disclosed_is_caveats_not_fail():
    gate_state = _final_state({}, pack_ids=["product-management"])
    assert gate_state == "PASS"  # no PM gate fired
    final = derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=False,
        budget_expired=False,
        acceptance_criteria_met=True,
        has_deferred_high_value_items=True,  # the city was disclosed as deferred, not hidden
    )
    assert final == "PASS_WITH_CAVEATS"


# 12. PRD that confuses market-wide data with target-segment demand.
def test_scenario_12_prd_market_vs_segment_conflation_fails():
    state = _final_state(
        {"pm_market_wide_data_presented_as_segment_evidence": True}, pack_ids=["product-management"]
    )
    assert state == "FAIL"


# 13. PRD containing a conditional tax rule rewritten as universal. The
#     schema/gate layer cannot itself parse prose to detect a dropped
#     qualifier (see docs/threat-model.md's "Claim-ledger content cannot be
#     verified against the actual source" entry) -- the mechanical
#     consequence this corpus can actually test is that a regulatory claim
#     with no evidence classification at all (which a generalized, dropped-
#     qualifier claim commonly is, since a properly-qualified claim
#     requires the fuller SECONDARY_SOURCE_SUPPORTED shape) downgrades the
#     result, never passing silently.
def test_scenario_13_conditional_tax_rule_generalized_incomplete():
    state = _final_state(
        {"pm_regulatory_claim_missing_evidence_classification": True}, pack_ids=["product-management"]
    )
    assert state == "INCOMPLETE"


# 14. Content post claiming an unsupported accuracy percentage (content +
#     data-science-ml) -- exercises the core unmapped_material_claims gate
#     (schema 0.4.0) in a data-science-ml-adjacent context, not a
#     data-science-ml-specific gate, showing the two mechanisms compose.
def test_scenario_14_content_unsupported_accuracy_claim_incomplete():
    final = derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=False,
        budget_expired=False,
        acceptance_criteria_met=True,
        has_unmapped_material_claims=True,  # the accuracy % has no claim_ledger entry
    )
    assert final == "INCOMPLETE"


# 15. Multi-pack conflict requiring a user decision -- proven generically
#     (with synthetic packs, not the real official ones, since none of the
#     five official packs actually conflict with each other) in
#     tests/unit/test_pack_sdk_resolver.py::test_conflicting_completion_gates_with_equal_priority_is_ambiguous
#     and ::test_explicit_conflict_between_selected_packs_raises. Referenced
#     here rather than duplicated, per this corpus's own "test observable
#     invariants, not preferred prose" discipline -- restating an identical
#     synthetic-pack test a second time under a different name would not
#     add coverage.
def test_scenario_15_multi_pack_conflict_reference_documented():
    import tests.unit.test_pack_sdk_resolver as resolver_tests

    assert hasattr(resolver_tests, "test_conflicting_completion_gates_with_equal_priority_is_ambiguous")
    assert hasattr(resolver_tests, "test_explicit_conflict_between_selected_packs_raises")
