# Domain Pack authoring guide

This is the authoring-facing guide for the **Domain Pack SDK** introduced in `v0.3.0rc1`. If you're authoring a single-file rule pack for a project (the pre-SDK format, still fully supported), see `docs/rule-pack-authoring.md` instead -- a Domain Pack's `provides.rules` file *is* exactly that format; this guide is about everything wrapped around it.

## Why a Domain Pack, not more Meta-Skill prose

The Groundspec Meta-Skill's job is to turn a natural-language request into a Task Contract; it is not meant to grow a paragraph of instructions for every profession that might ever use Groundspec. A Domain Pack lets a new profession be added as **data the deterministic CLI can validate, compose, and gate on**, loaded only when actually selected (progressive disclosure) -- see `docs/architecture.md`'s Domain Pack SDK section for the full target architecture.

## A Domain Pack is data, never code

A pack cannot run arbitrary commands, import arbitrary Python modules, include executable hooks, grant permissions, expand a user's authorization, contact the network, install dependencies, read secrets, or modify Groundspec's own behavior outside the extension points below. Pack content is untrusted input until validated -- see `docs/threat-model.md`'s Domain Pack extensibility section. Core invariants and a user's explicit authorization always outrank pack instructions; a pack's own rules may only *narrow* permissions or add confirmation requirements, never broaden them.

## Canonical structure

```
packs/<pack-id>/
├── pack.toml                    # manifest -- required
├── <pack-id>.toml                # rules (rule_pack_schema_version 0.1.0) -- optional
├── questions.toml                 # clarification dimensions -- optional
├── evidence-policy.toml            # evidence-labeling policies -- optional
├── acceptance-templates.toml        # reusable acceptance-criterion templates -- optional
├── completion-gates.toml             # the one deterministic behavioral extension point -- optional
├── references/
│   └── domain-guidance.md            # human/model-facing guidance -- optional but usually wanted
└── tests/
    └── scenarios.toml                 # deterministic fixtures for `pack test` -- optional
```

Don't create a file just to have the full structure -- `groundspec pack init` deliberately generates the smallest valid pack (a manifest, one example rule, one guidance note), and every file above is individually optional in `pack.toml`'s `provides` table. A pack that only contributes routing guidance and no machine-checkable rules is legitimate.

## The manifest (`pack.toml`)

Validated against `src/groundspec/schema/domain_pack.v0_1_0.schema.json`. Required: `domain_pack_schema_version` (const `"0.1.0"`), `pack_id`, `version` (strict `X.Y.Z`), `display_name`, `description`, and `compatibility.min_platform_version`. Everything else is optional with a sensible default -- see the schema file itself for every field's description, or `groundspec pack inspect <pack-id>` for a filled-in example.

A few fields worth calling out:

