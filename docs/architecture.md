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
| 4. Domain packs | software / research / content / product-management / data-science-ml | `src/groundspec/packs/<pack-id>/`, layer `domain` -- see "Domain Pack SDK" below |
| 5. Project rules | Anything supplied via `--project-pack` | Loaded as layer `project` |
| 6. Task preferences | Ad hoc, per-task choices (tone, format) | Represented as `quality.soft_objectives[].source: "user_override"`, not a rule-pack layer -- see "Why task preferences aren't a fifth rule-pack layer" below |

`groundspec.rules.precedence.build_rule_set` merges all applicable packs and resolves conflicts strictly by this table (see `LAYER_PRECEDENCE`), never by load order. Two rules only conflict if they share a non-empty `conflict_key` and disagree on `requirement`; agreement is not a conflict, and every actual conflict is recorded with an explanation on the returned `RuleSet.conflicts`, never silently dropped. [examples/09-domain-rule-vs-style-preference](../examples/09-domain-rule-vs-style-preference/) is a real, tested instance of this.

### Why task preferences aren't a fifth rule-pack layer

The PRD's Phase 7 lists five rule layers including "task preferences" (tone, format, style). Modeling free-form style preferences as full rules -- with a stable ID, a verification method, an evidence requirement, a failure behavior -- overstates what they are: a soft objective with a specific source, not a gate. v0.1 represents them as `quality.soft_objectives[].source: "user_override"` directly on the contract instead of inventing a fake rule layer for them. This is a deliberate, documented scope decision, not an oversight; it can be revisited if practice shows real value in giving task preferences their own conflict-detection machinery.

## Domain Pack SDK (v0.3.0rc1)

The target architecture this SDK implements:

```
Natural-language request
        |
Groundspec Meta-Skill            -- intent, mode, clarification, proposed pack selection (model-dependent)
        v
Deterministic Pack Resolver      -- availability, versions, dependencies, conflicts, precedence
        v
Task Contract                    -- goal, scope, permissions, budget, evidence, acceptance criteria
        v
Core invariants + domain packs + risk overlays
        v
Execution and evidence collection
        v
Deterministic validation and completion gates
        v
PASS / PASS_WITH_CAVEATS / INCOMPLETE / BLOCKED / FAIL
```

**The Meta-Skill may recommend and explain a pack selection; only the deterministic CLI (`groundspec pack resolve`) validates it.** This mirrors the exact same deterministic/model-dependent split documented below for everything else in this project -- see "The deterministic / model-dependent boundary."

### Why a Domain Pack SDK, not more Meta-Skill prose

Before this release, adding a new profession meant writing a single-file rule pack (still fully supported, see `docs/rule-pack-authoring.md`) and hand-editing Meta-Skill reference files to describe it. That doesn't scale, and it gives a new domain no way to declare its own dependencies, conflicts, version compatibility, or completion behavior beyond what a bare rules file's `applies_when` conditions can express. The SDK (`groundspec.packs.sdk`) adds a manifest format and a discovery/resolution/locking layer **on top of** the existing rule-pack engine, which is otherwise unmodified -- see `docs/pack-authoring-guide.md` for the authoring-facing guide and `docs/migration-guide-v0.3.md` for exactly how the three pre-existing packs were brought under it with zero content duplication (a `pack.toml` wrapper whose `provides.rules` points at the unchanged, pre-existing rule file).

### Canonical structure and manifest

```
packs/<pack-id>/
├── pack.toml                    # manifest, validated against domain_pack.v0_1_0.schema.json
├── <pack-id>.toml                 # rules (rule_pack_schema_version 0.1.0, unchanged format)
├── questions.toml                  # optional: clarification dimensions
├── evidence-policy.toml             # optional: evidence-labeling policies
├── acceptance-templates.toml         # optional: reusable acceptance-criterion templates
├── completion-gates.toml              # optional: the one deterministic behavioral extension point
├── references/domain-guidance.md       # optional: human/model-facing guidance
└── tests/scenarios.toml                 # optional: deterministic fixtures for `pack test`
```

Every file under a pack directory is individually optional except `pack.toml` itself -- `docs/pack-authoring-guide.md` has the full field reference.

### Discovery and trust (no remote marketplace)

Three origins, checked in this order: **official** (shipped with `groundspec`, discovered by scanning `src/groundspec/packs/` for any immediate subdirectory containing a `pack.toml`), **project** (`.groundspec/packs/<pack-id>/`), **user** (`~/.groundspec/packs/<pack-id>/`, only if present). No automatic download, no remote registry, no scanning of arbitrary parent directories. An unofficial pack declaring the same `pack_id` as an official one is never silently substituted -- see `docs/threat-model.md`'s Domain Pack extensibility section for the full security posture.

