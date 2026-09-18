"""Unit tests for groundspec.packs.sdk.resolver, built entirely on
synthetic packs under tmp_path -- these prove the composition mechanism
generically (dependencies, version ranges, conflicts, cycles, shadowing,
cross-pack rule/gate collisions), not just that the two shipped official
packs happen to compose cleanly (see test_pack_sdk_official_packs.py for
that separate, narrower claim).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from groundspec.packs.sdk.errors import (
    PackCompositionAmbiguousError,
    PackCompositionInvalidError,
    PackDependencyCycleError,
    PackNotFoundError,
    PackVersionRangeError,
)
from groundspec.packs.sdk.resolver import resolve


def _pack(
    root: Path,
    pack_id: str,
    *,
    origin_dir: str,
    version: str = "0.1.0",
    dependencies: str = "",
    conflicts: str = "",
    priority: int = 0,
    rules: list[str] | None = None,
    gates: list[tuple[str, str, str]] | None = None,  # (gate_id, condition_toml, on_violation)
) -> None:
    pack_dir = root / origin_dir / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)
    provides_lines = []
    if rules is not None:
        rules_body = "\n".join(
            f"""
[[rules]]
id = "{rid}"
version = "0.1.0"
title = "t"
purpose = "p"
scope = "s"
applies_when = true
severity = "advisory"
requirement = "r"
verification_method = "manual_inspection"
evidence_requirement = "e"
failure_behavior = "warn_only"
source_or_rationale = "x"
"""
            for rid in rules
        )
        (pack_dir / "rules.toml").write_text(
            f"""rule_pack_schema_version = "0.1.0"
pack_id = "{pack_id}"
version = "{version}"
layer = "domain"
title = "t"
{rules_body}
""",
            encoding="utf-8",
        )
        provides_lines.append('rules = "rules.toml"')
    if gates is not None:
        gates_body = "\n".join(
            f"""
[[gates]]
id = "{gid}"
description = "d"
condition = {cond}
on_violation = "{action}"
rationale = "r"
"""
            for gid, cond, action in gates
        )
        (pack_dir / "completion-gates.toml").write_text(
            f'domain_pack_schema_version = "0.1.0"\npack_id = "{pack_id}"\n{gates_body}\n',
            encoding="utf-8",
        )
        provides_lines.append('completion_gates = "completion-gates.toml"')

    (pack_dir / "pack.toml").write_text(
        f"""domain_pack_schema_version = "0.1.0"
pack_id = "{pack_id}"
version = "{version}"
display_name = "{pack_id}"
description = "test pack"
priority = {priority}

[compatibility]
min_platform_version = "1.0.0"

{dependencies}
{conflicts}

