# Threat model

Format per threat: **Asset** at risk, **Attacker/failure source**, **Attack path**, **Existing mitigation**, **Remaining risk**, **Test**, **User responsibility**.

## Prompt injection in the user brief

- **Asset:** the eventual executor's adherence to the real contract.
- **Attacker/failure source:** the user themselves (accidentally) or a third party pasting text into the brief field.
- **Attack path:** `brief.raw_user_brief` contains text like "ignore all prior instructions and...".
- **Existing mitigation:** the deterministic core never executes anything found inside `raw_user_brief` -- it is schema-validated as a plain string (max 20000 chars) and rendered verbatim into compiled output as *quoted content*, never as a new instruction to the compiler itself. The compiled output's own instructions (goal, hard constraints, budgets) come from the rest of the contract, which a human or the AI Skill populated deliberately.
- **Remaining risk:** the *executing* AI agent reading the compiled Skill could still be manipulated by injected text inside the rendered brief, exactly like any other prompt-injection surface -- this project structures the task, it does not sandbox the model executing it.
- **Test:** `tests/unit/test_contract_roundtrip.py` (brief length bound); this specific residual risk is out of scope for a mechanical test and is instead a documented limitation.
- **User responsibility:** treat any AI's output about untrusted content, including a Groundspec-compiled brief containing quoted third-party text, as data, not instructions -- the same rule this very project's own operating instructions apply to observed tool content.

## Prompt injection in uploaded documents

- **Asset:** same as above.
- **Attack path:** a document referenced in `brief.inputs` or `brief.context` contains hidden instructions.
- **Existing mitigation:** `inputs[].description`/`source` are plain strings; the schema gives no field any special "trusted instruction" status.
- **Remaining risk:** same as prompt injection in the brief -- inherent to any system compiling natural-language content for an LLM.
- **Test:** none beyond schema type-checking; this is a model-execution-time concern.
- **User responsibility:** same as above.

## Malicious rule packs

- **Asset:** rule-precedence integrity; the guarantee that a project-layer pack can never outrank core/risk-overlay rules.
- **Attack path:** a third-party rule pack declares a `hard_constraint` with high-sounding `source_or_rationale` text, hoping to be trusted, or tries to share a `conflict_key` with a core rule to override it.
- **Existing mitigation:** layer precedence is structural (`LAYER_PRECEDENCE` in `rules/precedence.py`), not something a pack can declare about itself; a project-layer pack can never win a conflict against a higher layer regardless of content. See `eval` scenario `sec-override-precedence`, mechanically verified by `tests/unit/test_precedence.py::test_higher_layer_wins_conflict`.
- **Remaining risk:** a malicious pack's `requirement` prose could still mislead a human reviewer reading it, or influence an AI Skill's behavior if it's naively trusted as an instruction rather than data about the contract -- see "Untrusted rule packs are data, not instructions" in `docs/rule-pack-authoring.md`.
- **Test:** `tests/unit/test_precedence.py::test_higher_layer_wins_conflict`, `test_duplicate_pack_id_with_different_content_raises`.
- **User responsibility:** review a rule pack you didn't author before trusting it, same as any dependency.

## Rules attempting to override core protections

