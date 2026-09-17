import json
from pathlib import Path

import pytest

from groundspec.rules.errors import (
    CyclicImport,
    DuplicateRuleId,
    ImportDepthExceeded,
    PackNotFound,
    PackVersionMismatch,
)
from groundspec.rules.pack_loader import flatten, resolve_pack


def _rule(rule_id: str, **overrides: object) -> dict[str, object]:
    base = {
        "id": rule_id,
        "version": "0.1.0",
        "title": f"Rule {rule_id}",
        "purpose": "test purpose",
        "scope": "test scope",
        "applies_when": True,
        "severity": "advisory",
        "requirement": "do the thing",
        "verification_method": "manual_inspection",
        "evidence_requirement": "a note saying it was done",
        "failure_behavior": "warn_only",
        "source_or_rationale": "unit test fixture",
    }
    base.update(overrides)
    return base


def _pack(
    pack_id: str,
    layer: str,
    rules: list[dict[str, object]],
    imports: list[dict[str, str]] | None = None,
):
    return {
        "rule_pack_schema_version": "0.1.0",
        "pack_id": pack_id,
        "version": "0.1.0",
        "layer": layer,
        "title": pack_id,
        "rules": rules,
        "imports": imports or [],
    }


def _write(dir_: Path, pack: dict[str, object]) -> Path:
    path = dir_ / f"{pack['pack_id']}.json"
    path.write_text(json.dumps(pack), encoding="utf-8")
    return path


def test_resolve_simple_pack_with_no_imports(tmp_path: Path):
    entry = _write(tmp_path, _pack("solo", "core", [_rule("r1")]))
    loaded = resolve_pack(entry, search_dirs=[tmp_path])
    assert loaded.pack_id == "solo"
    assert len(loaded.rules) == 1


def test_resolve_follows_imports(tmp_path: Path):
    _write(tmp_path, _pack("base", "core", [_rule("r1")]))
    entry = _write(
        tmp_path,
        _pack("child", "domain", [_rule("r2")], imports=[{"pack_id": "base", "version": "0.1.0"}]),
    )
    loaded = resolve_pack(entry, search_dirs=[tmp_path])
    all_packs = flatten(loaded)
    assert {p.pack_id for p in all_packs} == {"child", "base"}


def test_missing_import_raises_pack_not_found(tmp_path: Path):
    entry = _write(
        tmp_path,
        _pack("child", "domain", [_rule("r2")], imports=[{"pack_id": "ghost", "version": "0.1.0"}]),
    )
    with pytest.raises(PackNotFound):
        resolve_pack(entry, search_dirs=[tmp_path])


def test_version_mismatch_raises(tmp_path: Path):
    _write(tmp_path, _pack("base", "core", [_rule("r1")]))
    entry = _write(
        tmp_path,
        _pack("child", "domain", [_rule("r2")], imports=[{"pack_id": "base", "version": "9.9.9"}]),
    )
    with pytest.raises(PackVersionMismatch):
        resolve_pack(entry, search_dirs=[tmp_path])


def test_cyclic_import_raises(tmp_path: Path):
    _write(
        tmp_path,
        _pack("pack-a", "domain", [_rule("ra")], imports=[{"pack_id": "pack-b", "version": "0.1.0"}]),
    )
    entry = _write(
        tmp_path,
        _pack("pack-b", "domain", [_rule("rb")], imports=[{"pack_id": "pack-a", "version": "0.1.0"}]),
    )
    with pytest.raises(CyclicImport):
        resolve_pack(entry, search_dirs=[tmp_path])


def test_import_depth_exceeded(tmp_path: Path):
    # chain of 6 packs, each importing the next: exceeds default depth of 4
    for i in range(6):
        imports = [{"pack_id": f"p{i + 1}", "version": "0.1.0"}] if i < 5 else []
        _write(tmp_path, _pack(f"p{i}", "domain", [_rule(f"r{i}")], imports=imports))
    with pytest.raises(ImportDepthExceeded):
        resolve_pack(tmp_path / "p0.json", search_dirs=[tmp_path], max_import_depth=4)


def test_duplicate_rule_id_within_pack_raises(tmp_path: Path):
    entry = _write(tmp_path, _pack("dup", "core", [_rule("same"), _rule("same")]))
    with pytest.raises(DuplicateRuleId):
        resolve_pack(entry, search_dirs=[tmp_path])


def test_pack_id_cannot_traverse_directories():
    # Enforced structurally: pack_id regex forbids '/' so a crafted
    # {"pack_id": "../../etc/passwd"} import reference cannot ever resolve
    # outside the search directories -- the schema itself is the control.
    from groundspec.contract.validator import validate_rule_pack_dict

    pack = _pack("evil", "project", [_rule("r1")], imports=[{"pack_id": "../secret", "version": "0.1.0"}])
    issues = validate_rule_pack_dict(pack)
    assert issues, "path-traversal-shaped pack_id must fail schema validation"
