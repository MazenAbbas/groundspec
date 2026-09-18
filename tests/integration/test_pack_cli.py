"""Integration tests for `groundspec pack <subcommand>` via the real CLI
entry point (groundspec.cli.main.main), matching the style of
tests/integration/test_cli.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from groundspec.cli.main import main


def run(argv: list[str]) -> int:
    return main(argv)


def test_pack_list_exits_zero_and_includes_official_packs(capsys):
    assert run(["pack", "list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    ids = {r["pack_id"] for r in rows}
    assert {"software", "research", "content", "product-management", "data-science-ml"} <= ids
    assert all(r["official"] for r in rows if r["pack_id"] in {"software", "product-management"})


def test_pack_inspect_json_report_has_no_absolute_paths(capsys):
    assert run(["pack", "inspect", "product-management", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["pack_id"] == "product-management"
    assert report["content_hash"].startswith("sha256:")
    serialized = json.dumps(report)
    assert "C:\\" not in serialized
    assert "/home/" not in serialized
    assert "/Users/" not in serialized


def test_pack_inspect_unknown_pack_fails_cleanly():
    assert run(["pack", "inspect", "totally-unknown-pack-xyz"]) == 2


def test_pack_validate_official_pack_by_id():
    assert run(["pack", "validate", "software"]) == 0
    assert run(["pack", "validate", "data-science-ml"]) == 0


def test_pack_validate_bare_rule_pack_file_still_works(tmp_path: Path):
    # Backward compatibility: the pre-SDK single-file rule pack path (used
    # for project-level rule packs before the Domain Pack SDK existed)
    # must keep working exactly as it always did.
    bare = tmp_path / "my-project-pack.toml"
    bare.write_text(
        """rule_pack_schema_version = "0.1.0"
pack_id = "my-project-pack"
version = "0.1.0"
layer = "project"
title = "t"

[[rules]]
id = "r1"
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
""",
        encoding="utf-8",
    )
    assert run(["pack", "validate", str(bare)]) == 0


def test_pack_validate_nonexistent_path_or_id_fails():
    assert run(["pack", "validate", "definitely-not-a-real-thing.toml"]) == 2


def test_pack_init_then_validate_round_trip(tmp_path: Path):
    assert run(["pack", "init", "test-init-pack", "--output", str(tmp_path)]) == 0
    assert run(["pack", "validate", str(tmp_path / "test-init-pack")]) == 0


def test_pack_init_refuses_overwrite_without_force(tmp_path: Path):
    assert run(["pack", "init", "dupe-cli", "--output", str(tmp_path)]) == 0
    assert run(["pack", "init", "dupe-cli", "--output", str(tmp_path)]) == 1
    assert run(["pack", "init", "dupe-cli", "--output", str(tmp_path), "--force"]) == 0


def test_pack_resolve_json_output(capsys):
    assert run(["pack", "resolve", "--pack", "software", "--pack", "research", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert {e["pack_id"] for e in report["selected"]} == {"software", "research"}


def test_pack_resolve_reports_conflict_with_nonzero_exit(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".groundspec" / "packs" / "software").mkdir(parents=True)
    (tmp_path / ".groundspec" / "packs" / "software" / "pack.toml").write_text(
        """domain_pack_schema_version = "0.1.0"
pack_id = "software"
version = "0.1.0"
display_name = "fake"
description = "shadow attempt"

[compatibility]
min_platform_version = "1.0.0"
""",
        encoding="utf-8",
    )
    assert run(["pack", "resolve", "--pack", "software"]) == 1


def test_pack_test_runs_official_pack_scenarios():
    assert run(["pack", "test", "product-management"]) == 0
    assert run(["pack", "test", "data-science-ml"]) == 0


def test_pack_lock_writes_deterministic_file(tmp_path: Path):
    out1 = tmp_path / "a.lock"
    out2 = tmp_path / "b.lock"
    assert run(["pack", "lock", "--pack", "software", "--out", str(out1)]) == 0
    assert run(["pack", "lock", "--pack", "software", "--out", str(out2)]) == 0
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


def test_pack_lock_requires_at_least_one_pack():
    # argparse's own `required=True` on --pack raises SystemExit(2) before
    # cmd_pack_lock's own defensive "no packs" check would even run.
    with pytest.raises(SystemExit) as exc:
        run(["pack", "lock"])
    assert exc.value.code == 2
