# Architecture

## Overview

```
                     ┌─────────────────────────────────────────────┐
                     │              Task Contract (JSON/TOML)        │
                     │  brief · scope · routing · quality · accept-  │
                     │  ance · budget · control · status             │
                     └───────────────┬───────────────────────────────┘
                                      │ validated against
                                      ▼
                     src/groundspec/schema/*.schema.json (JSON Schema 2020-12)
                                      │
              ┌───────────────────────┼────────────────────────┐
              ▼                       ▼                        ▼
   contract/validator.py    packs/registry.py          budget/model.py
   contract/normalize.py     + rules/pack_loader.py     scoring/rubric.py
   contract/serialization.py + rules/precedence.py
   contract/toml_codec.py    + rules/condition.py
   contract/factory.py       + rules/evaluator.py
              │                       │                        │
              └───────────┬───────────┴────────────────────────┘
                          ▼
                cli/commands.py (init, create, validate, compile,
                audit, evaluate, pack validate, example, doctor)
                          │
                          ▼
        adapters/common.py → render_body() (one canonical rendering)
              │                 │                    │
              ▼                 ▼                    ▼
   adapters/claude_skill.py  adapters/codex_skill.py  adapters/generic.py
```

Every box above is pure Python, offline, and has no model dependency. There is no code anywhere in this diagram that calls an LLM.

## Layers, precedence, and where each one is enforced

| Layer | What lives here | Enforced by |
|---|---|---|
| 0. Platform/system safety | The host AI platform's own restrictions | Outside this project entirely -- documented, never modeled in the schema |
| 1. Explicit authorization | `routing.authorization` (granted permissions, boundaries, confirm-before list) | Schema + `core-invariants:respect-authorization` rule |
| 2. Core invariants | Universal rules (preserve intent, separate fact from assumption, no unperformed-work claims, ...) | `src/groundspec/packs/core-invariants.json`, layer `core` |
| 3. Risk overlays | 7 built-in packs, selected by `routing.risk_overlays` | `src/groundspec/packs/risk_overlays/*.json`, layer `risk_overlay` |
| 4. Domain packs | software / research / content | `src/groundspec/packs/{software,research,content}/*.json`, layer `domain` |
| 5. Project rules | Anything supplied via `--project-pack` | Loaded as layer `project` |
| 6. Task preferences | Ad hoc, per-task choices (tone, format) | Represented as `quality.soft_objectives[].source: "user_override"`, not a rule-pack layer -- see "Why task preferences aren't a fifth rule-pack layer" below |

`groundspec.rules.precedence.build_rule_set` merges all applicable packs and resolves conflicts strictly by this table (see `LAYER_PRECEDENCE`), never by load order. Two rules only conflict if they share a non-empty `conflict_key` and disagree on `requirement`; agreement is not a conflict, and every actual conflict is recorded with an explanation on the returned `RuleSet.conflicts`, never silently dropped. [examples/09-domain-rule-vs-style-preference](../examples/09-domain-rule-vs-style-preference/) is a real, tested instance of this.

### Why task preferences aren't a fifth rule-pack layer

The PRD's Phase 7 lists five rule layers including "task preferences" (tone, format, style). Modeling free-form style preferences as full rules -- with a stable ID, a verification method, an evidence requirement, a failure behavior -- overstates what they are: a soft objective with a specific source, not a gate. v0.1 represents them as `quality.soft_objectives[].source: "user_override"` directly on the contract instead of inventing a fake rule layer for them. This is a deliberate, documented scope decision, not an oversight; it can be revisited if practice shows real value in giving task preferences their own conflict-detection machinery.

## The deterministic / model-dependent boundary

This is the single most important architectural line in the project, and crossing it silently would be a shipped defect, not a feature.

