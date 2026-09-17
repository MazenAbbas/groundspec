"""Validates the three constructed Meta-Skill examples (Phase 5/7): real
contracts, run through the real deterministic engine, checked for the
observable artifacts the task calls for (valid contract, selected packs,
assumptions, blocking/high-value questions, acceptance criteria, absence of
unauthorized actions). See each example's session-notes.md for the explicit
"constructed, not a live model run" label -- examples/metaskill/README.md
explains the distinction from 03-software-csv-export.
"""

from pathlib import Path

from groundspec.contract.serialization import load_document
from groundspec.contract.validator import validate_contract_dict
from groundspec.packs.registry import select_packs_for_contract
from groundspec.rules.precedence import build_rule_set

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples" / "metaskill"

CONSTRUCTED_SLUGS = [
    "01-food-delivery-ksa-university-prd",
    "02-image-dataset-validation-approaches",
    "04-audit-linkedin-launch-post",
]


def _load(slug: str) -> dict:
    return load_document(EXAMPLES_DIR / slug / "contract.toml")


def test_every_constructed_example_has_session_notes_disclosing_provenance():
    for slug in CONSTRUCTED_SLUGS:
        notes = (EXAMPLES_DIR / slug / "session-notes.md").read_text(encoding="utf-8")
        assert "constructed" in notes.lower()
        assert "not" in notes.lower() and "live model run" in notes.lower()


def test_every_constructed_example_is_schema_valid_and_resolves_packs():
    for slug in CONSTRUCTED_SLUGS:
        contract = _load(slug)
        issues = validate_contract_dict(contract)
        assert issues == [], f"{slug}: {[str(i) for i in issues]}"
        packs = select_packs_for_contract(contract)
        rule_set = build_rule_set(packs)
        assert rule_set.active_rules  # at least core invariants applied


def test_01_food_delivery_selects_multiple_domain_packs_and_has_ranked_risk_questions():
    contract = _load("01-food-delivery-ksa-university-prd")
    domain_ids = {p["pack_id"] for p in contract["routing"]["domain_packs"]}
    assert domain_ids == {"software", "research"}
    assumptions = contract["scope"]["assumptions"]
    assert len(assumptions) >= 2
    for a in assumptions:
        assert a["confidence"] in ("low", "medium", "high")
    high_value = [q for q in contract["scope"]["open_questions"] if q["classification"] == "high_value"]
    assert len(high_value) >= 2
    must_criteria = [c for c in contract["acceptance"]["criteria"] if c["priority"] == "must"]
    assert len(must_criteria) >= 3


def test_01_does_not_authorize_any_external_action():
    contract = _load("01-food-delivery-ksa-university-prd")
    auth = contract["routing"]["authorization"]
    assert auth["granted_permissions"] == []
    assert contract["routing"]["risk_overlays"] == ["informational"]


def test_02_research_records_a_resolved_blocking_question_with_stated_rationale():
    contract = _load("02-image-dataset-validation-approaches")
    blocking = [q for q in contract["scope"]["open_questions"] if q["classification"] == "blocking"]
    assert len(blocking) == 1
    assert blocking[0]["resolution_status"] == "answered"
    assert blocking[0]["answer"]
    assert contract["budget"]["time_budget_minutes"] == 240


def test_04_audit_does_not_modify_non_goal_and_flags_fabricated_urgency():
    contract = _load("04-audit-linkedin-launch-post")
    assert any("rewrit" in ng.lower() or "publish" in ng.lower() for ng in contract["scope"]["non_goals"])
    criteria_ids = {c["id"] for c in contract["acceptance"]["criteria"]}
    assert "fabricated-urgency-flagged" in criteria_ids
    assert "external_communication" in contract["routing"]["risk_overlays"]
    # Audit mode: only 'informational'-shaped authorization, nothing granted to publish/act.
    assert contract["routing"]["authorization"]["granted_permissions"] == []
