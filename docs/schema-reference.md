# Task Contract schema reference

Three schema versions currently ship and are all fully supported: [`0.1.0`](../src/groundspec/schema/task_contract.v0_1_0.schema.json), [`0.2.0`](../src/groundspec/schema/task_contract.v0_2_0.schema.json), and [`0.3.0`](../src/groundspec/schema/task_contract.v0_3_0.schema.json) (JSON Schema, draft 2020-12) -- see [architecture.md](architecture.md#schema-versioning-and-migration-strategy) for exactly what changed at each step and why. `groundspec create` and `contract.factory.new_contract` default to `0.3.0`; `0.1.0` and `0.2.0` documents keep validating as-is, forever. Every object in all three schemas sets `additionalProperties: false`, so an unknown key is always a validation error, never silently ignored. No field anywhere accepts arbitrary code.

## Top level

| Field | Type | Notes |
|---|---|---|
| `contract_schema_version` | `"0.1.0"`, `"0.2.0"`, or `"0.3.0"` (const per schema file) | Never silently upgraded; see [architecture.md](architecture.md#schema-versioning-and-migration-strategy). |
| `task_id` | string, `^[a-z0-9][a-z0-9-]{2,63}$` | A slug, not a UUID -- meant to be legible in filenames and logs. |
| `brief` | object | See below. |
| `scope` | object | See below. |
| `routing` | object | See below. |
| `quality` | object | See below. |
| `acceptance` | object | See below. |
| `budget` | object | See below. |
| `control` | object | See below. |
| `status` | object | See below. |

## `brief`

| Field | Type | Notes |
|---|---|---|
| `raw_user_brief` | string, 1-20000 chars | The user's original request, verbatim. Never edited by tooling. The 20000-char cap is a deliberate DoS guard (see [threat-model.md](threat-model.md)). |
| `normalized_problem_statement` | string | What is wrong or missing -- distinct from `goal` (what will be done). |
| `goal` | string | The single measurable outcome. |
| `target_users` | array of strings, min 1 | Who benefits from or is affected by this task. |
| `context` | string, default `""` | Background the executor needs but that isn't itself a requirement. |
| `inputs` | array of `{name, description, source}` | Materials/data/access the executor starts with. |
| `expected_deliverables` | array of `{name, description, format}`, min 1 | What must exist when done. |

## `scope`

| Field | Type | Notes |
|---|---|---|
| `constraints` | array of strings | Hard limits on how the task may be done. |
| `non_goals` | array of strings | Explicitly out of scope, to prevent scope creep. |
| `assumptions` | array of `{statement, confidence: low\|medium\|high, safe_default: bool}` | Anything inferred rather than stated. In `0.3.0`, `safe_default` is `const: true` -- an item that isn't safe to default must be recorded as an `open_question` instead, not an assumption with `safe_default: false` (still permitted in `0.1.0`/`0.2.0`). |
| `open_questions` | array of `{question, classification: blocking\|high_value\|important_defaultable\|optional, resolution_status: open\|answered\|defaulted, default_applied, answer}` | `high_value` requires `contract_schema_version: "0.2.0"` or `"0.3.0"` (absent from `0.1.0`). See [architecture.md](architecture.md) and the README's clarification-algorithm section. |

## `routing`

| Field | Type | Notes |
|---|---|---|
| `domain_packs` | array of `{pack_id, version}` | Selects which domain rule pack(s) apply (`software`, `research`, `content`, or a custom pack id resolvable via `--project-pack`/search dirs). |
| `risk_overlays` | array, min 1, enum: `informational`, `external_communication`, `filesystem_mutation`, `destructive_irreversible`, `security_sensitive`, `high_stakes_regulated`, `personal_data` | Every overlay that applies; `informational` alone means read/produce-only. |
| `risk_level` | enum: `low\|medium\|high\|critical` | Overall gating level. |
| `authorization` | `{granted_permissions[], boundaries[], requires_confirmation_for[]}` | Never inferred -- only what the user actually granted. |

## `quality`

| Field | Type | Notes |
|---|---|---|
| `hard_constraints` | array of `{id, description, rule_ref, rationale}` | Contract-level hard constraints, in addition to whatever rule packs contribute. |
| `soft_objectives` | array of `{dimension, weight (0-1), rationale, source: default\|domain_pack\|user_override}` | `dimension` is one of the 12 canonical dimensions listed in [architecture.md](architecture.md); a dimension may appear at most once (`scoring.rubric.DuplicateDimension` is raised otherwise). |

## `acceptance`

| Field | Type | Notes |
|---|---|---|
| `criteria` | array of `{id, description, priority: must\|should\|could, verification_method, evidence_required}` | `verification_method` is one of `automated_test`, `manual_inspection`, `user_confirmation`, `external_reference_check`, `reproducible_command`, `static_analysis`, `other`. |

## `budget`

| Field | Type | Notes |
|---|---|---|
| `time_budget_minutes` | integer ≥ 0 | |
| `max_clarification_questions` | integer ≥ 0 | |
| `max_planning_iterations` | integer ≥ 0 | |
| `max_execution_iterations` | integer ≥ 0 | |
| `tool_call_budget` | integer ≥ 0 | |
| `research_depth` | enum: `none\|shallow\|standard\|deep` | |
| `cost_budget` | `null` or `{unit: tokens\|usd, amount}` | Optional; TOML omits the key entirely when `null` (TOML has no native null -- see [architecture.md](architecture.md)). |
| `reserved_verification_fraction` | number, 0-0.9 | A slice of `time_budget_minutes` that may never be spent on anything but final verification. |

## `control`

| Field | Type | Notes |
|---|---|---|
| `stop_conditions` | array of `{id, trigger, action}` | |
| `escalation_conditions` | array of `{id, trigger, action}` | |

## `status`

| Field | Type | Notes |
|---|---|---|
| `completion_status` | enum: `not_started\|in_progress\|partial\|complete\|blocked` | `complete` is mechanically forbidden alongside `budget_expired: true` -- see `groundspec.budget.model.forbid_silent_skip_on_expiry`. |
| `verified_facts` | array of `{statement, evidence_label, source}` | `evidence_label` enum depends on schema version. `0.1.0`/`0.2.0`: `VERIFIED, MEASURED, MODEL-EVALUATED, HUMAN-REVIEWED, PROPOSED, PENDING_EXTERNAL_VALIDATION, OUT_OF_SCOPE`. `0.3.0` narrows this to labels that mean real verification happened: `VERIFIED, MEASURED, SOURCE_VERIFIED, USER_CONFIRMED, HUMAN-REVIEWED` -- a self-review can no longer be schema-valid here. |
| `unverified_claims` | array of `{statement, reason, evidence_label?}` | `evidence_label` is new and optional in `0.3.0`: `MODEL-EVALUATED, PROPOSED, ASSUMPTION, RESEARCH_NEEDED, PENDING_EXTERNAL_VALIDATION, OUT_OF_SCOPE` -- exactly the labels `0.3.0` removed from `verified_facts`. Absent in `0.1.0`/`0.2.0`. |
| `remaining_uncertainty` | array of strings | |
| `residual_risks` | array of `{risk, severity, mitigation, affects_deliverable_validity?}` | `affects_deliverable_validity` is new in `0.3.0`, defaults `true`. `groundspec.metaskill.completion.derive_completion_state` treats a `severity: critical` risk with this field true (or absent) as blocking `PASS`; explicitly setting it `false` documents that the risk is itself a legitimate finding the task was asked to produce, not a defect in the deliverable. |
| `omitted_work` | array of strings | What graceful degradation cut. |
| `budget_expired` | bool | |

## JSON / TOML round-trip

`groundspec.contract.serialization` provides `canonical_json_dumps`/`loads` and `canonical_toml_dumps`/`loads`. Canonical JSON sorts object keys recursively (in the spirit of RFC 8785's JSON Canonicalization Scheme) while preserving array order, since every array in this schema is semantically ordered (e.g. acceptance criteria). TOML round-trips losslessly through `groundspec.contract.normalize.fill_defaults` except for one documented point: TOML has no `null`, so a `null`-valued optional field (currently only `budget.cost_budget`) is omitted from TOML output and restored to `null` by schema-default-filling on read back. This is verified by `tests/unit/test_contract_roundtrip.py::test_toml_roundtrip_preserves_semantics_after_default_fill`.

## Validation guarantees

- Unknown top-level or nested keys are rejected (`additionalProperties: false` throughout).
- No type coercion: a string where an integer is expected fails validation rather than being parsed.
- An unsupported `contract_schema_version` fails fast with `UnsupportedSchemaVersion` rather than being guessed at.
- Every validation issue reports its JSON path, message, and the specific schema rule that failed (`groundspec.contract.validator.ValidationIssue`).