### Composition, precedence, and conflicts

`groundspec pack resolve --pack <id> [--pack <id> ...]` computes the dependency closure for an *explicitly requested* set of pack IDs (never inferred from natural language by the CLI itself), checks version ranges, and classifies every conflict as `resolvable_by_precedence` (a shadow, or two packs' completion gates disagreeing but broken by declared `priority` -- reported, not blocking), `requires_user_decision` (a genuinely ambiguous same-priority gate disagreement), or an outright invalid composition (an explicit `conflicts` declaration, a cross-pack duplicate rule ID, an impossible/unsatisfied version range, or a dependency cycle). The existing core/risk-overlay/domain/project rule-*layer* precedence (the table above) is completely unchanged by any of this -- a pack's `priority` field only ever breaks a tie between two packs' *completion gates*, never between rules across layers.

### The one deterministic behavioral extension point: completion gates

A pack cannot change how `groundspec.metaskill.completion.derive_completion_state` computes the core completion state -- that function is untouched. Instead, `groundspec.packs.sdk.gates.apply_pack_gates` takes the core result and a pack's *triggered* gates (conditions evaluated against `{"contract": ..., "evidence": ...}` through the same safe DSL rules already use) and only ever **downgrades** it (`PASS` -> `PASS_WITH_CAVEATS`/`INCOMPLETE`/`FAIL`, never the reverse) -- the same "a lower layer can narrow but never broaden" rule that governs pack-provided rules generally. `product-management` and `data-science-ml` both use this to implement the completion-gate requirements from their own specs (a silently-defaulted material decision, an unresolved leakage risk, a production claim resting on one offline score, and so on) without either pack needing a single line of Python.

### Lock files

`groundspec pack lock` writes a canonical-JSON `groundspec.lock` (exact pack IDs, versions, SHA-256 content hashes computed fresh from disk, origins, dependency closure) using the same canonical-JSON writer that already guarantees Task Contract determinism (`groundspec.contract.serialization.canonical_json_dumps`) -- no timestamps, no absolute host paths, byte-identical output for byte-identical inputs. It is currently a **reproducibility record**, not yet an enforcement mechanism (there is no lock-verification command in this release) -- see `docs/threat-model.md`'s "Lock-file tampering and enforcement" entry.

### Performance (measured, single-machine, not a universal benchmark)

Measured once, on one Windows development machine, against a clean dev-tree install with all 5 official packs present (20 repeats per number, median reported; see `tests/integration/test_pack_sdk_official_packs.py::test_full_composition_resolves_quickly` for the regression guard this informs). **These are not portable performance guarantees** -- they exist to establish "responsive on an ordinary student laptop, no GPU required" in concrete terms, not to promise a specific number on every machine.

| Operation | Median time |
|---|---|
| `discover_official()` | ~1.4 ms |
| `discover_all()` (official + project + user) | ~1.5 ms |
| `load_pack()` for one pack, including the full safety scan | 65-95 ms |
| `resolve()` for 1 requested pack | ~385 ms |
| `resolve()` for all 5 official packs | ~385 ms |

Peak traced memory (`tracemalloc`) for a full 5-pack `resolve()`: under 250 KiB -- negligible, and not meaningfully different from a 1-pack resolve, since Python's own interpreter/import overhead dominates whatever this SDK allocates.

**A real, honestly-disclosed characteristic, not a bug:** `resolve()`'s time is essentially flat regardless of how many packs are *requested*, because `_load_all_candidates` (`groundspec/packs/sdk/resolver.py`) loads and safety-scans **every pack discoverable from every origin** up front, not just the requested subset -- this is what makes official-pack shadow detection work even for a pack the caller never explicitly asked about. The consequence: `resolve()`'s cost scales with the total number of packs *installed and discoverable*, not with the size of the request. At 5 official packs this is still sub-half-second and well within "responsive," but it would not scale gracefully to a project with hundreds of local packs without changing `_load_all_candidates` to lazily load only requested-pack-plus-dependency-closure candidates and fall back to a full scan only for the shadow-detection warning path. Filed as a known limitation rather than fixed in this release, since this version ships no marketplace and no mechanism for a project to accumulate hundreds of packs.

Installed package footprint: wheel 196 KiB, sdist 280 KiB, installed `site-packages/groundspec/` 1.1 MiB -- consistent with the "no pandas/NumPy/scikit-learn/PyTorch/TensorFlow/Jupyter" constraint on `data-science-ml`; the SDK and both new official packs add no new third-party dependency beyond what `groundspec` already required (`jsonschema`, `tomli`/`tomli-w`).

### What this SDK does not do

No remote pack marketplace, no automatic download or update, no medical/legal/investment-advice packs (see `docs/domain-pack-backlog.md` for what those would actually require), no gating on the manifest's own `risk_classification` field beyond surfacing it. All disclosed, not hidden.

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

`contract_schema_version` and `rule_pack_schema_version` are `const` fields in their respective schemas -- a document declares exactly which schema it conforms to, and `schema_loader.load_contract_schema`/`load_rule_pack_schema` raise `UnsupportedSchemaVersion` rather than guessing or silently upgrading a document written against a version this build doesn't ship.

The Task Contract schema has gone through this three times so far.

**0.1.0 -> 0.2.0** added `high_value` to `scope.open_questions[].classification`'s enum -- needed because the Meta-Skill's clarification policy (`references/clarification-policy.md`) distinguishes a fourth category (worth asking if budget allows, but no safe default exists) that the original three-value enum (`blocking`/`important_defaultable`/`optional`) couldn't represent. Purely additive: every field, every other enum, and every `$defs` entry is byte-identical between the two schema files except that one enum's value list (verified by `tests/unit/test_schema_versioning.py`).

**0.2.0 -> 0.3.0** was prompted by a live user test of the Meta-Skill (`v0.2.0rc1`) that reported `Completion state: PASS` despite a model self-review being recorded as a verified fact, an unresolved critical risk, and an authorization violation -- see `tests/regression/food_delivery_v0_2_0rc1/README.md` and `CHANGELOG.md`'s `[0.2.0rc2]` entry for the full account. Three additive changes: `status.verified_facts.evidence_label` is narrowed to labels that mean real verification happened (dropping `MODEL-EVALUATED`/`PROPOSED`/`PENDING_EXTERNAL_VALIDATION`/`OUT_OF_SCOPE` from *that specific field* -- they still exist, moved to a new optional `evidence_label` on `status.unverified_claims`, alongside two new values, `ASSUMPTION` and `RESEARCH_NEEDED`); `scope.assumptions.safe_default` becomes `const: true` (an item that isn't safe to default no longer belongs in `scope.assumptions` at all); and `status.residual_risks` gains `affects_deliverable_validity` (default `true`) so a critical risk can't silently avoid gating completion by omission. None of this is a compatibility break for existing documents -- it narrows what a *new* `0.3.0` document may say, while `0.1.0` and `0.2.0` files keep validating against their own untouched schema files exactly as before.

