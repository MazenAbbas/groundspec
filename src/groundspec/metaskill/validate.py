"""Structural validation of a rendered Skill file set -- catches a broken
reference or malformed frontmatter before it ever reaches disk, independent
of which vendor exporter produced the file set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_REFERENCE_PATH_RE = re.compile(r"references/[A-Za-z0-9_\-/]+\.md")


@dataclass(frozen=True)
class StructuralIssue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _frontmatter_block(skill_md: str) -> str | None:
    if not skill_md.startswith("---\n"):
        return None
    end = skill_md.find("\n---", 4)
    if end == -1:
        return None
    return skill_md[4:end]


def validate_skill_files(files: dict[str, str]) -> list[StructuralIssue]:
    """Checks that apply to any exported Skill, regardless of vendor:

    - ``SKILL.md`` is present and starts with a well-formed frontmatter block.
    - The frontmatter declares both ``name`` and ``description``.
    - Every ``references/...md`` path mentioned anywhere in the file set
      actually exists in that same file set (no broken reference).
    """
    issues: list[StructuralIssue] = []

    skill_md = files.get("SKILL.md")
    if skill_md is None:
        issues.append(StructuralIssue("SKILL.md", "missing from file set"))
        return issues

    frontmatter = _frontmatter_block(skill_md)
    if frontmatter is None:
        issues.append(StructuralIssue("SKILL.md", "must start with a '---' ... '---' frontmatter block"))
    else:
        for required_key in ("name:", "description:"):
            if required_key not in frontmatter:
                missing_key_msg = f"frontmatter missing required key {required_key!r}"
                issues.append(StructuralIssue("SKILL.md", missing_key_msg))

    referenced: set[str] = set()
    for text in files.values():
        referenced.update(_REFERENCE_PATH_RE.findall(text))

    for ref in sorted(referenced):
        if ref not in files:
            issues.append(StructuralIssue(ref, "referenced in Skill content but not present in the file set"))

    return issues
