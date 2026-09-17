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
- **Existing mitigation:** there is currently only one schema version (`0.1.0`), so there is nothing to downgrade to; the version is a `const`, and `schema_loader` refuses any version it doesn't ship rather than falling back to a "closest match."
- **Remaining risk:** becomes a real concern once `0.2.0` ships -- the migration strategy in `architecture.md` commits to explicit, tested migrations specifically so a downgrade can't be used to smuggle a document past stricter later checks.
- **Test:** `tests/unit/test_contract_roundtrip.py::test_unsupported_schema_version_is_rejected`.
- **User responsibility:** none currently; revisit at the next schema version.

## Confused-deputy authorization errors

- **Asset:** the boundary between "the user authorized this" and "the contract merely mentions this."
- **Attack path:** an executor treats a contract field (e.g. a domain pack's advisory text) as if it were user-granted authorization for an action.
- **Existing mitigation:** `routing.authorization.granted_permissions` is the *only* field the schema treats as authorization; `core-invariants:respect-authorization` is a hard constraint requiring every non-informational action to be inside that list, and every `requires_confirmation_for` entry to be confirmed per-action, not once for the whole task.
- **Remaining risk:** enforcement is instructional, not runtime -- see the deterministic/model-dependent boundary.
- **Test:** `examples/10-unauthorized-external-action`, `tests/integration/test_examples.py::test_10_*`.
- **User responsibility:** grant only what you actually intend to authorize; confirm per-action when asked.

## Personal-data handling

- Covered by the `personal_data` risk overlay (`risk-overlay-personal-data.json`): minimum-necessary collection and diagnostic redaction as hard constraints. See `docs/rule-pack-authoring.md` and PRD Phase 14 for the broader privacy posture (no telemetry, no analytics, local-first).