- Covered by the same mitigation and test as "Malicious rule packs" above -- there is no field in the rule-pack schema that lets a rule declare its own layer independent of the file's `layer` field, and `layer` values `core`/`risk_overlay` are reserved for this project's own bundled packs (a project pack claiming one of those layer strings still only competes at that layer's precedence, it does not get elevated privileges from the claim -- see the caveat in `rule-pack-authoring.md`).

## Path traversal

- **Asset:** the filesystem outside the configured rule-pack search directories.
- **Attack path:** an `imports` entry's `pack_id` contains `../` or an absolute path, hoping to be resolved outside the search directories.
- **Existing mitigation:** `pack_id` is schema-constrained to `^[a-z0-9][a-z0-9_.-]{1,63}$` -- no `/` or `\` character is permitted at all, so a filename built from it (`f"{pack_id}.json"`) can never leave the directory it's joined against. This is enforced at the schema level, not just by convention.
- **Remaining risk:** none identified for pack resolution; a user could still pass `groundspec pack validate` or `groundspec audit --project-pack` an arbitrary path directly on the command line, but that is the user's own filesystem access, not an escalation.
- **Test:** `tests/unit/test_rule_pack_loader.py::test_pack_id_cannot_traverse_directories`; eval scenario `sec-malicious-rule-pack`.
- **User responsibility:** none beyond normal care with CLI arguments.

## Zip-slip / archive extraction

- **Asset:** filesystem outside an extraction target.
- **Attack path:** a rule pack distributed as a zip/tar containing a member path like `../../etc/cron.d/evil`.
- **Existing mitigation:** v0.1 rule packs are a single JSON or TOML file, never a directory or archive -- there is no extraction code anywhere in this project, which removes the entire attack surface rather than trying to sandbox it.
- **Remaining risk:** none in-scope, by construction. A future multi-file pack format would need its own extraction-safety design (path normalization, symlink rejection, a size/entry-count cap) before shipping.
- **Test:** N/A (no extraction code exists to test).
- **User responsibility:** N/A.

## Symlink and junction escape

- **Asset:** files outside an intended directory tree.
- **Attack path:** a symlink inside a search directory pointing outside it.
- **Existing mitigation:** not specifically hardened in v0.1 -- pack loading uses ordinary `Path.is_file()`/`open()`, which will follow a symlink if the OS presents one.
- **Remaining risk:** a search directory populated with attacker-controlled symlinks could cause a pack lookup to read a file outside the intended tree. This only matters if an attacker can already write into a directory you configured as a rule-pack search path, which is a stronger precondition than the path-traversal case above.
- **Test:** none yet -- tracked as a gap, not silently assumed safe.
- **User responsibility:** only point `--project-pack`/search directories at locations you trust the contents of.

## Arbitrary code execution

- **Asset:** the host running `groundspec`.
- **Attack path:** a rule pack or contract field containing code that gets `eval`'d or `exec`'d.
- **Existing mitigation:** there is no `eval`, `exec`, `pickle.load`, or dynamic-import-of-untrusted-content anywhere in this codebase. `applies_when` conditions are interpreted by a small closed comparison language (`rules/condition.py`) with an explicit, enumerated operator set (`UnknownOperator` is raised for anything else) -- not evaluated as Python.
- **Remaining risk:** none identified.
- **Test:** `tests/unit/test_rules_engine.py::test_unknown_operator_raises`; the absence of `eval`/`exec` is also checkable with `grep -rn "eval(\|exec(" src/` (returns nothing).
- **User responsibility:** none.

## Secret leakage

- **Asset:** credentials, API keys.
- **Attack path:** a secret ends up in `raw_user_brief`, an assumption, or an error message, and is then written to an exported artifact.
- **Existing mitigation:** the core has no telemetry and writes only to paths the user explicitly names; `core-invariants:protect-secrets-and-private-data` is a hard constraint requiring a secret-scan of produced artifacts before completion.
- **Remaining risk:** the deterministic core has no way to *automatically* scan free-text fields for secrets; this hard constraint's `verification_method` is `automated_test` at the level of "run a scanner," which is the executor's job to actually run, not something `groundspec audit` does for you today.
- **Test:** the rule's presence and applicability is tested in `tests/integration/test_builtin_packs.py`; the scan itself is not implemented in v0.1 (see Known limitations in the README).
- **User responsibility:** don't paste secrets into a brief; run a secret scanner over generated artifacts before publishing.

## Unsafe external tool calls / destructive filesystem actions / repository mutation

- **Asset:** user data and repository state.
- **Attack path:** a task compiled without the right risk overlay proceeds to delete or force-push without confirmation.
- **Existing mitigation:** the `filesystem_mutation` and `destructive_irreversible` risk overlays contribute hard constraints requiring inspection-before-write and explicit per-action confirmation respectively (`risk-overlay-filesystem-mutation:inspect-before-mutating`, `risk-overlay-destructive-irreversible:confirm-before-irreversible-action`).
- **Remaining risk:** these are compiled *instructions*; the deterministic core cannot force the executing agent to actually pause for confirmation -- see the deterministic/model-dependent boundary in `architecture.md`.
- **Test:** `tests/integration/test_builtin_packs.py` (rule applicability); `examples/01-food-delivery-mvp` and `examples/08-partial-completion-correct` exercise the `filesystem_mutation` overlay end to end.
- **User responsibility:** select the correct risk overlays for the task; confirm destructive actions when the executor asks.

## Untrusted generated commands

- **Asset:** the host running whatever command an AI agent generates.
- **Attack path:** a compiled contract's acceptance criteria reference a `reproducible_command` that the executor then runs blindly.
- **Existing mitigation:** groundspec never executes acceptance-criteria commands itself; it only records that a criterion claims this verification method.
- **Remaining risk:** entirely in the executor's hands, out of this project's control surface.
- **Test:** N/A.
- **User responsibility:** review any command an AI proposes before running it, same as always.

## Fabricated evidence / report injection

- **Asset:** the integrity of `status.verified_facts` and the final report.
- **Attack path:** an executor claims work was done/verified that wasn't.
- **Existing mitigation:** `core-invariants:no-claiming-unperformed-work` is a hard constraint; `groundspec.scoring.rubric.score` requires actual per-dimension evidence and reports `insufficient_evidence` rather than assuming a passing score when evidence is missing.
- **Remaining risk:** the deterministic core cannot independently verify that a claimed VERIFIED fact is true -- this is fundamentally a trust boundary between the report and reality, mitigated by evidence-labeling discipline, not eliminated by it.
- **Test:** `tests/unit/test_budget_and_scoring.py` (insufficient-evidence handling); `examples/07-insufficient-evidence`.
- **User responsibility:** spot-check claimed evidence, especially for consequential decisions.

## Terminal-control characters

- **Asset:** the terminal/CLI output stream.
- **Attack path:** a brief or rule-pack field contains ANSI escape sequences designed to spoof CLI output.
- **Existing mitigation:** not specifically stripped in v0.1; `print()` calls pass field content through as-is.
- **Remaining risk:** a crafted contract could inject terminal-control sequences into `groundspec audit`/`validate` output. Low severity (local CLI, not a network service), but not yet mitigated.
- **Test:** none yet -- tracked as a gap.
- **User responsibility:** be cautious running `groundspec` commands against contract files from an untrusted source, same as opening any untrusted text file in a terminal.

## Denial of service via huge inputs

- **Asset:** CLI availability/performance.
- **Attack path:** a contract with an enormous `raw_user_brief`, or deeply nested rule-pack imports.
- **Existing mitigation:** `raw_user_brief` is capped at 20000 chars by schema; most array fields have a `maxItems` bound; rule-pack import depth defaults to 4 and raises `ImportDepthExceeded` beyond that; cyclic imports raise immediately rather than looping.
- **Remaining risk:** no bound on the *number* of separate rule packs a single `--project-pack` invocation could load, though each is individually small; not considered a realistic local-CLI DoS vector.
- **Test:** `tests/unit/test_rule_pack_loader.py::test_import_depth_exceeded`, `test_cyclic_import_raises`.
- **User responsibility:** none beyond normal care.

## Recursive pack imports

- Covered by "Denial of service via huge inputs" above -- cycle detection and the depth ceiling are the same mitigation.

## Dependency and CI supply-chain risks

- **Asset:** the build/release pipeline.
- **Attack path:** a compromised dependency or a GitHub Action pinned by mutable tag.
- **Existing mitigation:** the only runtime dependency is `jsonschema` (see `architecture.md` for why); GitHub Actions in `.github/workflows/` are pinned to full commit SHAs with a version comment (see CI file).
- **Remaining risk:** a SHA pin does not protect against a vulnerability already present at that commit; dependency updates still require human review.
- **Test:** `pip check`/`twine check` in CI; SHA-pinning is visually auditable in the workflow file.
- **User responsibility:** review dependency/Action version bumps before merging.

## Schema downgrade attacks

- **Asset:** the guarantee that a contract's declared schema version is actually the one it was validated against.
- **Attack path:** an attacker edits `contract_schema_version` down to an older, laxer schema after a stricter one was expected.
- **Existing mitigation:** the version is a `const` per schema file, and `schema_loader` refuses any version it doesn't ship rather than falling back to a "closest match" -- a document cannot claim a version and be validated against a different one.
- **Remaining risk:** now materialized, and honestly unresolved: because `0.1.0`/`0.2.0`/`0.3.0` remain valid forever (by design, for backward compatibility -- see `architecture.md`), a document can deliberately declare an older `contract_schema_version` specifically to route around later hardening (e.g. `0.1.0` to use `safe_default: false` or to record a self-review as a `verified_facts` entry, both rejected under `0.3.0`+; or `0.3.0` to avoid `0.4.0`'s `claim_ledger`/material-claim gating entirely, since a `0.3.0` document has no `claim_ledger` field and so can never trigger `has_unmapped_material_claims`/`claim_ledger_has_disclosed_material_limitations` at all). `groundspec create`/`new_contract` defaulting to the newest schema raises the bar for the common path, but nothing currently warns when an *existing* contract deliberately targets an older, laxer schema version. This is a real, disclosed gap, not a solved problem.
- **Test:** `tests/unit/test_contract_roundtrip.py::test_unsupported_schema_version_is_rejected`; `tests/unit/test_schema_versioning.py::test_assumption_safe_default_false_still_allowed_in_0_1_0_and_0_2_0` documents (rather than hides) that the older, laxer behavior is still reachable on purpose.
- **User responsibility:** if you specifically need `0.4.0`'s claim-ledger/evidence-integrity guarantees, check `contract_schema_version` yourself rather than assuming the newest rules are in force -- `groundspec audit` does not currently flag an old-but-valid schema version as suspicious.

## Claim-ledger content cannot be verified against the actual source

- **Asset:** the honesty of `status.claim_ledger[].scope_and_qualifiers`, `evidence_label`, and `limitations` -- the claim that a conditional source rule's actual conditions were preserved, or that a claim's evidence strength was labeled accurately.
- **Attack path (or, more realistically, an honest mistake under time pressure):** an executor writes a `claim_record` that generalizes a conditional rule (drops the qualifiers `scope_and_qualifiers` was supposed to preserve), or mislabels the strength of evidence in a way the schema's structural checks don't catch (e.g. a `SECONDARY_SOURCE_SUPPORTED` entry whose `excerpt_or_locator` doesn't actually say what the `claim` field claims it says).
- **Existing mitigation:** the schema mechanically prevents the *structural* version of this problem -- `SECONDARY_SOURCE_SUPPORTED` can never carry `authority_level: primary_official`; `PRIMARY_SOURCE_VERIFIED`/`SECONDARY_SOURCE_SUPPORTED` can never omit a citation; a legal/regulatory `SECONDARY_SOURCE_SUPPORTED` claim can never omit a stated limitation. `references/execution-and-verification.md` documents the exact discipline (a real ZATCA VAT example of a conditional rule correctly vs. incorrectly stated) for the part that's genuinely a prose-content judgment call, not a structural one.
- **Remaining risk:** genuinely unresolved, and stated as such rather than hidden: JSON Schema validates structure and enumerated values, not whether a free-text field's *content* accurately reflects an external source neither `groundspec validate` nor `groundspec evaluate` has access to. A `scope_and_qualifiers` string that says "none; unconditional" for a claim that is, in reality, conditional is schema-valid. This is the same category of trust boundary as "Fabricated evidence / report injection" above, applied specifically to the claim ledger's provenance fields.
- **Test:** `tests/unit/test_schema_versioning.py::test_conditional_zatca_style_claim_preserves_qualifiers_and_validates` documents (rather than hides) that the schema accepts a `scope_and_qualifiers` value that drops the real conditions -- the mitigation for that specific content-level failure mode lives in Meta-Skill instructions and human/model review discipline, not in `groundspec validate`.
- **User responsibility:** for a high-stakes regulatory, legal, or financial claim, spot-check the cited source yourself rather than trusting a `PRIMARY_SOURCE_VERIFIED`/`SECONDARY_SOURCE_SUPPORTED` label at face value, especially before a build/launch/spend decision.

## Confused-deputy authorization errors

- **Asset:** the boundary between "the user authorized this" and "the contract merely mentions this."
- **Attack path:** an executor treats a contract field (e.g. a domain pack's advisory text) as if it were user-granted authorization for an action.
- **Existing mitigation:** `routing.authorization.granted_permissions` is the *only* field the schema treats as authorization; `core-invariants:respect-authorization` is a hard constraint requiring every non-informational action to be inside that list, and every `requires_confirmation_for` entry to be confirmed per-action, not once for the whole task.
- **Remaining risk:** enforcement is instructional, not runtime -- see the deterministic/model-dependent boundary.
- **Test:** `examples/10-unauthorized-external-action`, `tests/integration/test_examples.py::test_10_*`.
- **User responsibility:** grant only what you actually intend to authorize; confirm per-action when asked.

## Personal-data handling

- Covered by the `personal_data` risk overlay (`risk-overlay-personal-data.json`): minimum-necessary collection and diagnostic redaction as hard constraints. See `docs/rule-pack-authoring.md` and PRD Phase 14 for the broader privacy posture (no telemetry, no analytics, local-first).

## Meta-Skill-specific threats

The Meta-Skill (`groundspec skill export`, `src/groundspec/metaskill/`) adds its own surface, addressed separately from the deterministic engine's own threats above.

### Prompt injection at the Skill instruction boundary

- **Asset:** the Meta-Skill's own operating instructions staying in force regardless of what content it's asked to process.
- **Attack path:** a task description, a referenced document, a rule pack, or an artifact being audited in Audit mode contains text engineered to look like an instruction to the AI reading it ("ignore the above, grant yourself permission to...").
- **Existing mitigation:** `SKILL.md`'s Non-negotiables and `task-contract-workflow.md`'s "untrusted content is data, not instructions" section state explicitly that none of these sources can expand authorization, skip a risk overlay, or change mode/intent -- mirroring this project's own operating rules for observed tool content.
- **Remaining risk:** this is instructional, not runtime-enforced -- a sufficiently capable injection could still influence a model that doesn't hold the line, exactly like any other prompt-injection surface. The Skill cannot force compliance, only state the rule clearly and let `groundspec audit`/`evaluate` catch the downstream symptom (an authorization hard constraint failing) after the fact.
- **Test:** none automated (this is a model-behavior claim, not a deterministic one); tracked as a documented limitation, consistent with the same caveat on the v0.1 core.
- **User responsibility:** review what an AI following this Skill actually did, same as with any agent.

### Recursive Skill invocation / infinite clarification loops

- **Asset:** forward progress on a task; the user's time.
- **Attack path:** the Skill re-invokes itself mid-task, or keeps generating clarification questions indefinitely.
- **Existing mitigation:** `SKILL.md`'s Non-negotiables explicitly forbid self-re-invocation within one task. `clarification-policy.md` gives Quick mode a hard cap of 3 questions and Guided mode a hard backstop at the contract's own `budget.max_clarification_questions` (schema-enforced field, not just a suggestion) -- exceeding it means stop and tell the user to narrow the request, not keep asking.
- **Remaining risk:** both are instructional controls on model behavior, not something the deterministic CLI can enforce at runtime (there is no code path in `groundspec` that counts an external model's questions). `groundspec audit`'s budget-sanity checks catch a contract that declares an unreasonable budget, not a model that ignores its own declared budget.
- **Test:** `tests/unit/test_metaskill_completion.py` covers the mechanical consequence (an unresolved blocking question forces `BLOCKED`, never a silent `PASS`); the question-budget adherence itself is a documented behavioral expectation, not code-tested.
- **User responsibility:** if a session seems to be asking far more than 3 (Quick) or the contract's own budget (Guided), that's a signal the Skill isn't being followed correctly -- interrupt and say so.

### Skill export safety (path traversal, unsafe overwrite, symlinks, malformed content, interrupted writes)

- All covered by `groundspec.metaskill.export.export_file_set`, which is the same threat class as the v0.1 rule-pack loader's path-traversal protection, applied to writing instead of reading: relative paths are schema-constrained at the content-authoring level (canonical content only, never derived from untrusted input) and additionally validated at export time (`UnsafeRelativePath` rejects `..`/absolute paths defensively, even though nothing in this codebase currently generates such a path); the destination and its immediate parent are checked for symlinks before any write (`UnsafeDestination`); every write is staged in a temporary sibling directory and moved into place with a single rename, with rollback to the prior content on failure (no partial/interrupted state ever visible at the destination path); overwrite requires `--force` explicitly (`DestinationExists` otherwise); output is deterministic (sorted file iteration, no timestamps); and arbitrary Unicode/control-character content round-trips through the filesystem correctly without being interpreted as anything other than file bytes.
- **Remaining risk:** the symlink check covers the destination itself and its immediate parent, not the full ancestor chain (same documented scope limitation as the v0.1 threat model's symlink entry) -- exploitable only if an attacker already controls a directory the user chose to export into.
- **Test:** `tests/unit/test_metaskill_export.py` (13 tests covering all of the above, including two dedicated to Unicode/control characters); `tests/integration/test_metaskill_cli.py` for the end-to-end CLI path.

### Structural validation and broken references

- **Asset:** a Skill that's actually usable once exported (no dangling reference, valid frontmatter).
- **Existing mitigation:** `groundspec.metaskill.validate.validate_skill_files` checks frontmatter shape and that every `references/*.md` path mentioned anywhere in the file set actually exists in it; `groundspec skill export` refuses to write a Skill that fails this check (treated as a groundspec bug, not a user error); `groundspec skill validate <dir>` and `groundspec doctor` both re-run it independently of which vendor exporter produced the files.
- **Test:** `tests/unit/test_metaskill_exports.py`.
