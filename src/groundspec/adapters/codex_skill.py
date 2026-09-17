"""Renders a Task Contract as an OpenAI Codex Skill.

Format confirmed against OpenAI's official docs (accessed 2026-09-17):
https://learn.chatgpt.com/docs/build-skills and
https://learn.chatgpt.com/docs/agent-configuration/agents-md -- Codex
supports a directory-based Skill (SKILL.md + frontmatter name/description,
optional scripts/, references/, assets/) discovered under
.agents/skills/<name>/, largely mirroring the cross-vendor Agent Skills
format, plus a separate AGENTS.md convention. This adapter targets the
Skill format since it is the closer analogue to a Claude Code Skill; it is
deliberately not byte-identical to the Claude adapter's frontmatter because
the two platforms do not define identical frontmatter fields.
"""

from __future__ import annotations

from groundspec.adapters.common import render_body
from groundspec.rules.evaluator import AppliedRule


def _yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def render_codex_skill(
    contract: dict[str, object],
    applied_rules: list[AppliedRule],
) -> dict[str, str]:
    task_id = contract["task_id"]
    brief = contract["brief"]
    assert isinstance(brief, dict) and isinstance(task_id, str)
    goal = brief["goal"]
    assert isinstance(goal, str)

    description = f"Compiled groundspec task contract: {goal}"

    frontmatter = (
        "---\n"
        f"name: {task_id}\n"
        f"description: {_yaml_scalar(description)}\n"
        "---\n"
    )

    body_full = render_body(contract, applied_rules)

    skill_md = (
        frontmatter
        + "\n"
        + f"# {task_id}\n\n"
        + f"{description}.\n\n"
        + "The full compiled contract -- deliverables, constraints, acceptance criteria, hard "
        "constraints, soft objectives, and budgets -- is in `references/contract.md` next to "
        "this file. Read it before planning or executing this task.\n"
    )

    return {"SKILL.md": skill_md, "references/contract.md": body_full}