**0.3.0 -> 0.4.0** was prompted by a second live user test of the Meta-Skill: a Riyadh university-student food-delivery PRD that reported `Completion state: PASS` despite an unsupported market/competitor claim with no evidence record at all, a materially outcome-changing pilot city/campus silently promoted from illustrative anchor to confirmed scope, a conditional regulatory rule (Saudi ZATCA VAT deemed-supplier treatment) generalized past its actual conditions, and a secondary news source treated as if it were official regulatory confirmation -- see `tests/regression/food_delivery_riyadh_v0_2_0rc2/README.md`. One additive change: `status` gains an optional `claim_ledger` array of a new `claim_record` shape -- a structured, citable provenance record for a **material factual claim** (one affecting the problem definition, market size, legal/regulatory or financial feasibility, risk severity, product scope, an acceptance threshold, or a go/no-go recommendation). `claim_record` carries its own, more granular 7-value evidence-label enum (`MEASURED`/`PRIMARY_SOURCE_VERIFIED`/`SECONDARY_SOURCE_SUPPORTED`/`USER_CONFIRMED`/`MODEL_EVALUATED`/`ASSUMPTION`/`RESEARCH_NEEDED`) plus `source_type`/`authority_level`/citation fields, with `allOf`/`if`/`then` rules that make three defects structurally impossible rather than merely discouraged: (a) `PRIMARY_SOURCE_VERIFIED`/`SECONDARY_SOURCE_SUPPORTED` without a full citation (URL, title, access date, excerpt/locator) fails validation; (b) `SECONDARY_SOURCE_SUPPORTED` combined with `authority_level: primary_official` fails validation -- a secondary source can never claim primary/official authority; (c) a `SECONDARY_SOURCE_SUPPORTED` claim that `affects` `legal_or_regulatory_feasibility` requires a non-empty `limitations` string. `scope_and_qualifiers` is required on every `claim_record` (conditions/exceptions preserved, or an explicit "none" statement) but its *content* can't be schema-checked against the actual source -- that remains a documented discipline in `references/execution-and-verification.md`, not a mechanical guarantee, exactly like the honesty limitations already documented below for `0.1.0`-`0.3.0`. On the runtime side, `groundspec.metaskill.completion` gained `has_unmapped_material_claims` (a material claim with no ledger entry forces `INCOMPLETE`, fed via `evaluate`'s `evidence.json`'s new `unmapped_material_claims` key) and `claim_ledger_has_disclosed_material_limitations` (a material claim resting on secondary support, model judgment, an assumption, or a bounded research gap forces `PASS_WITH_CAVEATS`, never a bare `PASS`). Purely additive to the schema: `0.1.0`-`0.3.0` documents are unaffected, since `claim_ledger` did not exist for them and still doesn't need to.

