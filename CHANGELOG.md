# Changelog

All notable changes to this project are documented in this file.

## [0.1.0rc1] - unreleased

First public release candidate.

### Added

- Versioned Task Contract JSON Schema (`contract_schema_version: "0.1.0"`) with strict validation (unknown keys rejected, no type coercion).
- Deterministic, dependency-free canonical JSON and TOML serialization with a documented, tested round-trip.
- Rule pack format (`rule_pack_schema_version: "0.1.0"`) with a closed, non-executable condition language, cycle/duplicate/import-depth-limited loading, and deterministic precedence resolution across four layers (core, risk overlay, domain, project).
- Ten built-in rule packs: core invariants, seven risk overlays (informational, external communication, filesystem mutation, destructive/irreversible, security-sensitive, high-stakes/regulated, personal data), and three domain packs (software, research, content).
- Budget model with time/iteration/tool/cost budgets, a reserved verification fraction, and a mechanical guard against claiming completion after budget expiry.
- Soft-loss scoring rubric across 12 quality dimensions, explicitly separating objective from subjective dimensions and never letting a soft score outweigh a failed hard constraint.
- `groundspec` CLI: `init`, `create`, `validate`, `compile`, `audit`, `evaluate`, `pack validate`, `example`, `doctor`.
- Three compilation adapters sharing one canonical rendering: Claude Code Skill, OpenAI Codex Skill, and a vendor-neutral generic prompt.
- Ten worked example scenarios (`examples/`), each validated by the test suite.
- A 30-scenario evaluation corpus and metrics module (`eval/`), with live model-comparison runs explicitly marked pending (see `docs/evaluation-methodology.md`).
- Documentation: architecture, schema reference, rule-pack authoring guide, adapter guide, threat model, evaluation methodology, user-validation protocol.

### Known limitations

See the README's "Known limitations / what's still pending" section.
