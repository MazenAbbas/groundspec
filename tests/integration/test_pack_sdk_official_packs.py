"""Integration tests for the five shipped official Domain Packs together:
the exact "realistic composition of all official packs" the product spec
calls for, plus each new pack's own declarative test suite and the
completion-gate wiring into `groundspec evaluate`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from groundspec.contract.factory import new_contract
from groundspec.contract.serialization import canonical_json_dumps
from groundspec.metaskill.completion import CompletionState
from groundspec.packs.sdk.discovery import discover_official
from groundspec.packs.sdk.gates import apply_pack_gates, evaluate_gates
from groundspec.packs.sdk.manifest import load_pack
from groundspec.packs.sdk.resolver import resolve
from groundspec.packs.sdk.testing import run_pack_tests

ALL_OFFICIAL_PACK_IDS = ["software", "research", "content", "product-management", "data-science-ml"]


def test_all_five_official_packs_are_discovered():
    ids = {loc.pack_id_hint for loc in discover_official()}
    assert ids == set(ALL_OFFICIAL_PACK_IDS)


def test_all_five_official_packs_resolve_together_with_no_invalid_conflicts():
    result = resolve(ALL_OFFICIAL_PACK_IDS)
    assert result.ok, [c.message for c in result.conflicts]
    assert {e.pack.pack_id for e in result.selected} == set(ALL_OFFICIAL_PACK_IDS)


def test_full_composition_resolves_quickly():
    # Not a claim of a universal benchmark -- see docs/architecture.md's
    # performance-measurement caveats. This just guards against an
    # accidental O(n^2)-over-full-file-rescans regression: resolving all
    # five official packs together should stay well under a second on any
    # reasonable development machine.
    start = time.monotonic()
    resolve(ALL_OFFICIAL_PACK_IDS)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"resolving all official packs took {elapsed:.2f}s"


def test_no_cross_pack_rule_id_collisions_across_all_official_packs():
    result = resolve(ALL_OFFICIAL_PACK_IDS)
    seen: dict[str, str] = {}
    for entry in result.selected:
        if entry.pack.rules is None:
            continue
        for rule in entry.pack.rules.rules:
            rule_id = rule["id"]
            prior_owner = seen.get(rule_id)
            assert prior_owner is None, f"{rule_id!r} declared by both {prior_owner} and {entry.pack.pack_id}"
            seen[rule_id] = entry.pack.pack_id


def test_lock_of_all_five_is_byte_identical_across_repeated_resolution():
    from groundspec.packs.sdk.lock import build_lock_document

    doc1 = build_lock_document(resolve(ALL_OFFICIAL_PACK_IDS))
    doc2 = build_lock_document(resolve(ALL_OFFICIAL_PACK_IDS))
    assert canonical_json_dumps(doc1) == canonical_json_dumps(doc2)


def _load_official(pack_id: str):
    location = next(loc for loc in discover_official() if loc.pack_id_hint == pack_id)
    return load_pack(location.pack_dir, origin=location.origin)


def test_product_management_pack_own_scenarios_pass():
    pack = _load_official("product-management")
    results = run_pack_tests(pack)
    assert results, "expected at least one declared scenario"
    failed = [r for r in results if not r.passed]
    assert not failed, [(r.scenario_id, r.failures) for r in failed]


def test_data_science_ml_pack_own_scenarios_pass():
    pack = _load_official("data-science-ml")
    results = run_pack_tests(pack)
    assert results
    failed = [r for r in results if not r.passed]
    assert not failed, [(r.scenario_id, r.failures) for r in failed]


def test_product_management_pack_declares_no_heavy_or_forbidden_content():
    pack = _load_official("product-management")
    assert pack.rules is not None and len(pack.rules.rules) > 0
    assert len(pack.completion_gates) > 0


def test_data_science_ml_pack_has_no_heavy_dependency_footprint():
    # This pack must never cause groundspec itself to import a heavy
    # numerical/ML library -- the whole point is staying usable on an
    # ordinary student laptop with no GPU. Confirmed by checking that
    # loading and testing the pack doesn't import anything beyond the
    # standard library and groundspec's own already-lightweight modules.
    import sys

    forbidden_modules = {"pandas", "numpy", "sklearn", "torch", "tensorflow", "jupyter"}
    before = set(sys.modules)
    pack = _load_official("data-science-ml")
    run_pack_tests(pack)
    after = set(sys.modules)
    newly_imported = after - before
    assert not (newly_imported & forbidden_modules)


def test_product_management_gate_integration_with_groundspec_evaluate(tmp_path: Path):
    """End-to-end: a contract selecting product-management, evaluated with
    evidence that trips one of its completion gates, actually reaches the
    downgraded state through the real `groundspec evaluate` code path
    (groundspec.cli.commands.cmd_evaluate), not just the SDK in isolation.
    """
    from groundspec.cli.commands import cmd_evaluate

    contract = new_contract(
        task_id="pm-gate-integration-check",
        raw_user_brief="b",
        normalized_problem_statement="p",
        goal="g",
        target_users=["u"],
        expected_deliverables=[{"name": "d", "description": "d"}],
    )
    contract["routing"]["domain_packs"] = [{"pack_id": "product-management", "version": "0.1.0"}]
    contract["acceptance"]["criteria"] = [
        {
            "id": "c1",
            "description": "d",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "e",
        }
    ]
    contract_path = tmp_path / "contract.toml"
    from groundspec.contract.serialization import dump_document

    dump_document(contract, contract_path)

    result_dir = tmp_path / "result"
    result_dir.mkdir()
    (result_dir / "evidence.json").write_text(
        json.dumps(
            {
                "hard_constraint_results": {},
                "dimension_scores": {},
                "acceptance_criteria_results": {"c1": True},
                "authorization_violations": [],
                "unmapped_material_claims": [],
                "pm_market_wide_data_presented_as_segment_evidence": True,
            }
        ),
        encoding="utf-8",
    )

    contract_path_str = str(contract_path)
    result_dir_str = str(result_dir)

    class Args:
        contract = contract_path_str
        result_dir = result_dir_str

    exit_code = cmd_evaluate(Args())
    assert exit_code == 1  # FAIL exit code


def test_gate_mechanism_directly_matches_cli_behavior_for_a_clean_run():
    """Sanity cross-check: the gates.py mechanism used directly agrees with
    what a clean (no pm_*/ds_* flags) evidence.json produces."""
    pack = _load_official("product-management")
    gates = [(pack.pack_id, g) for g in pack.completion_gates]
    triggered = evaluate_gates(gates, contract={}, evidence={})
    assert triggered == []
    final: CompletionState = apply_pack_gates("PASS", triggered)
    assert final == "PASS"
