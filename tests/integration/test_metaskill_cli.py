from pathlib import Path

from groundspec.cli.main import main


def run(argv: list[str]) -> int:
    return main(argv)


def test_export_claude_code_writes_all_referenced_files(tmp_path: Path):
    assert run(["skill", "export", "--target", "claude-code", "--output", str(tmp_path)]) == 0
    skill_dir = tmp_path / ".claude" / "skills" / "groundspec"
    assert (skill_dir / "SKILL.md").is_file()
    for ref in [
        "task-contract-workflow.md",
        "clarification-policy.md",
        "routing-and-risk.md",
        "execution-and-verification.md",
        "domain-guidance/software-and-product.md",
        "domain-guidance/research-and-analysis.md",
        "domain-guidance/content-and-marketing.md",
    ]:
        assert (skill_dir / "references" / ref).is_file(), ref


def test_export_codex_writes_all_referenced_files(tmp_path: Path):
    assert run(["skill", "export", "--target", "codex", "--output", str(tmp_path)]) == 0
    skill_dir = tmp_path / ".agents" / "skills" / "groundspec"
    assert (skill_dir / "SKILL.md").is_file()
    assert (skill_dir / "references" / "task-contract-workflow.md").is_file()


def test_exported_claude_and_codex_skills_have_identical_references(tmp_path: Path):
    run(["skill", "export", "--target", "claude-code", "--output", str(tmp_path)])
    run(["skill", "export", "--target", "codex", "--output", str(tmp_path)])
    claude_refs = tmp_path / ".claude" / "skills" / "groundspec" / "references"
    codex_refs = tmp_path / ".agents" / "skills" / "groundspec" / "references"
    for path in sorted(claude_refs.rglob("*.md")):
        rel = path.relative_to(claude_refs)
        assert (codex_refs / rel).read_text() == path.read_text()


def test_export_refuses_overwrite_then_succeeds_with_force(tmp_path: Path):
    assert run(["skill", "export", "--target", "claude-code", "--output", str(tmp_path)]) == 0
    assert run(["skill", "export", "--target", "claude-code", "--output", str(tmp_path)]) == 1
    assert run(["skill", "export", "--target", "claude-code", "--output", str(tmp_path), "--force"]) == 0


def test_exported_skill_passes_skill_validate(tmp_path: Path):
    run(["skill", "export", "--target", "claude-code", "--output", str(tmp_path)])
    skill_dir = tmp_path / ".claude" / "skills" / "groundspec"
    assert run(["skill", "validate", str(skill_dir)]) == 0


def test_skill_validate_reports_broken_reference(tmp_path: Path):
    skill_dir = tmp_path / "broken-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: x\ndescription: y\n---\nSee `references/does-not-exist.md`.", encoding="utf-8"
    )
    assert run(["skill", "validate", str(skill_dir)]) == 1


def test_user_scope_export_targets_home_directory(tmp_path: Path, monkeypatch):
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    assert run(["skill", "export", "--target", "codex", "--scope", "user"]) == 0
    assert (fake_home / ".agents" / "skills" / "groundspec" / "SKILL.md").is_file()


def test_existing_task_compile_workflow_is_unaffected(tmp_path: Path):
    """Backward compatibility: the pre-existing per-task compile pipeline
    (unrelated to the meta-skill) still works exactly as before."""
    contract_path = tmp_path / "demo.toml"
    assert (
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
        == 0
    )
    assert run(["validate", str(contract_path)]) == 0
    assert run(["compile", str(contract_path), "--target", "claude-code", "--out", str(tmp_path)]) == 0
    assert (tmp_path / ".claude" / "skills" / "demo-task" / "SKILL.md").is_file()