**Deterministic (this repository's `src/groundspec/` and `groundspec` CLI):**
schema validation, canonical JSON/TOML serialization, rule-pack loading and validation (path safety, cycle detection, duplicate-ID detection, import-depth limits), precedence resolution and conflict detection, budget arithmetic, the soft-loss rubric's weighted arithmetic, template rendering for the three adapters, and static audits (`groundspec audit`). None of this requires a network connection, an API key, or a model call, and none of it will ever get one added in this core -- see PRD Phase 10/11.

**Model-dependent (the AI Skill invoking groundspec, not groundspec itself):**
understanding a vague natural-language brief, deciding what's actually missing versus safely defaultable, drafting the first-pass contract, selecting which domain pack(s) plausibly apply, planning execution, and *judging* whether prose evidence actually satisfies a `manual_inspection`-verified hard constraint. `groundspec audit` will tell you a hard constraint applies and whether its verification method is `automated_test` (mechanically checked) or something else (needs a human or the AI Skill's own honest judgment, backed by real evidence) -- but it will never pretend to have performed that judgment itself.

Nothing in this repository claims a deterministic guarantee for the model-dependent half. Where a command's output depends on human or model judgment, its own text says so (see `cmd_audit`'s "needs human/model judgment with evidence" tag).

## Contract lifecycle

1. **Draft** -- `groundspec create` (quick or guided mode) produces a schema-valid contract with safe, explicit defaults from a handful of user-supplied fields; or an AI Skill drafts a fuller one directly against the schema.
2. **Validate** -- `groundspec validate` checks it against the versioned JSON Schema; `groundspec audit` additionally resolves rule packs and reports applicable hard constraints and any precedence conflicts.
3. **Compile** -- `groundspec compile --target {claude-code,codex,generic}` renders the exact same compiled brief (goal, deliverables, constraints, hard constraints, soft objectives, budgets, stop/escalation conditions) through one shared function (`adapters/common.render_body`), then wraps it in each platform's own frontmatter/file-layout convention. This guarantees the three adapters can never diverge in *meaning*, only in packaging -- see `tests/unit/test_adapters.py::test_all_three_adapters_agree_on_load_bearing_content`.
4. **Execute** -- outside this repository, by whatever AI tool loaded the compiled Skill/prompt.
5. **Evaluate** -- `groundspec evaluate contract.toml result/` scores a result directory's `evidence.json` against the contract's rubric (`groundspec.scoring.rubric.score`), refusing to produce a passing verdict if any hard constraint failed, and reporting `insufficient_evidence` rather than guessing when a dimension has no score.

## Schema versioning and migration strategy

`contract_schema_version` and `rule_pack_schema_version` are `const` fields in their respective schemas (currently `"0.1.0"` for both) -- a document declares exactly which schema it conforms to, and `schema_loader.load_contract_schema`/`load_rule_pack_schema` raise `UnsupportedSchemaVersion` rather than guessing or silently upgrading a document written against a version this build doesn't ship. When a `0.2.0` schema is introduced, it will live alongside `0.1.0` as a separate file (`task_contract.v0_2_0.schema.json`), and a `migrations.py` module (not yet needed, since only one version exists) will hold explicit, tested field-mapping functions between adjacent versions -- never an automatic best-effort conversion. JSON Schema itself defines no migration mechanism beyond the `$schema`/`$id` version identifiers (confirmed against json-schema.org's own specification pages, 2026-09-17); the migration discipline above is this project's own, on top of that.

## Why `jsonschema` is the one schema-validation dependency

The core could have hand-rolled a minimal validator against just this project's own schema shape, but that would silently reimplement (and likely under-implement) parts of the JSON Schema spec -- `additionalProperties`, `oneOf`, pattern/format validation, and correct error paths. `jsonschema` (pure Python, MIT-licensed, the de facto reference implementation) is used instead specifically so that `task_contract.v0_1_0.schema.json` means exactly what the JSON Schema spec says it means to any other tool that reads it, not just to this codebase.

## Why there is no TOML-writing dependency

Reading TOML uses the standard library's `tomllib` (Python 3.11+). Writing does not use a third-party library because this project needs a specific, narrow guarantee -- byte-for-byte deterministic output with sorted keys, matching the canonical JSON form -- that a general-purpose TOML writer does not promise as a stable contract. `contract/toml_codec.py` is a small, fully-tested writer scoped to exactly the value shapes the Task Contract and rule-pack schemas actually produce (see its module docstring for the one deliberate lossy point: TOML has no `null`, so a `None` value is omitted on write and restored by `normalize.fill_defaults` on read).
