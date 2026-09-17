# Adapter guide

`groundspec compile contract.toml --target {generic,claude-code,codex}` renders a compiled Task Contract three different ways. All three share exactly one content-producing function, `groundspec.adapters.common.render_body`, so they cannot drift apart in meaning -- see `tests/unit/test_adapters.py::test_all_three_adapters_agree_on_load_bearing_content`, which asserts the goal text, every applicable hard-constraint requirement, and every acceptance criterion appear verbatim in all three outputs. Only the packaging (frontmatter, file layout, vendor-specific notes) differs.

## `--target claude-code`

Writes `.claude/skills/<task_id>/SKILL.md` and `.claude/skills/<task_id>/reference.md`.

Format confirmed against Anthropic's official documentation, accessed 2026-09-17:
- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Agent Skills overview](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)

`SKILL.md` must start with `---` as its literal first line. Only `description` is effectively required by Claude Code; this adapter also sets `name` and `when_to_use`. Anthropic's own guidance recommends keeping `SKILL.md` short and pushing detail into supporting files ("progressive disclosure") -- which is why the full compiled brief lives in `reference.md`, not in `SKILL.md` itself. Claude Code discovers skills under a project's `.claude/skills/` directory (or the user's `~/.claude/skills/`).

## `--target codex`

Writes `.agents/skills/<task_id>/SKILL.md` and `.agents/skills/<task_id>/references/contract.md`.

Format confirmed against OpenAI's official documentation, accessed 2026-09-17:
- [Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

OpenAI's Codex CLI supports two related-but-distinct mechanisms: a directory-based **Skill** (`SKILL.md` + frontmatter, optional `scripts/`, `references/`, `assets/`), discovered under `.agents/skills/<name>/`, and a separate **AGENTS.md** convention (repo-wide instructions concatenated up the directory tree). This adapter targets the Skill format because it's the closer structural analogue to a Claude Code Skill. The frontmatter is deliberately not identical to the Claude adapter's -- Codex's Skill frontmatter and Claude's SKILL.md frontmatter are documented separately by their respective vendors and are not guaranteed to share every field, so this adapter only sets the fields both formats actually define (`name`, `description`) rather than assuming parity.

If your workflow relies on `AGENTS.md` instead of Skills, `--target generic`'s output can be pasted into an `AGENTS.md` file directly; a dedicated `AGENTS.md` adapter is not shipped in v0.1 since two nearly-identical text-file adapters would add surface area without adding real capability.

## `--target generic`

Writes a single Markdown file, `<task_id>.groundspec-prompt.md`, meant to be pasted into any chat-based AI tool as a system or first-turn message.

This is the weakest adapter by design, and says so in its own output: a plain prompt has no progressive disclosure, no platform-enforced invocation, and nothing stopping a model from drifting from it over a long conversation. The rendered file opens with an explicit "Limitations of prompt-only enforcement" notice rather than presenting itself as equivalent to a real Skill.

## Adapters must not change the contract's meaning

This is a mandatory release gate (see the project's own release-gate checklist). It's enforced two ways: structurally, by having all three adapters call the same `render_body`; and by test, in `tests/unit/test_adapters.py`, which fails the build if a load-bearing fact (the goal, an applicable hard constraint, or an acceptance criterion) is missing from any one of the three rendered outputs.

## What compiling does *not* do

Compiling does not call a model, does not check whether the eventual executor actually follows the compiled instructions, and does not modify the source contract file. Checking the *result* against the contract afterward is `groundspec audit`/`groundspec evaluate`'s job, not the adapters'.