[provides]
{chr(10).join(provides_lines)}
""",
        encoding="utf-8",
    )


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Resolver discovery looks at official (the real installed packs) +
    # project (.groundspec/packs under project_root) + user (~/.groundspec,
    # redirected to an empty tmp dir so a real developer machine's user
    # packs never leak into these tests).
    monkeypatch.setattr("groundspec.packs.sdk.discovery.Path.home", lambda: tmp_path / "empty-home")
    return tmp_path


def _project_packs_dir(project_root: Path) -> Path:
    return project_root / ".groundspec" / "packs"


def test_resolve_a_single_project_pack(project_root: Path):
    _pack(_project_packs_dir(project_root), "alpha", origin_dir=".", rules=["alpha-rule"])
    result = resolve(["alpha"], project_root=project_root)
    assert result.ok
    assert [e.pack.pack_id for e in result.selected] == ["alpha"]


def test_unknown_pack_id_raises():
    with pytest.raises(PackNotFoundError):
        resolve(["totally-nonexistent-pack-xyz"])


def test_dependency_closure_is_pulled_in(project_root: Path):
    base = _project_packs_dir(project_root)
    _pack(base, "base", origin_dir=".", rules=["base-rule"])
    _pack(
        base,
        "top",
        origin_dir=".",
        dependencies='[[dependencies]]\npack_id = "base"\nmin_version = "0.1.0"',
        rules=["top-rule"],
    )
    result = resolve(["top"], project_root=project_root)
    assert result.ok
    ids = {e.pack.pack_id for e in result.selected}
    assert ids == {"top", "base"}
    base_entry = next(e for e in result.selected if e.pack.pack_id == "base")
    assert base_entry.requested is False


def test_impossible_dependency_range_raises(project_root: Path):
    base = _project_packs_dir(project_root)
    _pack(base, "base", origin_dir=".", rules=["base-rule"])
    _pack(
        base,
        "top",
        origin_dir=".",
        dependencies='[[dependencies]]\npack_id = "base"\nmin_version = "5.0.0"\nmax_version = "1.0.0"',
        rules=["top-rule"],
    )
    with pytest.raises(PackVersionRangeError):
        resolve(["top"], project_root=project_root)


def test_unsatisfied_dependency_version_range_raises(project_root: Path):
    base = _project_packs_dir(project_root)
    _pack(base, "base", origin_dir=".", version="0.1.0", rules=["base-rule"])
    _pack(
        base,
        "top",
        origin_dir=".",
        dependencies='[[dependencies]]\npack_id = "base"\nmin_version = "9.0.0"',
        rules=["top-rule"],
    )
    with pytest.raises(PackVersionRangeError):
        resolve(["top"], project_root=project_root)


def test_dependency_cycle_raises(project_root: Path):
    base = _project_packs_dir(project_root)
    _pack(
        base, "pack-a", origin_dir=".",
        dependencies='[[dependencies]]\npack_id = "pack-b"\nmin_version = "0.1.0"',
        rules=["a-rule"],
    )
    _pack(
        base, "pack-b", origin_dir=".",
        dependencies='[[dependencies]]\npack_id = "pack-a"\nmin_version = "0.1.0"',
        rules=["b-rule"],
    )
    with pytest.raises(PackDependencyCycleError):
        resolve(["pack-a"], project_root=project_root)


def test_excessively_deep_dependency_chain_is_rejected(project_root: Path):
    # An acyclic but very deep chain -- cycle detection alone would not
    # catch this; a separate depth ceiling (resolver.MAX_DEPENDENCY_DEPTH)
    # does. Defense in depth against denial-of-service, see
    # docs/threat-model.md.
    from groundspec.packs.sdk.resolver import MAX_DEPENDENCY_DEPTH

    base = _project_packs_dir(project_root)
    chain_length = MAX_DEPENDENCY_DEPTH + 3
    for i in range(chain_length):
        deps = ""
        if i > 0:
            deps = f'[[dependencies]]\npack_id = "chain-{i - 1}"\nmin_version = "0.1.0"'
        _pack(base, f"chain-{i}", origin_dir=".", dependencies=deps, rules=[f"chain-{i}-rule"])
    with pytest.raises(PackDependencyCycleError):
        resolve([f"chain-{chain_length - 1}"], project_root=project_root)


def test_explicit_conflict_between_selected_packs_raises(project_root: Path):
    base = _project_packs_dir(project_root)
    _pack(base, "left", origin_dir=".", rules=["left-rule"])
    _pack(
        base,
        "right",
        origin_dir=".",
        conflicts='[[conflicts]]\npack_id = "left"\nreason = "philosophically incompatible"',
        rules=["right-rule"],
    )
    with pytest.raises(PackCompositionInvalidError):
        resolve(["left", "right"], project_root=project_root)


def test_no_conflict_when_conflicting_pack_not_actually_selected(project_root: Path):
    base = _project_packs_dir(project_root)
    _pack(base, "left", origin_dir=".", rules=["left-rule"])
    _pack(
        base,
        "right",
        origin_dir=".",
        conflicts='[[conflicts]]\npack_id = "left"\nreason = "philosophically incompatible"',
        rules=["right-rule"],
    )
    result = resolve(["right"], project_root=project_root)
    assert result.ok


def test_cross_pack_duplicate_rule_id_raises(project_root: Path):
    base = _project_packs_dir(project_root)
    _pack(base, "left", origin_dir=".", rules=["shared-id"])
    _pack(base, "right", origin_dir=".", rules=["shared-id"])
    with pytest.raises(PackCompositionInvalidError):
        resolve(["left", "right"], project_root=project_root)


def test_official_pack_cannot_be_silently_shadowed(project_root: Path):
    # "software" is a real official pack id -- a project pack claiming the
    # same id must never be silently substituted.
    _pack(_project_packs_dir(project_root), "software", origin_dir=".", rules=["fake-rule"])
    with pytest.raises(PackCompositionInvalidError):
        resolve(["software"], project_root=project_root)


def test_official_pack_can_be_shadowed_with_explicit_override(project_root: Path):
    _pack(_project_packs_dir(project_root), "software", origin_dir=".", rules=["fake-rule"])
    result = resolve(["software"], project_root=project_root, allow_shadow=frozenset({"software"}))
    assert result.ok
    entry = result.selected[0]
    assert entry.pack.pack_id == "software"
    assert entry.pack.origin == "project"  # project wins the shadow per documented precedence
    shadow_conflicts = [c for c in result.conflicts if c.kind == "shadow"]
    assert len(shadow_conflicts) == 1
    assert shadow_conflicts[0].classification == "resolvable_by_precedence"


_SHARED_CONDITION = '{ path = "evidence.x", op = "eq", value = true }'


def test_compatible_completion_gates_from_different_packs_merge_silently(project_root: Path):
    base = _project_packs_dir(project_root)
    same_gate = [("shared-gate", _SHARED_CONDITION, "downgrade_to_incomplete")]
    _pack(base, "left", origin_dir=".", gates=same_gate)
    _pack(base, "right", origin_dir=".", gates=same_gate)
    result = resolve(["left", "right"], project_root=project_root)
    assert result.ok
    assert not any(c.kind == "completion_gate_collision" for c in result.conflicts)


def test_conflicting_completion_gates_resolved_by_priority(project_root: Path):
    base = _project_packs_dir(project_root)
    _pack(
        base, "low-priority", origin_dir=".", priority=0,
        gates=[("shared-gate", _SHARED_CONDITION, "downgrade_to_incomplete")],
    )
    _pack(
        base, "high-priority", origin_dir=".", priority=10,
        gates=[("shared-gate", _SHARED_CONDITION, "downgrade_to_fail")],
    )
    result = resolve(["low-priority", "high-priority"], project_root=project_root)
    assert result.ok
    collision = next(c for c in result.conflicts if c.kind == "completion_gate_collision")
    assert collision.classification == "resolvable_by_precedence"
    assert "high-priority" in collision.message


def test_conflicting_completion_gates_with_equal_priority_is_ambiguous(project_root: Path):
    base = _project_packs_dir(project_root)
    _pack(
        base, "left", origin_dir=".", priority=0,
        gates=[("shared-gate", _SHARED_CONDITION, "downgrade_to_incomplete")],
    )
    _pack(
        base, "right", origin_dir=".", priority=0,
        gates=[("shared-gate", _SHARED_CONDITION, "downgrade_to_fail")],
    )
    with pytest.raises(PackCompositionAmbiguousError):
        resolve(["left", "right"], project_root=project_root)
