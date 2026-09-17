# Changelog

All notable changes to this project are documented in this file.

## [0.2.0rc2] - unreleased

Regression-fix release. An independent user test of `v0.2.0rc1`'s Meta-Skill (Guided-mode PRD scoping) found real behavioral defects: material product decisions silently defaulted with zero clarification questions; an explicit "do not perform any external action" instruction did not stop ten web searches; a model self-review was recorded as a verified fact; "no source exists" was asserted from one bounded search; row/label counts were treated as proof of semantic correctness; and `Completion state: PASS` was reported despite an unresolved critical risk, weak-evidence 'must' criteria, and the authorization violation. Full account: `tests/regression/food_delivery_v0_2_0rc1/README.md`.

### Fixed

- Contract schema **0.3.0** (additive; `0.1.0`/`0.2.0` untouched): `status.verified_facts.evidence_label` narrowed to labels that mean real verification happened (`VERIFIED`, `MEASURED`, `SOURCE_VERIFIED`, `USER_CONFIRMED`, `HUMAN-REVIEWED`) -- a self-review can no longer be schema-valid there. `status.unverified_claims` gains an optional `evidence_label` for the weaker labels plus two new ones, `ASSUMPTION` and `RESEARCH_NEEDED` (the latter bounded to "no suitable source found in the searches performed," never "no source exists"). `scope.assumptions.safe_default` is now `const: true` -- an item unsafe to default must be an `open_question`, not an assumption. `status.residual_risks` gains `affects_deliverable_validity` (default `true`), distinguishing a critical risk that undermines the deliverable's validity from one that is itself a legitimate finding the task was asked to produce.
- `groundspec.metaskill.completion.derive_completion_state` gains `authorization_boundary_violated` and `unresolved_critical_risk_to_validity`, both forcing `FAIL`, checked ahead of acceptance criteria. `evaluate_acceptance_criteria` now accepts a richer per-criterion `{met, evidence_label}` result (the plain-bool shape remains fully supported) and flags a 'must' criterion as evidence-inadequate -- producing `INCOMPLETE`, never a silent `PASS` -- when its `verification_method` demands real evidence but only a weak label was supplied. Wired into `groundspec evaluate` as a further additive, backward-compatible extension of the `evidence.json` convention (new `authorization_violations` key).
- Meta-Skill content rewritten to match: network access, web search, fetches, and API calls are now explicitly enumerated as external actions with no "just a search" exception; a concrete checklist of near-universally-material dimensions for product/PRD-scoping requests (geography, business model shape, persona, monetization, payments, language, research-vs-launch-plan scope); an explicit rule that a deferred high-value item is recorded as an open question, never folded into an assumption; full documentation of the new evidence taxonomy and the hardened completion-state gates.
- New maintained regression scenario (`tests/regression/food_delivery_v0_2_0rc1/`) converting the exact reported test into fixtures and deterministic assertions -- not prose matching.
- Two more stale pre-publication statements corrected (`SECURITY.md`'s hardcoded prerelease version; `CHANGELOG.md`'s own `[0.2.0rc1]` entry, which said "unreleased" after it had, in fact, been released).

## [0.2.0rc1] - 2026-09-17

Major prerelease feature: the **Groundspec Meta-Skill**, a reusable, natural-language front end that turns "use Groundspec to..." into a validated Task Contract, guided execution, and a mechanically-derived completion state -- without the user ever hand-writing TOML. The existing deterministic CLI and per-task compiled Skills (`groundspec compile`) are unchanged and remain fully supported; the Meta-Skill is additive.

### Added

- `groundspec skill export --target {claude-code,codex}`: renders one canonical, vendor-neutral Meta-Skill source (`src/groundspec/metaskill/canonical/groundspec/`) into each platform's Skill format, byte-identical in body and every reference file, differing only in frontmatter. Safe by construction: atomic writes, refuses to overwrite without `--force`, refuses to write through a symlinked destination, rejects unsafe relative paths, returns a file manifest with per-file SHA-256.
- `groundspec skill validate <dir>`: structural validation (frontmatter shape, broken-reference detection) for any exported Skill directory, independent of which vendor exporter produced it; also runs as part of `groundspec doctor`.
- Contract schema **0.2.0**, additive: `scope.open_questions[].classification` gains a `high_value` value (schema `0.1.0` is untouched and remains fully supported -- see `docs/architecture.md`'s schema-versioning section). `groundspec create` now defaults to `0.2.0`.
- `groundspec.metaskill.completion.derive_completion_state`: computes `PASS` / `PASS_WITH_CAVEATS` / `FAIL` / `INCOMPLETE` / `BLOCKED` from real structured evidence (per-criterion results, hard-constraint results, unresolved blocking questions, budget expiry) -- no code path reaches `PASS` from confident-sounding text alone. Wired into `groundspec evaluate` as a backward-compatible, additive extension (an `evidence.json` without the new `acceptance_criteria_results` key behaves exactly as it did in `v0.1.0rc1`).
- Four Meta-Skill example scenarios (`examples/metaskill/`): a Guided-mode PRD, a research comparison, a content audit, and one **genuine live dry run** (a fresh, isolated subagent completing a real CSV-export task end to end using only the exported Skill and the real CLI, independently re-verified afterward) -- see `examples/metaskill/README.md` for which is which.
- New Meta-Skill-specific threat-model section: prompt injection at the Skill instruction boundary, recursive invocation / clarification-loop guards, export safety, structural validation.

### Fixed

- README and CONTRIBUTING.md no longer claim CI hasn't run or the repository isn't public -- both became true after `v0.1.0rc1` shipped and this was missed at the time.

## [0.1.0rc1] - 2026-09-17

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
