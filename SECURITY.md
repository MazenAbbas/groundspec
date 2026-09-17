# Security policy

## Supported versions

Groundspec is pre-release (v0.1.0rc1). Only the latest prerelease is supported; there is no long-term-support branch yet.

## Reporting a vulnerability

Until this repository is public, report a suspected vulnerability by contacting the maintainer directly rather than opening a public issue. Once the repository is public, use GitHub's private vulnerability reporting ("Report a vulnerability" under the Security tab) if enabled, or open an issue marked `security` with only the fact that a report exists and where to reach you privately -- not the details.

Please include: the affected version/commit, a minimal reproduction (a rule pack or contract file, if relevant), and the specific guarantee you believe is broken (see `docs/threat-model.md` for the guarantees this project currently claims).

## Scope

In scope: the `groundspec` CLI and library (`src/groundspec/`), the bundled rule packs, and the JSON Schemas.

Out of scope: vulnerabilities in an AI model or platform (Claude, Codex, or any other) that merely *reads* groundspec-compiled output -- report those to the platform vendor. Groundspec's own threat model (`docs/threat-model.md`) explicitly documents that a compiled Skill/prompt cannot force an executing model to comply; that is a known, structural limitation, not itself a vulnerability report.

## What counts as a real finding here

- A rule pack or contract that achieves code execution.
- A `pack_id` or file path that escapes the configured search directories (path traversal).
- A way for a project-layer rule to outrank a core or risk-overlay rule.
- A way for `groundspec.scoring.rubric.score` to report a passing verdict alongside a failed hard constraint.
- A way for `status.budget_expired: true` to coexist with `status.completion_status: "complete"` after `groundspec audit`/`evaluate` without an error.
- Secret or personal-data leakage from the CLI's own output (not from user-supplied content the user chose to include).

See `docs/threat-model.md` for the full list of modeled threats, including several documented, unmitigated gaps (symlink escape into a configured search directory, terminal-control-character injection into CLI output) -- these are already known and tracked; a report matching one of them is still welcome but won't be new information.
