from groundspec.contract.factory import new_contract
from groundspec.contract.validator import validate_contract_dict
from groundspec.packs.registry import (
    CORE_PACK_ID,
    DOMAIN_PACK_IDS,
    RISK_OVERLAY_PACK_IDS,
    load_builtin,
    select_packs_for_contract,
)
from groundspec.rules.evaluator import applicable, evaluate_rule_set
from groundspec.rules.precedence import build_rule_set


def test_every_builtin_pack_loads():
    all_ids = [CORE_PACK_ID, *RISK_OVERLAY_PACK_IDS.values(), *DOMAIN_PACK_IDS.values()]
    for pack_id in all_ids:
        loaded = load_builtin(pack_id)
        assert loaded.pack_id == pack_id
        assert len(loaded.rules) > 0


def test_full_builtin_set_has_no_unexpected_precedence_conflicts():
    all_ids = [CORE_PACK_ID, *RISK_OVERLAY_PACK_IDS.values(), *DOMAIN_PACK_IDS.values()]
    packs = [load_builtin(pack_id) for pack_id in all_ids]
    rule_set = build_rule_set(packs)
    assert rule_set.conflicts == [], [c.explanation for c in rule_set.conflicts]
    total_rules = sum(len(p.rules) for p in packs)
    assert len(rule_set.active_rules) == total_rules


def _software_contract(risk_overlays: list[str]) -> dict:
    contract = new_contract(
        task_id="build-mvp",
        raw_user_brief="I want a food delivery app",
        normalized_problem_statement="No MVP scope or acceptance criteria exist yet for the requested app.",
        goal="Ship a walking-skeleton MVP of a food delivery app.",
        target_users=["hungry customers in one pilot city"],
        expected_deliverables=[{"name": "mvp_repo", "description": "A running MVP repository"}],
        risk_overlays=risk_overlays,
        risk_level="medium",
    )
    contract["routing"]["domain_packs"] = [{"pack_id": "software", "version": "0.1.0"}]
    contract["acceptance"]["criteria"] = [
        {
            "id": "order-flow-works",
            "description": "A user can place one order end to end",
            "priority": "must",
            "verification_method": "reproducible_command",
            "evidence_required": "test output showing the order flow test passing",
        }
    ]
    return contract


def test_pipeline_selects_domain_pack_and_applicable_rules():
    contract = _software_contract(["informational", "filesystem_mutation"])
    assert validate_contract_dict(contract) == []

    packs = select_packs_for_contract(contract)
    pack_ids = {p.pack_id for p in packs}
    assert "core-invariants" in pack_ids
    assert "risk-overlay-filesystem-mutation" in pack_ids
    assert "risk-overlay-external-communication" not in pack_ids
    assert "domain-software" in pack_ids

    rule_set = build_rule_set(packs)
    applied = evaluate_rule_set(rule_set, contract)
    applicable_hard = applicable(applied, severity="hard_constraint")
    applicable_ids = {a.qualified.fq_id for a in applicable_hard}
    assert "core-invariants:acceptance-criteria-scaled-to-risk" not in applicable_ids  # not a core rule
    assert "domain-software:acceptance-criteria-scaled-to-risk" in applicable_ids
    assert "core-invariants:preserve-user-intent" in applicable_ids
    # security-sensitive-only rule must not apply since that overlay isn't selected
    assert "domain-software:security-basics-for-user-input" not in applicable_ids


def test_unknown_domain_pack_id_raises_clear_error():
    from groundspec.packs.registry import BuiltinPackNotFound

    contract = _software_contract(["informational"])
    contract["routing"]["domain_packs"] = [{"pack_id": "underwater-basket-weaving", "version": "0.1.0"}]
    try:
        select_packs_for_contract(contract)
        raise AssertionError("expected BuiltinPackNotFound")
    except BuiltinPackNotFound:
        pass
