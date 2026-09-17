"""Renders the canonical Meta-Skill content as a Claude Code Skill.

Frontmatter format confirmed against Anthropic's official docs (accessed
2026-09-17), same sources cited in ``groundspec.adapters.claude_skill``.
Only the frontmatter differs from :mod:`groundspec.metaskill.codex_export`;
the body and every reference file are byte-identical, loaded from the same
canonical source -- see ``groundspec.metaskill.content``.
"""

from __future__ import annotations

from groundspec.metaskill import content

DESCRIPTION = (
    "Turns a natural-language request into a validated Groundspec Task Contract, then "
    "guides execution and verification against it. Use for ambiguous, multi-step, "
    "high-stakes, or requirements-heavy requests -- not for a single unambiguous, "
    "low-risk question a plain answer already resolves."
)

WHEN_TO_USE = (
    "Invoke explicitly with /groundspec, or let it activate automatically for a request "
    "that needs real scoping: an ambiguous ask, a multi-step project, anything involving "
    "publishing/spending/deleting/production/personal data, or a request to audit an "
    "existing plan, PRD, prompt, contract, or deliverable."
)


def _yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def render_claude_meta_skill() -> dict[str, str]:
    frontmatter = (
        "---\n"
        "name: groundspec\n"
        f"description: {_yaml_scalar(DESCRIPTION)}\n"
        f"when_to_use: {_yaml_scalar(WHEN_TO_USE)}\n"
        "---\n"
    )
    files: dict[str, str] = {"SKILL.md": frontmatter + "\n" + content.load_skill_body()}
    files.update(content.load_reference_files())
    return files
