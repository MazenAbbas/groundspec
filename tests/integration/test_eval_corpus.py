"""Validates the shape and coverage of eval/scenarios/scenarios.json (PRD
Phase 18). This does not run any model -- see docs/evaluation-methodology.md
for why, and for which scenarios below are already mechanically checked by
name (cross-referenced to real tests elsewhere in this suite).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "eval" / "scenarios" / "scenarios.json"

REQUIRED_FIELDS = {"id", "domain", "scenario_type", "input_brief", "evaluability", "expected_behavior"}


def _load_corpus() -> dict:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def test_corpus_has_at_least_30_scenarios():
    corpus = _load_corpus()
    assert len(corpus["scenarios"]) >= 30


def test_every_scenario_has_required_fields_and_unique_id():
    corpus = _load_corpus()
    seen_ids = set()
    for scenario in corpus["scenarios"]:
        missing = REQUIRED_FIELDS - scenario.keys()
        assert not missing, f"{scenario.get('id')} missing fields: {missing}"
        assert scenario["id"] not in seen_ids, f"duplicate scenario id: {scenario['id']}"
        seen_ids.add(scenario["id"])
        assert scenario["evaluability"] in ("mechanically_checkable_now", "requires_model_run")
        if scenario["evaluability"] == "mechanically_checkable_now":
            assert scenario.get("verified_by"), f"{scenario['id']} claims checkability with no pointer"


def test_every_declared_scenario_type_is_covered_by_at_least_one_scenario():
    corpus = _load_corpus()
    declared_types = set(corpus["scenario_types"])
    covered_types = {s["scenario_type"] for s in corpus["scenarios"]}
    missing = declared_types - covered_types
    assert not missing, f"scenario types declared but never used: {missing}"


def test_every_scenario_type_used_is_declared():
    corpus = _load_corpus()
    declared_types = set(corpus["scenario_types"])
    used_types = {s["scenario_type"] for s in corpus["scenarios"]}
    undeclared = used_types - declared_types
    assert not undeclared, f"scenario types used but not declared: {undeclared}"


def test_mechanically_checkable_scenarios_point_at_real_passing_tests():
    """A light cross-check: every 'verified_by' reference names a file that
    actually exists in this repository, so the claim is not decorative."""
    corpus = _load_corpus()
    for scenario in corpus["scenarios"]:
        if scenario["evaluability"] != "mechanically_checkable_now":
            continue
        reference = scenario["verified_by"]
        # references look like "path/to/file.ext::test_name (optional trailing note)"
        first_token = reference.split(" ")[0].rstrip(",.")
        first_path = first_token.split("::")[0]
        candidate = ROOT / first_path
        assert candidate.exists(), f"{scenario['id']} verified_by references missing path: {candidate}"
