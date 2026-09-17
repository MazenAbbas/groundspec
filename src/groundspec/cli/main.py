from __future__ import annotations

import argparse
from collections.abc import Sequence

from groundspec.__about__ import __version__
from groundspec.cli import commands
from groundspec.packs.registry import DOMAIN_PACK_IDS, RISK_OVERLAY_PACK_IDS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="groundspec",
        description="A requirements compiler and verification framework for AI agent tasks.",
    )
    parser.add_argument("--version", action="version", version=f"groundspec {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Set up a .groundspec/ directory for project-level rule packs.")
    p_init.add_argument("dir", nargs="?", default=".")
    p_init.set_defaults(func=commands.cmd_init)

    p_create = sub.add_parser(
        "create",
        help="Create a new Task Contract (quick mode: pass flags; guided mode: omit them, answer prompts).",
    )
    p_create.add_argument("--task-id")
    p_create.add_argument("--brief")
    p_create.add_argument("--goal")
    p_create.add_argument("--problem")
    p_create.add_argument("--user", action="append", help="Repeatable: a target user/beneficiary.")
    p_create.add_argument("--deliverable", action="append", help="Repeatable: name:description.")
    p_create.add_argument("--risk-overlay", action="append", choices=sorted(RISK_OVERLAY_PACK_IDS))
    p_create.add_argument("--risk-level", choices=["low", "medium", "high", "critical"])
    p_create.add_argument("--domain", action="append", choices=sorted(DOMAIN_PACK_IDS))
    p_create.add_argument("--out")
    p_create.set_defaults(func=commands.cmd_create)

    p_validate = sub.add_parser("validate", help="Validate a Task Contract file against the schema.")
    p_validate.add_argument("contract")
    p_validate.set_defaults(func=commands.cmd_validate)

    p_compile = sub.add_parser("compile", help="Compile a Task Contract into agent instructions.")
    p_compile.add_argument("contract")
    p_compile.add_argument("--target", required=True, choices=["generic", "claude-code", "codex"])
    p_compile.add_argument("--out", help="Output directory (default: current directory).")
    p_compile.add_argument(
        "--project-pack", action="append", help="Repeatable: path to a project-layer rule pack file."
    )
    p_compile.set_defaults(func=commands.cmd_compile)

    p_audit = sub.add_parser("audit", help="Run static, deterministic checks against a Task Contract.")
    p_audit.add_argument("contract")
    p_audit.add_argument(
        "--project-pack", action="append", help="Repeatable: path to a project-layer rule pack file."
    )
    p_audit.set_defaults(func=commands.cmd_audit)

    p_evaluate = sub.add_parser(
        "evaluate", help="Score a result directory's evidence.json against the contract's rubric."
    )
    p_evaluate.add_argument("contract")
    p_evaluate.add_argument("result_dir")
    p_evaluate.set_defaults(func=commands.cmd_evaluate)

    p_pack = sub.add_parser("pack", help="Rule pack operations.")
    pack_sub = p_pack.add_subparsers(dest="pack_command", required=True)
    p_pack_validate = pack_sub.add_parser("validate", help="Validate a single rule-pack file.")
    p_pack_validate.add_argument("path")
    p_pack_validate.set_defaults(func=commands.cmd_pack_validate)

    p_skill = sub.add_parser("skill", help="Groundspec Meta-Skill export and validation.")
    skill_sub = p_skill.add_subparsers(dest="skill_command", required=True)

    p_skill_export = skill_sub.add_parser(
        "export", help="Export the canonical Groundspec Meta-Skill for Claude Code or Codex."
    )
    p_skill_export.add_argument("--target", required=True, choices=["claude-code", "codex"])
    p_skill_export.add_argument(
        "--output", help="Base directory to export under (default: '.'). Ignored with --scope user."
    )
    p_skill_export.add_argument(
        "--scope",
        choices=["project", "user"],
        default="project",
        help="'project' (default) exports under --output; 'user' exports to the platform's user skills dir.",
    )
    p_skill_export.add_argument("--force", action="store_true", help="Overwrite an existing export.")
    p_skill_export.set_defaults(func=commands.cmd_skill_export)

    p_skill_validate = skill_sub.add_parser(
        "validate", help="Structurally validate an exported Skill directory (SKILL.md + references/)."
    )
    p_skill_validate.add_argument("path")
    p_skill_validate.set_defaults(func=commands.cmd_skill_validate)

    p_example = sub.add_parser("example", help="Write ready-to-copy example Task Contracts.")
    p_example.add_argument("--out", help="Output directory (default: current directory).")
    p_example.set_defaults(func=commands.cmd_example)

    p_doctor = sub.add_parser(
        "doctor", help="Check that groundspec and its bundled rule packs are installed correctly."
    )
    p_doctor.set_defaults(func=commands.cmd_doctor)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
