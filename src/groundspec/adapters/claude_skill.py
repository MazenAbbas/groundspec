"""Renders a Task Contract as a Claude Code Skill.

Format confirmed against Anthropic's official docs (accessed 2026-09-17):
https://code.claude.com/docs/en/skills and
https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview --
SKILL.md must start with `---` as its literal first line; only `description`
is effectively required; content should stay short with detail pushed into
supporting files (progressive disclosure), which is why the full compiled
brief lives in reference.md rather than SKILL.md itself.
"""

from __future__ import annotations

from groundspec.adapters.common import render_body
from groundspec.rules.evaluator import AppliedRule


def _yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def render_claude_skill(
    contract: dict[str, object],
    applied_rules: list[AppliedRule],
) -> dict[str, str]:
    task_id = contract["task_id"]
    brief = contract["brief"]
    assert isinstance(brief, dict) and isinstance(task_id, str)
    goal = brief["goal"]
    assert isinstance(goal, str)

    description = f"Compiled groundspec task contract: {goal}"
    when_to_use = (
        f"Use when working on the task {task_id!r} so goals, constraints, acceptance criteria, "
        "budgets, and hard constraints are honored exactly as specified in this contract."
    )

    frontmatter = (
        "---\n"
        f"name: {task_id}\n"
        f"description: {_yaml_scalar(description)}\n"
        f"when_to_use: {_yaml_scalar(when_to_use)}\n"
        "metadata:\n"
        "  groundspec_contract_schema_version: "
        f"{_yaml_scalar(str(contract['contract_schema_version']))}\n"
        "---\n"
    )

    body_full = render_body(contract, applied_rules)

    skill_md = (
        frontmatter
        + "\n"
        + f"# {task_id}\n\n"
        + f"{description}.\n\n"
        + "The full compiled contract -- deliverables, constraints, acceptance criteria, hard "
        "constraints, soft objectives, and budgets -- is in `reference.md` next to this file. "
        "Read it before planning or executing this task.\n"
    )

    return {"SKILL.md": skill_md, "reference.md": body_full}