- **`compatibility.min_platform_version`/`max_platform_version`** range against `groundspec.__about__.PACK_PLATFORM_VERSION` (currently `1.0.0`) -- **not** `groundspec.__version__` (the CLI's own, possibly-prerelease version string). This is deliberate: the platform version only changes when the pack manifest schema, the resolver's composition rules, or the completion-gate contract change in a way that could break an existing pack, decoupled from ordinary CLI releases.
- **`dependencies`**/**`conflicts`** reference other `pack_id`s with an optional version range (`min_version` required, `max_version` optional/nullable). An impossible range (`min > max`) or an unsatisfied range fails resolution -- see "Resolution" below.
- **`priority`** (default `0`) only ever breaks a tie between two packs' completion gates that share a `gate_id` and disagree -- it has no effect on the existing core/risk-overlay/domain/project rule-layer precedence, which is unchanged from before this SDK existed.
- **`risk_classification`** (`standard`/`requires_expert_review`) documents that a domain (medical/legal/investment-advice) needs more than an ordinary pack provides -- see `docs/domain-pack-backlog.md`. The CLI surfaces this value but does not yet gate on it; no such pack ships in this release.

## `provides`: wiring in your content files

Every entry is a path relative to the pack directory. `provides.rules` points at a rule-pack file in the existing `rule_pack_schema_version: "0.1.0"` format -- it can even be a pure-import wrapper (`imports = [...]`, `rules = []`) if you want to reuse an existing rule file unchanged; that's exactly how the built-in `software`/`research`/`content` packs were migrated onto this SDK without duplicating a single rule (see `docs/migration-guide-v0.3.md`).

## `questions.toml`, `evidence-policy.toml`, `acceptance-templates.toml`

All three are advisory, structured documentation consumed by the Meta-Skill and validated for well-formedness by the SDK -- none of them are mechanically enforced beyond that. This is a deliberate, disclosed scope boundary: Groundspec cannot deterministically judge whether a clarification question is actually material, whether an evidence policy was correctly applied, or whether an acceptance-criterion template was filled in faithfully -- that remains model/human judgment, exactly like everything else across the deterministic/model-dependent boundary (see `docs/architecture.md`).

```toml
# questions.toml
[[questions]]
id = "prediction-target"
question = "..."
why_material = "..."
classification_guidance = "..."
```

```toml
# evidence-policy.toml
[[policies]]
id = "..."
description = "..."
applies_to_claim_categories = ["market_size"]
guidance = "..."
```

```toml
# acceptance-templates.toml
[[templates]]
id = "..."
description_template = "..."
default_priority = "must"                  # must | should | could
default_verification_method = "manual_inspection"
default_evidence_required = "..."
```

## `completion-gates.toml`: the one deterministic extension point

A gate is a condition (the exact same safe DSL a rule's `applies_when` already uses -- `path`/`op`/`value`, `all`/`any`/`not`) evaluated at `groundspec evaluate` time against `{"contract": <task contract>, "evidence": <evidence.json>}`, plus a fixed action:

```toml
[[gates]]
id = "no-baseline-for-performance-claim"
description = "..."
condition = { path = "evidence.ds_no_baseline_for_performance_claim", op = "eq", value = true }
on_violation = "downgrade_to_incomplete"    # downgrade_to_caveats | downgrade_to_incomplete | downgrade_to_fail
rationale = "..."
```

`groundspec.metaskill.completion.derive_completion_state` itself is never modified -- `apply_pack_gates` (in `groundspec.packs.sdk.gates`) only ever *downgrades* its result, mirroring the "a lower layer can narrow but never broaden" rule that governs everything else in this project. A gate condition typically reads an `evidence.<your_field_name>` boolean an evaluator (human or model) populates honestly -- Groundspec cannot itself detect leakage, an unlabeled claim, or a mismatched metric from contract structure alone; the gate only ever gates on a supplied signal, never computes one.

## `tests/scenarios.toml`: fixtures for `groundspec pack test`

```toml
[[scenarios]]
id = "no-baseline-triggers-incomplete"
description = "..."
evaluation_kind = "deterministic"           # deterministic | model_evaluated | human_reviewed | pending_external_validation
given_evidence = { ds_no_baseline_for_performance_claim = true }
given_contract_fragment = {}
expect_gates_triggered = ["no-baseline-for-performance-claim"]
expect_gates_not_triggered = []
expect_rules_apply = []
expect_rules_not_apply = []
```

`groundspec pack test <pack-id>` runs every scenario by evaluating your gates/rules' conditions against the given fixtures -- no pack-provided code executes, ever. This is exactly the mechanism `product-management`'s and `data-science-ml`'s own 12-scenario suites use (`groundspec pack test product-management` / `data-science-ml`).

## Discovery and trust

Three origins, checked in this order for a `pack list`/`pack resolve`: **official** (shipped with `groundspec`), **project** (`.groundspec/packs/<pack-id>/`), **user** (`~/.groundspec/packs/<pack-id>/`, only if present). No remote marketplace, no automatic download, no scanning of arbitrary parent directories. An unofficial pack declaring the same `pack_id` as an official one is never silently substituted -- `pack resolve`/`pack lock` refuse it unless you pass an explicit `--allow-shadow <pack-id>`, and even then the shadow is reported, not hidden, with project taking precedence over user when both shadow the same official id.

## Resolution and composition

`groundspec pack resolve --pack <id> [--pack <id> ...]` is the only place a multi-pack selection is validated. It computes the full dependency closure, checks every version range, and classifies every conflict it finds as:

- **`resolvable_by_precedence`** -- informational; a shadow, or two packs' completion gates disagreeing but broken by `priority`. Reported, not blocking.
- **`requires_user_decision`** (raises `PackCompositionAmbiguousError`) -- two same-priority completion gates disagree with no way to break the tie deterministically.
- **invalid composition** (raises `PackCompositionInvalidError`, `PackVersionRangeError`, or `PackDependencyCycleError`) -- an explicit `conflicts` declaration between two selected/depended packs, a cross-pack duplicate rule id, an impossible or unsatisfied version range, or a dependency cycle. None of these are ever silently resolved by picking one side.

Compatible rules and gates from different packs simply merge (the existing core/risk-overlay/domain/project layer precedence, unchanged, already handles same-`conflict_key` rule disagreements by layer).

## Lock files

`groundspec pack lock --pack <id> [--pack <id> ...] [--out groundspec.lock]` writes a canonical-JSON `groundspec.lock`: exact pack IDs, versions, content hashes (SHA-256 over every file in the pack directory, computed fresh at lock time -- never pre-declared by the author), origins, and the dependency closure. Repeated resolution of the same inputs produces byte-identical lock content (no timestamps, no absolute host paths -- an official pack's "source" is a symbolic `official:<name>` marker, a project/user pack's is a path relative to the project root).

## Worked minimal example

```bash
groundspec pack init my-domain --output .groundspec/packs
groundspec pack validate .groundspec/packs/my-domain
groundspec pack test my-domain
groundspec pack resolve --pack my-domain
```

Then edit `pack.toml`'s `description`/`capabilities`, the generated `<pack-id>.toml`'s one example rule into real rules, and `references/domain-guidance.md` into real guidance -- re-run `pack validate`/`pack test` after each change.
