import json
from pathlib import Path

import pytest

from groundspec.cli.main import main


def run(argv: list[str]) -> int:
    return main(argv)


def test_doctor_exits_zero():
    assert run(["doctor"]) == 0


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        run(["--version"])
    assert exc.value.code == 0
    assert "groundspec" in capsys.readouterr().out


def test_init_is_idempotent(tmp_path: Path, capsys):
    assert run(["init", str(tmp_path)]) == 0
    assert (tmp_path / ".groundspec" / "config.toml").is_file()
    assert run(["init", str(tmp_path)]) == 0
    assert "already exists" in capsys.readouterr().out


def test_create_validate_compile_audit_roundtrip(tmp_path: Path):
    contract_path = tmp_path / "demo.toml"
    rc = run(
        [
            "create",
            "--task-id",
            "demo-task",
            "--brief",
            "write a blog post",
            "--goal",
            "produce a 500 word blog post",
            "--user",
            "readers",
            "--deliverable",
            "post:the blog post text",
            "--out",
            str(contract_path),
        ]
    )
    assert rc == 0
    assert contract_path.is_file()

    assert run(["validate", str(contract_path)]) == 0
    assert run(["audit", str(contract_path)]) == 0

    for target, expected in [
        ("generic", tmp_path / "demo-task.groundspec-prompt.md"),
        ("claude-code", tmp_path / ".claude" / "skills" / "demo-task" / "SKILL.md"),
        ("codex", tmp_path / ".agents" / "skills" / "demo-task" / "SKILL.md"),
    ]:
        rc = run(["compile", str(contract_path), "--target", target, "--out", str(tmp_path)])
        assert rc == 0
        assert expected.is_file(), expected


def test_validate_rejects_broken_contract(tmp_path: Path, capsys):
    path = tmp_path / "broken.json"
    path.write_text(json.dumps({"contract_schema_version": "0.1.0"}), encoding="utf-8")
    rc = run(["validate", str(path)])
    assert rc == 1
    assert "issue" in capsys.readouterr().out


def test_evaluate_with_passing_evidence(tmp_path: Path):
    contract_path = tmp_path / "demo.toml"
    run(
        [
            "create",
            "--task-id",
            "demo-task",
            "--brief",
            "b",
            "--goal",
            "g",
            "--user",
            "u",
            "--deliverable",
            "d:desc",
            "--out",
            str(contract_path),
        ]
    )
    result_dir = tmp_path / "result"
    result_dir.mkdir()
    (result_dir / "evidence.json").write_text(
        json.dumps({"hard_constraint_results": {"x": True}, "dimension_scores": {}}), encoding="utf-8"
    )
    assert run(["evaluate", str(contract_path), str(result_dir)]) == 0


def test_evaluate_missing_evidence_file_errors(tmp_path: Path):
    contract_path = tmp_path / "demo.toml"
    run(
        [
            "create",
            "--task-id",
            "demo-task",
            "--brief",
            "b",
            "--goal",
            "g",
            "--user",
            "u",
            "--deliverable",
            "d:desc",
            "--out",
            str(contract_path),
        ]
    )
    empty_dir = tmp_path / "empty_result"
    empty_dir.mkdir()
    assert run(["evaluate", str(contract_path), str(empty_dir)]) == 2


def test_pack_validate_accepts_builtin_core_pack():
    from importlib import resources

    core_path = Path(str(resources.files("groundspec.packs"))) / "core-invariants.json"
    assert run(["pack", "validate", str(core_path)]) == 0


def test_pack_validate_rejects_duplicate_rule_ids(tmp_path: Path):
    pack = {
        "rule_pack_schema_version": "0.1.0",
        "pack_id": "broken-pack",
        "version": "0.1.0",
        "layer": "project",
        "title": "broken",
        "rules": [
            {
                "id": "dup",
                "version": "0.1.0",
                "title": "t",
                "purpose": "p",
                "scope": "s",
                "applies_when": True,
                "severity": "advisory",
                "requirement": "r",
                "verification_method": "manual_inspection",
                "evidence_requirement": "e",
                "failure_behavior": "warn_only",
                "source_or_rationale": "src",
            }
        ]
        * 2,
    }
    path = tmp_path / "broken-pack.json"
    path.write_text(json.dumps(pack), encoding="utf-8")
    assert run(["pack", "validate", str(path)]) == 1


def test_example_writes_valid_contracts(tmp_path: Path):
    assert run(["example", "--out", str(tmp_path)]) == 0
    written = list(tmp_path.glob("*.toml"))
    assert len(written) >= 2
    for path in written:
        assert run(["validate", str(path)]) == 0
