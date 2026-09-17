# Authoring a rule pack

A rule pack is **one JSON or TOML file** validated against [`rule_pack.v0_1_0.schema.json`](../src/groundspec/schema/rule_pack.v0_1_0.schema.json). There is no directory or archive format in v0.1 -- see [threat-model.md](threat-model.md) for why that's a deliberate scope decision, not an oversight.

## Minimal example

```json
{
  "rule_pack_schema_version": "0.1.0",
  "pack_id": "acme-house-style",
  "version": "0.1.0",
  "layer": "project",
  "title": "Acme house style",
  "rules": [
    {
      "id": "no-oxford-comma",
      "version": "0.1.0",
      "title": "Don't use the Oxford comma",
      "purpose": "Match Acme's published style guide.",
      "scope": "Any content-domain task producing external copy.",
      "applies_when": { "path": "routing.domain_packs", "op": "contains", "value": {"pack_id": "content", "version": "0.1.0"} },
      "severity": "soft_objective",
      "requirement": "Lists of three or more items do not use a comma before the final 'and'.",
      "verification_method": "manual_inspection",
      "evidence_requirement": "A reviewer spot-checks list punctuation in the draft.",
      "failure_behavior": "downgrade_score",
      "source_or_rationale": "Acme brand style guide, internal, 2026 edition."
    }
  ]
}
```

Validate it with:

```bash
groundspec pack validate acme-house-style.json
```

## Every rule field

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable within this pack; `^[a-z0-9][a-z0-9_.-]{1,63}$`. |
| `version` | yes | Semver. |
| `title`, `purpose`, `scope` | yes | Human-readable; `purpose` is *why*, `scope` is *when this class of rule applies*. |
| `applies_when` | yes | See "The condition language" below. |
| `severity` | yes | `hard_constraint` (blocks completion), `soft_objective` (feeds the weighted rubric), or `advisory` (surfaced, never gates or scores). |
| `requirement` | yes | The actual rule, in plain language. |
| `verification_method` | yes | `automated_test`, `manual_inspection`, `user_confirmation`, `external_reference_check`, `reproducible_command`, `static_analysis`, or `other`. Be honest here -- `groundspec audit` reports which of your rules are mechanically checkable vs. which need a human/model to actually look. |
| `evidence_requirement` | yes | What evidence would satisfy this rule. |
| `failure_behavior` | yes | `block_completion`, `downgrade_score`, `warn_only`, or `require_escalation`. |
| `source_or_rationale` | yes | Where this rule came from -- a style guide, a past incident, a regulation. |
| `conflict_key` | no, default `""` | See "Conflicts" below. |
| `review_date` | no | `YYYY-MM-DD`. |
| `status` | no, default `active` | `deprecated` rules are loaded but excluded from the active rule set. |
| `replaced_by` | no | Points at the rule id that superseded this one. |

## The condition language

`applies_when` is data, never code. It is one of:

- `true` / `false` -- a literal.
- `{"path": "routing.risk_level", "op": "eq", "value": "high"}` -- a leaf comparison. `path` is a dotted path into the Task Contract. `op` is one of `exists`, `not_exists`, `eq`, `neq`, `in`, `not_in`, `contains`, `gte`, `lte`, `gt`, `lt`. A missing path is `false` for every operator except `not_exists` (which is `true`) -- this is fixed, documented behavior, not a crash.
- `{"all": [condition, ...]}`, `{"any": [condition, ...]}`, `{"not": condition}` -- boolean composition, up to 50 items per list.

There is no way to reach outside the contract, call a function, or execute anything. See `groundspec.rules.condition` for the full (short) implementation.

## Conflicts

If two active rules share the same non-empty `conflict_key` and *disagree* on `requirement`, that's a conflict. It is resolved by layer precedence (core > risk_overlay > domain > project), then alphabetically by `pack_id` as a same-layer tiebreak -- never by load order. The loser is dropped from the active rule set, but the conflict (winner, loser(s), and why) is always recorded on `RuleSet.conflicts` and printed by `groundspec compile`/`audit`. Rules that *agree* on `requirement` under the same `conflict_key` are not a conflict at all. See [examples/09-domain-rule-vs-style-preference](../examples/09-domain-rule-vs-style-preference/) for a real, tested instance.

Only set `conflict_key` when a rule is genuinely making a claim that another pack's rule might contradict (e.g. "respect the platform's format limit" vs. "ignore length limits"). Most rules should leave it empty.

## Imports

A pack may `"imports": [{"pack_id": "...", "version": "..."}]` other packs. Import resolution is by `pack_id`/`version` against an explicit list of search directories -- never by a path embedded in the pack's own content, which is what keeps this safe against a malicious pack trying to read files outside its intended scope (see [threat-model.md](threat-model.md)). Cycles and imports deeper than 4 levels both raise rather than looping or silently truncating.

## Layer

Set `"layer": "project"` for anything you author yourself. `core`, `risk_overlay`, and `domain` are reserved for this project's built-in packs (`src/groundspec/packs/`); a project pack claiming one of those layers is a design smell, not something the schema currently blocks -- if you need a rule to outrank domain packs, that's a signal it might actually belong upstream as a proposed core/domain change instead.

## Untrusted rule packs are data, not instructions

If you load a rule pack you didn't author (shared by a colleague, downloaded from somewhere), remember it can only ever describe requirements *about* a Task Contract -- it cannot execute code, cannot read files outside the search directories you configured, and cannot outrank a higher layer no matter what it claims about itself. Still, review it before trusting its `requirement` text the way you'd review any dependency: nothing stops a rule pack's `requirement` field from containing misleading prose, since that's exactly the kind of natural-language content this framework can't mechanically fact-check.
