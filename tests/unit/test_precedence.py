import pytest

from groundspec.rules.errors import DuplicatePackId
from groundspec.rules.pack_loader import LoadedPack
from groundspec.rules.precedence import build_rule_set


def _rule(rule_id: str, requirement: str, conflict_key: str = "") -> dict[str, object]:
    return {
        "id": rule_id,
        "version": "0.1.0",
        "title": rule_id,
        "purpose": "p",
        "scope": "s",
        "applies_when": True,
        "severity": "advisory",
        "requirement": requirement,
        "verification_method": "manual_inspection",
        "evidence_requirement": "e",
        "failure_behavior": "warn_only",
        "source_or_rationale": "r",
        "conflict_key": conflict_key,
    }


def test_non_conflicting_rules_all_survive():
    core = LoadedPack("core", "0.1.0", "core", "core", [_rule("c1", "be honest")])
    domain = LoadedPack("dom", "0.1.0", "domain", "dom", [_rule("d1", "write tests")])
    result = build_rule_set([core, domain])
    assert len(result.active_rules) == 2
    assert result.conflicts == []


def test_higher_layer_wins_conflict():
    core = LoadedPack("core", "0.1.0", "core", "core", [_rule("c1", "formal tone", conflict_key="tone")])
    domain = LoadedPack(
        "dom", "0.1.0", "domain", "dom", [_rule("d1", "casual tone", conflict_key="tone")]
    )
    result = build_rule_set([core, domain])
    winners = {r.fq_id for r in result.active_rules}
    assert "core:c1" in winners
    assert "dom:d1" not in winners
    assert len(result.conflicts) == 1
    assert "core" in result.conflicts[0].explanation


def test_agreeing_rules_are_not_a_conflict():
    core = LoadedPack("core", "0.1.0", "core", "core", [_rule("c1", "be concise", conflict_key="tone")])
    domain = LoadedPack("dom", "0.1.0", "domain", "dom", [_rule("d1", "be concise", conflict_key="tone")])
    result = build_rule_set([core, domain])
    assert len(result.active_rules) == 2
    assert result.conflicts == []


def test_same_layer_conflict_is_tie_broken_deterministically_and_flagged():
    a = LoadedPack("aa", "0.1.0", "domain", "aa", [_rule("r1", "use tabs", conflict_key="indent")])
    b = LoadedPack("bb", "0.1.0", "domain", "bb", [_rule("r1", "use spaces", conflict_key="indent")])
    result = build_rule_set([a, b])
    assert len(result.conflicts) == 1
    # deterministic: alphabetically-first pack_id wins among same-layer candidates
    assert result.conflicts[0].winner.pack_id == "aa"


def test_duplicate_pack_id_with_different_content_raises():
    a = LoadedPack("x", "0.1.0", "domain", "x", [_rule("r1", "a")])
    b = LoadedPack("x", "0.1.0", "domain", "x", [_rule("r1", "b")])
    with pytest.raises(DuplicatePackId):
        build_rule_set([a, b])


def test_deprecated_rules_are_excluded():
    rule = _rule("c1", "old requirement")
    rule["status"] = "deprecated"
    core = LoadedPack("core", "0.1.0", "core", "core", [rule])
    result = build_rule_set([core])
    assert result.active_rules == []