No migration function has been needed for any step because none removed or renamed a field an existing document could have used -- each older schema file stays untouched and fully supported forever, and `groundspec` ships and supports all versions simultaneously (`SUPPORTED_CONTRACT_VERSIONS = ("0.1.0", "0.2.0", "0.3.0", "0.4.0")`). New contracts (`groundspec create`, or `contract.factory.new_contract`) default to the newest, `0.4.0`.

A future *non*-additive change (a field renamed, removed, or made required) would need an actual `migrations.py` module holding explicit, tested field-mapping functions between adjacent versions -- never an automatic best-effort conversion -- and that module still doesn't exist because it still hasn't been needed. JSON Schema itself defines no migration mechanism beyond the `$schema`/`$id` version identifiers (confirmed against json-schema.org's own specification pages, 2026-09-17); the migration discipline above is this project's own, on top of that.

## Material-claim policy

A **material factual claim** is one that affects: the problem definition, market size, legal or regulatory feasibility, financial feasibility, risk severity, product scope, an acceptance threshold, or a go/no-go recommendation. This is deliberately a floor, not an exhaustive taxonomy of every sentence a deliverable contains -- ordinary connective prose, stylistic choices, and non-material color commentary are never classified or gated. Groundspec cannot deterministically prove the truth of arbitrary prose, and the tooling and this document say so honestly; what the material-claim policy actually guarantees is narrower and mechanical: every material claim maps to exactly one of adequate evidence, user confirmation, an explicit assumption, a disclosed model-evaluated judgment, or a disclosed research-needed gap -- via `status.claim_ledger` (schema `0.4.0`+, see above) -- before `groundspec.metaskill.completion.derive_completion_state` can report an unconditional `PASS`.

Consequences, mechanically enforced by `derive_completion_state`, `has_unmapped_material_claims`, and `claim_ledger_has_disclosed_material_limitations` (`src/groundspec/metaskill/completion.py`):

- A material claim with **no** `claim_ledger` entry at all (fed via `evaluate`'s `evidence.json`'s `unmapped_material_claims` key) forces `INCOMPLETE` -- not proven wrong, just not evidenced.
- A material claim whose ledger entry is honestly labeled `SECONDARY_SOURCE_SUPPORTED`, `MODEL_EVALUATED`, `ASSUMPTION`, or `RESEARCH_NEEDED` is a **disclosed limitation**, not a defect -- but it forces `PASS_WITH_CAVEATS` rather than a bare `PASS`, because a deliverable resting on it is not fully independently confirmed.
- A material claim whose ledger entry is `MEASURED`, `PRIMARY_SOURCE_VERIFIED`, or `USER_CONFIRMED` is strong evidence and does not, by itself, prevent a bare `PASS`.

This is the same shape as the existing `high_value` open-question gate (a disclosed default caveats `PASS`, an undisclosed one is worse) applied to factual claims instead of scope decisions -- see `references/clarification-policy.md`'s "illustrative anchor is not a decision" section for the parallel case where a *decision* (not a factual claim) is silently promoted from illustrative to confirmed.

## Why `jsonschema` is the one schema-validation dependency

The core could have hand-rolled a minimal validator against just this project's own schema shape, but that would silently reimplement (and likely under-implement) parts of the JSON Schema spec -- `additionalProperties`, `oneOf`, pattern/format validation, and correct error paths. `jsonschema` (pure Python, MIT-licensed, the de facto reference implementation) is used instead specifically so that `task_contract.v0_1_0.schema.json` means exactly what the JSON Schema spec says it means to any other tool that reads it, not just to this codebase.

## Why there is no TOML-writing dependency

Reading TOML uses the standard library's `tomllib` (Python 3.11+). Writing does not use a third-party library because this project needs a specific, narrow guarantee -- byte-for-byte deterministic output with sorted keys, matching the canonical JSON form -- that a general-purpose TOML writer does not promise as a stable contract. `contract/toml_codec.py` is a small, fully-tested writer scoped to exactly the value shapes the Task Contract and rule-pack schemas actually produce (see its module docstring for the one deliberate lossy point: TOML has no `null`, so a `None` value is omitted on write and restored by `normalize.fill_defaults` on read).
