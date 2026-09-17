"""Renders the canonical Meta-Skill content as an OpenAI Codex Skill.

Frontmatter format confirmed against OpenAI's official docs (accessed
2026-09-17), same sources cited in ``groundspec.adapters.codex_skill``.
Only the frontmatter differs from :mod:`groundspec.metaskill.claude_export`;
the body and every reference file are byte-identical, loaded from the same
canonical source -- see ``groundspec.metaskill.content``.
"""

from __future__ import annotations

from groundspec.metaskill import content
from groundspec.metaskill.claude_export import DESCRIPTION


def _yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def render_codex_meta_skill() -> dict[str, str]:
    frontmatter = (
        "---\n"
        "name: groundspec\n"
        f"description: {_yaml_scalar(DESCRIPTION)}\n"
        "---\n"
    )
    files: dict[str, str] = {"SKILL.md": frontmatter + "\n" + content.load_skill_body()}
    files.update(content.load_reference_files())
    return files
