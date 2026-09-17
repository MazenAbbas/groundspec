"""Loads the canonical, vendor-neutral Meta-Skill content bundled as package
data under ``groundspec.metaskill.canonical.groundspec``.

There is exactly one copy of this content. The Claude Code and Codex
exporters (:mod:`groundspec.metaskill.claude_export`,
:mod:`groundspec.metaskill.codex_export`) each add only their own
frontmatter around the same ``SKILL.body.md`` and copy every reference file
byte-for-byte -- so the two exported Skills cannot drift apart in meaning,
the same guarantee the three Task Contract adapters already give (see
``adapters/common.py``).
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def _canonical_root() -> Path:
    return Path(str(resources.files("groundspec.metaskill.canonical.groundspec")))


def load_skill_body() -> str:
    return (_canonical_root() / "SKILL.body.md").read_text(encoding="utf-8")


def load_reference_files() -> dict[str, str]:
    """Returns {relative_path_under_references: content} for every file
    under the canonical ``references/`` directory, discovered from disk so
    that adding a new reference file never requires touching this module."""
    root = _canonical_root() / "references"
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        result[f"references/{rel}"] = path.read_text(encoding="utf-8")
    return result


def load_all_canonical_files() -> dict[str, str]:
    """Everything except SKILL.md itself (which each exporter renders with
    its own frontmatter around ``load_skill_body()``)."""
    return load_reference_files()
