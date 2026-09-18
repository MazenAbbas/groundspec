"""Unit tests for the Domain Pack manifest schema and loader
(groundspec.packs.sdk.manifest), using synthetic packs under tmp_path so
these prove the *mechanism*, not just that the two shipped official packs
happen to be well-formed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from groundspec.contract.validator import validate_domain_pack_dict
from groundspec.packs.sdk.errors import PackManifestError, UnsafePackContentError
from groundspec.packs.sdk.manifest import load_pack

MIN_MANIFEST = """
domain_pack_schema_version = "0.1.0"
pack_id = "widgetry"
version = "0.1.0"
display_name = "Widgetry"
description = "A minimal test pack."

[compatibility]
min_platform_version = "1.0.0"
"""


def _write(pack_dir: Path, filename: str, content: str) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / filename).write_text(content, encoding="utf-8")


def test_minimal_manifest_validates_against_schema():
    import tomllib

    data = tomllib.loads(MIN_MANIFEST)
    assert validate_domain_pack_dict(data) == []


def test_minimal_pack_loads_with_no_rules():
    def _make(tmp_path: Path) -> Path:
        pack_dir = tmp_path / "widgetry"
        _write(pack_dir, "pack.toml", MIN_MANIFEST)
        return pack_dir

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pack_dir = _make(Path(tmp))
        pack = load_pack(pack_dir, origin="project")
        assert pack.pack_id == "widgetry"
        assert pack.rules is None
        assert pack.completion_gates == ()


def test_missing_pack_toml_raises(tmp_path: Path):
    empty_dir = tmp_path / "no-manifest"
    empty_dir.mkdir()
    with pytest.raises(PackManifestError):
        load_pack(empty_dir, origin="project")


def test_duplicate_top_level_key_rejected():
    # additionalProperties: false on the schema already rejects an unknown
    # key; this proves a completely bogus field is caught, not silently
    # ignored.
    import tomllib

    data = tomllib.loads(MIN_MANIFEST)
    data["not_a_real_field"] = True
    issues = validate_domain_pack_dict(data)
    assert len(issues) == 1
    assert issues[0].schema_rule == "additionalProperties"


def test_invalid_pack_id_rejected():
    import tomllib

    data = tomllib.loads(MIN_MANIFEST)
    data["pack_id"] = "Not Valid!"
    issues = validate_domain_pack_dict(data)
    assert len(issues) == 1
    assert issues[0].path == "pack_id"


def test_malformed_version_rejected():
    import tomllib

    data = tomllib.loads(MIN_MANIFEST)
    data["version"] = "not-a-version"
    issues = validate_domain_pack_dict(data)
    assert len(issues) == 1


def test_impossible_compatibility_range_is_schema_valid_but_resolver_rejects_it():
    # The schema itself cannot express "min > max" as a structural
    # violation (both are independently valid version strings) -- this is
    # exactly why the resolver has its own semver.range_is_possible check,
    # exercised in test_pack_sdk_resolver.py. Documented here so the
    # boundary isn't assumed away.
    import tomllib

    data = tomllib.loads(MIN_MANIFEST)
    data["compatibility"]["max_platform_version"] = "0.0.1"
    issues = validate_domain_pack_dict(data)
    assert issues == []


def test_provides_reference_escaping_pack_dir_is_rejected(tmp_path: Path):
    pack_dir = tmp_path / "escaper"
    _write(
        pack_dir,
        "pack.toml",
        MIN_MANIFEST.replace('pack_id = "widgetry"', 'pack_id = "escaper"')
        + '\n[provides]\nreferences = ["../../etc/passwd"]\n',
    )
    with pytest.raises((PackManifestError, UnsafePackContentError)):
        load_pack(pack_dir, origin="project")


def test_missing_provides_reference_is_rejected(tmp_path: Path):
    pack_dir = tmp_path / "ghost-ref"
    _write(
        pack_dir,
        "pack.toml",
        MIN_MANIFEST.replace('pack_id = "widgetry"', 'pack_id = "ghost-ref"')
        + '\n[provides]\nreferences = ["references/does-not-exist.md"]\n',
    )
    with pytest.raises(PackManifestError):
        load_pack(pack_dir, origin="project")


def test_content_hash_changes_when_a_file_changes(tmp_path: Path):
    pack_dir = tmp_path / "hashy"
    _write(pack_dir, "pack.toml", MIN_MANIFEST.replace('pack_id = "widgetry"', 'pack_id = "hashy"'))
    first = load_pack(pack_dir, origin="project").content_hash

    changed = MIN_MANIFEST.replace('pack_id = "widgetry"', 'pack_id = "hashy"') + "\n# comment\n"
    _write(pack_dir, "pack.toml", changed)
    second = load_pack(pack_dir, origin="project").content_hash

    assert first != second


def test_content_hash_is_stable_for_identical_content(tmp_path: Path):
    pack_dir_a = tmp_path / "a" / "stable"
    pack_dir_b = tmp_path / "b" / "stable"
    _write(pack_dir_a, "pack.toml", MIN_MANIFEST.replace('pack_id = "widgetry"', 'pack_id = "stable"'))
    _write(pack_dir_b, "pack.toml", MIN_MANIFEST.replace('pack_id = "widgetry"', 'pack_id = "stable"'))
    hash_a = load_pack(pack_dir_a, origin="project").content_hash
    hash_b = load_pack(pack_dir_b, origin="project").content_hash
    assert hash_a == hash_b
