"""Unit tests for the smaller Domain Pack SDK modules: semver, gates,
lock determinism, and scaffold (`pack init`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from groundspec.packs.sdk import semver
from groundspec.packs.sdk.content import CompletionGate
from groundspec.packs.sdk.errors import PackManifestError
from groundspec.packs.sdk.gates import TriggeredGate, apply_pack_gates, evaluate_gates
from groundspec.packs.sdk.manifest import load_pack
from groundspec.packs.sdk.resolver import resolve
from groundspec.packs.sdk.scaffold import DestinationExists, init_pack

# --- semver ---------------------------------------------------------------


def test_semver_parse_rejects_non_strict_versions():
    with pytest.raises(semver.InvalidVersionError):
        semver.parse("1.2")
    with pytest.raises(semver.InvalidVersionError):
        semver.parse("1.2.3-rc1")


def test_semver_in_range():
    assert semver.in_range("1.2.3", min_version="1.0.0", max_version=None)
    assert semver.in_range("1.2.3", min_version="1.0.0", max_version="2.0.0")
    assert not semver.in_range("0.9.0", min_version="1.0.0", max_version=None)
    assert not semver.in_range("3.0.0", min_version="1.0.0", max_version="2.0.0")


def test_semver_range_is_possible():
    assert semver.range_is_possible(min_version="1.0.0", max_version=None)
    assert semver.range_is_possible(min_version="1.0.0", max_version="1.0.0")
    assert not semver.range_is_possible(min_version="2.0.0", max_version="1.0.0")


# --- gates ------------------------------------------------------------------


def _gate(gate_id: str, action: str, path: str = "evidence.flag") -> CompletionGate:
    return CompletionGate(
        id=gate_id,
        description="d",
        condition={"path": path, "op": "eq", "value": True},
        on_violation=action,
        rationale="r",
    )


def test_evaluate_gates_only_triggers_matching_condition():
    gates = [("pack-a", _gate("g1", "downgrade_to_incomplete"))]
    triggered = evaluate_gates(gates, contract={}, evidence={"flag": True})
    assert [t.gate_id for t in triggered] == ["g1"]

    not_triggered = evaluate_gates(gates, contract={}, evidence={"flag": False})
    assert not_triggered == []


def _triggered(action: str) -> TriggeredGate:
    return TriggeredGate(pack_id="p", gate_id="g", description="d", on_violation=action, rationale="r")


def test_apply_pack_gates_never_upgrades_past_blocked():
    triggered = [_triggered("downgrade_to_fail")]
    assert apply_pack_gates("BLOCKED", triggered) == "BLOCKED"


def test_apply_pack_gates_picks_worst_of_several():
    triggered = [
        _triggered("downgrade_to_caveats"),
        _triggered("downgrade_to_fail"),
        _triggered("downgrade_to_incomplete"),
    ]
    result = apply_pack_gates("PASS", triggered)
    assert result == "FAIL"


def test_apply_pack_gates_never_downgrades_below_incomplete_to_fail_incorrectly():
    # FAIL and INCOMPLETE rank equally severe in this project's model (both
    # "not a trustworthy PASS") -- a caveats-only trigger must never push
    # an already-FAIL state anywhere.
    result = apply_pack_gates("FAIL", [_triggered("downgrade_to_caveats")])
    assert result == "FAIL"


def test_apply_pack_gates_no_triggers_is_a_no_op():
    assert apply_pack_gates("PASS", []) == "PASS"
    assert apply_pack_gates("PASS_WITH_CAVEATS", []) == "PASS_WITH_CAVEATS"


# --- lock determinism (see test_pack_sdk_official_packs.py for a fuller
#     end-to-end version against real official packs) ---------------------


def test_lock_is_byte_identical_across_repeated_resolution():
    from groundspec.packs.sdk.lock import build_lock_document

    result1 = resolve(["software"])
    result2 = resolve(["software"])
    doc1 = build_lock_document(result1)
    doc2 = build_lock_document(result2)
    assert doc1 == doc2


def test_lock_never_contains_a_real_absolute_path():
    import re

    from groundspec.packs.sdk.lock import build_lock_document

    result = resolve(["software"])
    doc = build_lock_document(result)
    windows_drive_letter = re.compile(r"^[A-Za-z]:[\\/]")
    for entry in doc["packs"]:
        assert not entry["source"].startswith("/")
        assert not windows_drive_letter.match(entry["source"])


# --- scaffold (`pack init`) -------------------------------------------------


def test_init_pack_creates_a_structurally_valid_pack(tmp_path: Path):
    pack_dir = init_pack("my-new-pack", tmp_path)
    pack = load_pack(pack_dir, origin="project")
    assert pack.pack_id == "my-new-pack"
    assert pack.rules is not None
    assert len(pack.rules.rules) == 1


def test_init_pack_refuses_overwrite_without_force(tmp_path: Path):
    init_pack("dupe", tmp_path)
    with pytest.raises(DestinationExists):
        init_pack("dupe", tmp_path)


def test_init_pack_force_overwrites(tmp_path: Path):
    init_pack("dupe2", tmp_path)
    pack_dir = init_pack("dupe2", tmp_path, force=True)
    assert pack_dir.is_dir()


def test_init_pack_rejects_invalid_id(tmp_path: Path):
    with pytest.raises(PackManifestError):
        init_pack("Not Valid!", tmp_path)


def test_init_pack_creates_no_unnecessary_files(tmp_path: Path):
    pack_dir = init_pack("lean-pack", tmp_path)
    all_files = sorted(p.relative_to(pack_dir).as_posix() for p in pack_dir.rglob("*") if p.is_file())
    assert all_files == ["pack.toml", "references/domain-guidance.md", "rules.toml"]
