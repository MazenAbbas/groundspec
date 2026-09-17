from groundspec.metaskill import content
from groundspec.metaskill.claude_export import render_claude_meta_skill
from groundspec.metaskill.codex_export import render_codex_meta_skill
from groundspec.metaskill.validate import validate_skill_files


def test_canonical_body_and_references_are_non_empty():
    assert len(content.load_skill_body()) > 500
    refs = content.load_reference_files()
    assert len(refs) >= 7
    for path, text in refs.items():
        assert path.startswith("references/")
        assert path.endswith(".md")
        assert len(text) > 100


def test_claude_export_structure():
    files = render_claude_meta_skill()
    assert files["SKILL.md"].startswith("---\n")
    assert "name: groundspec" in files["SKILL.md"]
    assert "when_to_use:" in files["SKILL.md"]
    assert "references/task-contract-workflow.md" in files


def test_codex_export_structure():
    files = render_codex_meta_skill()
    assert files["SKILL.md"].startswith("---\n")
    assert "name: groundspec" in files["SKILL.md"]
    # Codex frontmatter deliberately does not claim when_to_use -- that key
    # is not part of OpenAI's documented Skill frontmatter.
    assert "when_to_use:" not in files["SKILL.md"]


def test_claude_and_codex_bodies_and_references_are_byte_identical():
    claude_files = render_claude_meta_skill()
    codex_files = render_codex_meta_skill()

    claude_body = claude_files["SKILL.md"].split("---\n", 2)[-1]
    codex_body = codex_files["SKILL.md"].split("---\n", 2)[-1]
    assert claude_body == codex_body

    claude_refs = {k: v for k, v in claude_files.items() if k != "SKILL.md"}
    codex_refs = {k: v for k, v in codex_files.items() if k != "SKILL.md"}
    assert claude_refs == codex_refs


def test_both_vendor_exports_pass_structural_validation():
    assert validate_skill_files(render_claude_meta_skill()) == []
    assert validate_skill_files(render_codex_meta_skill()) == []


def test_structural_validation_catches_missing_skill_md():
    issues = validate_skill_files({"references/a.md": "x"})
    assert any("SKILL.md" in str(i) for i in issues)


def test_structural_validation_catches_broken_reference():
    files = {"SKILL.md": "---\nname: x\ndescription: y\n---\nSee `references/missing.md`."}
    issues = validate_skill_files(files)
    assert any("references/missing.md" in str(i) for i in issues)


def test_structural_validation_catches_missing_frontmatter_keys():
    files = {"SKILL.md": "---\nname: x\n---\nbody"}
    issues = validate_skill_files(files)
    assert any("description" in str(i) for i in issues)


def test_structural_validation_catches_malformed_frontmatter():
    files = {"SKILL.md": "no frontmatter here"}
    issues = validate_skill_files(files)
    assert any("frontmatter" in str(i) for i in issues)
