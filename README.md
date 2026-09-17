# Groundspec

*A requirements compiler and verification framework for AI agent tasks.*

**Status: pre-release candidate.** The deterministic core, rule engine, three domain packs, CLI, the reusable Meta-Skill, and the Claude Code / Codex / generic adapters are implemented, tested, and passing in cross-platform CI (Ubuntu/Windows/macOS x Python 3.11-3.13; see the [Actions tab](https://github.com/MazenAbbas/groundspec/actions)). PyPI publication and external user validation have not happened yet -- see [Known limitations](#known-limitations--whats-still-pending) below.

## What problem does this solve?

Most people don't fail with AI because the model lacks capability. They fail because their request never specified the real goal, who it's for, what "done" looks like, what must not happen, or what evidence would actually prove it worked. A one-shot prompt has no durable place to record any of that, so a long conversation drifts, a contradiction gets silently resolved however the model guessed, and a half-finished result gets reported as if it were complete.

Groundspec turns an ordinary, incomplete request into a **Task Contract**: a structured, versioned, schema-validated document with a goal, target users, explicit constraints and non-goals, acceptance criteria, a risk level, authorization boundaries, hard constraints, a weighted soft-quality rubric, and time/iteration/tool budgets. It then compiles that contract into instructions an AI agent can actually be held to, and can check the resulting work against the same contract afterward.

## Who is it for?

Non-technical users with a vague request, students planning a project, product managers writing a PRD, developers planning or implementing software, researchers doing evidence-based analysis, marketers producing content, and AI power users who want reusable, auditable Skills. See [examples/](examples/) for one worked scenario per audience.

## Why is this not just another prompt generator?

A prompt generator produces better wording for the same underlying ambiguity. Groundspec instead:

1. Identifies only the missing information that would *materially* change the result (see [Clarification algorithm](#clarification-algorithm)), rather than interrogating the user about everything.
2. Produces a structured, machine-validated contract -- not prose -- with a versioned JSON Schema, so the same contract can be validated, diffed, and audited by tooling other than an LLM.
3. Separates **hard constraints** (binary, a single violation blocks completion) from a **soft loss function** (weighted, improvable, and explicitly non-objective), so safety and correctness can never be outvoted by "the writing sounds better."
4. Ships **risk overlays** and **domain rule packs** as data, with an explicit, auditable precedence order -- not one enormous system prompt trying to cover every profession.
5. Defines budgets and **graceful degradation** up front, so a task that runs out of time reports what was omitted instead of silently claiming success.
6. Works the same whether the executor is Claude Code, OpenAI Codex, or any other chat-based AI tool, via adapters that render the *same* compiled contract three different ways.

## What does it guarantee?

Only what the deterministic core actually does, offline, with no model call:

- Schema validation is strict: unknown keys are rejected, types are never silently coerced, and the schema version is explicit (`contract_schema_version`).
- JSON and TOML serialization are canonical and deterministic (see [docs/schema-reference.md](docs/schema-reference.md#json--toml-round-trip)) -- the same contract always serializes to the same bytes.
- Rule precedence (core > risk overlay > domain > project) is resolved deterministically, and every conflict is recorded with an explanation, never silently dropped.
- A hard-constraint failure can never be outweighed by a soft score (`groundspec.scoring.rubric.score` refuses to produce a passing verdict alongside a failed hard constraint).
- A rule pack cannot execute code: its `applies_when` condition is a small, closed, non-Turing-complete comparison language (`groundspec.rules.condition`), and `pack_id` values are schema-constrained so they can never traverse outside the directories they're looked up in.
- A budget that expires can never be paired with a claimed-complete status (`groundspec.budget.model.forbid_silent_skip_on_expiry`).

## What does it *not* guarantee?

It does not make an incapable model capable, guarantee factual correctness or task success, replace domain expertise or professional review (medical/legal/financial/safety), eliminate hallucinations, infer missing authorization, verify actions it cannot observe, make a malicious tool safe, turn a subjective preference into objective truth, or execute anything remote without approval. Natural-language understanding -- reading a vague brief and drafting a first-pass contract -- is the AI Skill's job, not the deterministic CLI's; see [docs/architecture.md](docs/architecture.md#the-deterministic--model-dependent-boundary) for exactly where that line is drawn, and why crossing it silently is treated as a bug.

## Two ways to use Groundspec

**The Meta-Skill** (`groundspec skill export`) is a reusable, natural-language front end: install it once into Claude Code or Codex, then say "use Groundspec to..." for any new task. It reads your request, classifies what's actually missing, asks only high-value questions, builds and validates a Task Contract through the real CLI (never by hand-writing TOML), routes it to the right rule packs, guides execution, and reports a mechanically-derived completion state. This is the ordinary path -- you never need to touch the schema or the CLI's individual commands directly. See [Quick, Guided, and Audit modes](#quick-guided-and-audit-modes) below.

**Per-task compiled Skills** (`groundspec compile`) are the original, lower-level mechanism from `v0.1`: given an *already-built* Task Contract file, compile it into a one-off Skill or prompt for that specific task. The Meta-Skill uses this internally once it has a contract; you can also use it directly if you're scripting contract creation yourself or already have a contract from somewhere else. Both mechanisms remain fully supported and independent -- the Meta-Skill is additive, not a replacement.

```
                    ┌─────────────────────────────────────────┐
  "use Groundspec   │   Meta-Skill (model-dependent)            │
  to build/study/   │   - classify missing info                 │
  audit X"    ──────▶   - ask only high-value questions          │
                    │   - build contract via `groundspec create`│
                    └───────────────────┬───────────────────────┘
                                        │ Task Contract (TOML/JSON)
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │  Deterministic CLI (groundspec)            │
                    │  validate → audit → compile → evaluate     │
                    └───────────────────┬───────────────────────┘
                                        │ compiled Skill / prompt,
                                        │ then a completion state
                                        ▼
                              PASS / PASS_WITH_CAVEATS /
                              FAIL / INCOMPLETE / BLOCKED
```

Only the top box is model-dependent; everything below the first arrow is the same deterministic engine described throughout this README, unchanged by the Meta-Skill's existence.

## Quick, Guided, and Audit modes

| Mode | For | What happens |
|---|---|---|
| **Quick** | a fast, well-scoped ask | Safe defaults, at most 3 high-value questions, assumptions shown, contract built and validated, reversible work proceeds immediately; stops to ask before anything irreversible/external/costly. |
| **Guided** | product/research/engineering/professional work | Prioritized clarification questions, exposes goal/stakeholders/constraints/acceptance/risk/budget explicitly, explains trade-offs in plain language, shows a contract preview before consequential execution. |
| **Audit** | an existing plan, PRD, prompt, contract, repo, or deliverable | Finds ambiguity, contradictions, missing evidence, hidden assumptions, unverifiable claims, weak acceptance criteria; returns a corrected contract or a remediation report; never modifies the audited artifact unless asked to. |

The Skill detects the likely mode from your request but honors an explicit override ("in guided mode," "just audit this"). Full policy: [the Meta-Skill's own clarification-policy reference](src/groundspec/metaskill/canonical/groundspec/references/clarification-policy.md).

## The Task Contract

A contract is one JSON or TOML document validated against a versioned JSON Schema (currently [`0.1.0`](src/groundspec/schema/task_contract.v0_1_0.schema.json), [`0.2.0`](src/groundspec/schema/task_contract.v0_2_0.schema.json), or [`0.3.0`](src/groundspec/schema/task_contract.v0_3_0.schema.json) -- all three fully supported; see [docs/schema-reference.md](docs/schema-reference.md) for exactly what changed at each step). Top-level sections: `brief` (raw request, normalized problem, goal, users, deliverables), `scope` (constraints, non-goals, assumptions, open questions), `routing` (domain packs, risk overlays, risk level, authorization), `quality` (hard constraints, soft objectives), `acceptance` (criteria with a verification method and required evidence per item), `budget` (time/iteration/tool/cost limits, plus a reserved verification fraction), `control` (stop/escalation conditions), and `status` (completion state, verified facts, unverified claims, remaining uncertainty, residual risks). Full field-by-field reference: [docs/schema-reference.md](docs/schema-reference.md).

## Hard constraints vs. the loss function

**Hard constraints** are binary pass/fail gates (e.g. "no secret may appear in an exported artifact"). A single violation blocks completion regardless of everything else. **Soft objectives** are a weighted rubric over explicitly-labeled dimensions (correctness, requirement coverage, evidence quality, usability, clarity, maintainability, efficiency, uncertainty handling, scope discipline, unsupported claims, acceptance-criteria completeness, resource overrun) -- see [`groundspec.scoring.rubric`](src/groundspec/scoring/rubric.py). The weights are explicit numbers with a stated source (default, domain pack, or user override); they are never claimed to be mathematically objective, a dimension with no evidence is reported as insufficient rather than scored as zero, and no combination of soft scores can ever overturn a failed hard constraint.

## Time, iteration, and budget model

Every contract declares a time budget, a clarification-question budget, planning/execution iteration budgets, a tool-call budget, an optional cost/token budget, and a **reserved verification fraction** -- a slice of the time budget that may never be spent on anything but final verification. See [`groundspec.budget.model`](src/groundspec/budget/model.py). When a budget runs out, the fixed priority order is: protect safety and hard constraints first, preserve the core deliverable, reduce optional depth, report omitted work explicitly, never skip required verification silently, and return incomplete rather than pretend completion -- enforced mechanically by `forbid_silent_skip_on_expiry`, not just documented as a hope.

## How are rule packs selected, and how are conflicts resolved?

Rules are layered, in fixed precedence order: **core invariants** (built in, universal) > **risk overlays** (selected by the contract's declared risk overlays: informational, external communication, filesystem mutation, destructive/irreversible, security-sensitive, high-stakes/regulated, personal data) > **domain packs** (software, research, or content -- selected by `routing.domain_packs`) > **project packs** (supplied locally via `--project-pack`). A lower layer never overrides a higher one. Two rules only conflict if they share an explicit `conflict_key` and disagree on their `requirement`; when that happens, the higher-precedence rule wins and the conflict -- winner, loser, and why -- is recorded, never silently dropped. See [`groundspec.rules.precedence`](src/groundspec/rules/precedence.py) and [examples/09-domain-rule-vs-style-preference](examples/09-domain-rule-vs-style-preference/) for a live instance of this resolving.

## Clarification algorithm

For each piece of missing information, the question is: would the answer materially change the deliverable, does a safe default exist, can it be discovered from context, and would guessing create real risk? The schema (`0.2.0`+) classifies missing information as **blocking** (no useful progress without it), **high-value** (not strictly blocking, but worth asking if the question budget allows -- schema value `high_value`, new in `0.2.0`), **important but defaultable** (a safe, honestly-safe default preserves intent -- apply it and record the assumption; schema value `important_defaultable`; in `0.3.0` an assumption's `safe_default` must actually be `true`, enforced by the schema), or **optional** (doesn't materially change the result -- don't ask, don't record it). This classification lives in `scope.open_questions[].classification` and `scope.assumptions[]` in the schema itself, so it's inspectable after the fact, not just a behavior the model is asked to follow. The Meta-Skill implements the full policy (question budgets per mode, a hard ceiling via `budget.max_clarification_questions`, how to record assumptions) -- see its [clarification-policy reference](src/groundspec/metaskill/canonical/groundspec/references/clarification-policy.md). See [examples/06-contradictory-requirements](examples/06-contradictory-requirements/) for a worked case where two requirements conflict and the resolution is recorded rather than silently picked, and [examples/metaskill/](examples/metaskill/) for the Meta-Skill's own worked scenarios.

## Quickstart (5 minutes)

**Install and export the Meta-Skill into your AI tool:**

```bash
pip install groundspec                                        # once published -- see Known limitations below
groundspec doctor                                              # confirm the install and bundled rule packs are healthy
groundspec skill export --target claude-code --output .        # writes .claude/skills/groundspec/
groundspec skill export --target codex --output .              # writes .agents/skills/groundspec/
```

Then, in Claude Code, invoke it explicitly (`/groundspec use groundspec to study and plan a food-delivery application`) or just describe an ambiguous/multi-step/high-stakes task and let it activate automatically. In Codex, invoke it with `$groundspec` the same way. It will ask at most a few high-value questions, build and validate a real Task Contract behind the scenes (never asking you to write TOML), and report back a `PASS`/`PASS_WITH_CAVEATS`/`FAIL`/`INCOMPLETE`/`BLOCKED` completion state grounded in actual evidence -- see [Quick, Guided, and Audit modes](#quick-guided-and-audit-modes) above.

**Inspecting what it produced:** the Meta-Skill's workflow always leaves a real contract file on disk (wherever the conversation put it) -- open it in any text editor, or run `groundspec validate <file>` / `groundspec audit <file>` yourself to check it independently of whatever the AI told you.

### Under the hood: the same thing via the CLI directly

This is what the Meta-Skill actually runs on your behalf -- useful if you're scripting contract creation yourself, or already have a contract from elsewhere:

```bash
groundspec create --task-id write-launch-post \
  --brief "write a linkedin post announcing our launch" \
  --goal "produce one LinkedIn post announcing the launch" \
  --user "prospective customers" \
  --deliverable "post_draft:Final LinkedIn post text" \
  --risk-overlay informational --risk-overlay external_communication \
  --domain content --out launch-post.toml
groundspec validate launch-post.toml
groundspec audit launch-post.toml
groundspec compile launch-post.toml --target claude-code   # or --target codex / generic
```

`create` with no flags drops into guided mode and asks only the essential questions. See `groundspec --help` and [docs/schema-reference.md](docs/schema-reference.md) for every field.

## Using it in Claude Code

**The Meta-Skill:** `groundspec skill export --target claude-code --output .` writes `.claude/skills/groundspec/SKILL.md` plus its `references/`, matching [Anthropic's documented Skill format](https://code.claude.com/docs/en/skills). Claude Code discovers it under the project's (or, with `--scope user`, your personal) `.claude/skills/` directory; invoke explicitly with `/groundspec` or let it activate automatically.

**Per-task compiled Skills:** `groundspec compile contract.toml --target claude-code --out .` writes `.claude/skills/<task_id>/SKILL.md` (short, frontmatter-only) plus `reference.md` (the full compiled brief) for one already-built contract.

## Using it in Codex

**The Meta-Skill:** `groundspec skill export --target codex --output .` writes `.agents/skills/groundspec/SKILL.md` plus its `references/`, matching [OpenAI's documented Codex Skill format](https://learn.chatgpt.com/docs/build-skills). Invoke with `$groundspec`. Codex also supports `AGENTS.md`-style instructions; the Skill format was chosen here as the closer analogue to a Claude Code Skill (see [docs/adapter-guide.md](docs/adapter-guide.md)).

**Per-task compiled Skills:** `groundspec compile contract.toml --target codex --out .` writes `.agents/skills/<task_id>/SKILL.md` plus `references/contract.md` for one already-built contract.

## Using it with another AI

`groundspec compile contract.toml --target generic` writes a single Markdown prompt with an explicit "limitations of prompt-only enforcement" notice up front: there is no runtime enforcing a plain prompt, so paste it as a system/first-turn message and expect to re-paste it if the conversation runs long. (There is no generic-prompt export for the Meta-Skill itself in this release -- its natural-language workflow assumes a Skill-capable host; the per-task `generic` adapter above is unaffected.)

## Validating a contract

`groundspec validate contract.toml` runs strict schema validation (unknown keys rejected, no type coercion). `groundspec audit contract.toml` additionally resolves the applicable rule packs, reports precedence conflicts, checks budget/verification-reserve sanity, and lists every applicable hard constraint labeled as either mechanically checkable now or requiring human/model judgment -- it never claims to have verified something it can't observe.

## Authoring a rule pack

A rule pack is one JSON or TOML file validated against [`rule_pack.v0_1_0.schema.json`](src/groundspec/schema/rule_pack.v0_1_0.schema.json): a stable ID, a layer (`project` for anything you author locally), and a list of rules, each with an ID, purpose, scope, a small closed `applies_when` condition, severity, requirement, verification method, evidence requirement, and failure behavior. No code execution is possible anywhere in this format. Full guide: [docs/rule-pack-authoring.md](docs/rule-pack-authoring.md). Validate one with `groundspec pack validate path/to/pack.json`.

## How is my data handled?

Local-first, offline-capable after install, no telemetry, no analytics, no account, no remote storage. The deterministic CLI only reads the files you name on the command line and only writes to the output paths you specify; `groundspec skill export` additionally refuses to overwrite an existing export without `--force` and writes atomically (see [docs/threat-model.md](docs/threat-model.md)). The Meta-Skill itself makes no network calls of its own -- whatever AI host is running it (Claude Code, Codex) handles the actual model inference under that host's own data-handling terms, not groundspec's. See [SECURITY.md](SECURITY.md).

## Permission boundaries

Neither the deterministic CLI nor the Meta-Skill will infer authorization for anything consequential. Publishing externally, spending money, an irreversible/destructive action, changing an account, sending a message on your behalf, deploying to production, or handling sensitive/personal data all require an explicit, per-action confirmation -- never a standing approval carried over from earlier in a conversation. This is enforced instructionally in the Meta-Skill (see its [execution-and-verification reference](src/groundspec/metaskill/canonical/groundspec/references/execution-and-verification.md)) and structurally in the contract via `routing.authorization` (`granted_permissions`, `boundaries`, `requires_confirmation_for`) plus the relevant risk-overlay hard constraints -- see [examples/10-unauthorized-external-action](examples/10-unauthorized-external-action/) for a worked case.

## What's experimental, and what still requires human review?

The rule content itself (which requirements belong in each domain pack, and their weights) reflects one reasonable starting design, not a validated standard -- see [Known limitations](#known-limitations--whats-still-pending). Every hard constraint whose `verification_method` is `manual_inspection`, `user_confirmation`, or `external_reference_check` requires a human or the executing AI Skill to actually check it; `groundspec audit`/`evaluate` will tell you which constraints these are, but cannot itself verify them. High-stakes domains (medical/legal/financial/safety) get only the general risk overlay -- see [Product boundaries](#product-boundaries) below. The Meta-Skill's natural-language behavior (mode detection, question selection, judgment calls about evidence) is inherently model-dependent and not deterministic -- see [current evaluation status](#current-evaluation-status).

## Product boundaries

Groundspec does not: make an incapable model capable; guarantee factual correctness or task success; replace domain expertise or required professional review; eliminate hallucinations; infer missing authorization; verify actions it cannot observe; make a malicious tool safe; turn a subjective preference into objective truth; support every profession (three domain packs ship: software, research, content); execute any remote action without approval; or offer a hosted service or third-party rule-pack marketplace. The Meta-Skill specifically does not guarantee it asks the objectively right questions, that its mode/intent detection is always correct, or that its judgment about whether evidence satisfies a criterion is reliable -- it structures and records that judgment so it can be checked, it doesn't replace the checking.

## Current evaluation status

- **Deterministic engine:** fully covered by the automated test suite (counts and results in [CHANGELOG.md](CHANGELOG.md) and each release's notes) -- schema validation, rule precedence, budget arithmetic, and completion-state derivation are all unit- and integration-tested, not just asserted.
- **Meta-Skill, one live run:** [examples/metaskill/03-software-csv-export](examples/metaskill/03-software-csv-export/) is a genuine live dry run -- a fresh, isolated subagent followed only the exported Skill files and the real CLI to complete a real task end to end, independently re-verified afterward. It found and led to fixing four real gaps in the Skill's instructions. It is one scenario, one run, not a statistically powered evaluation.
- **Meta-Skill, three constructed examples:** [examples/metaskill/](examples/metaskill/)'s other three scenarios demonstrate the target contract shape but were authored during development, not captured from a live run -- each says so in its own `session-notes.md`.
- **The 30-scenario deterministic-engine evaluation corpus and its 3-arm baseline comparison protocol** are built (`eval/`) but the live-model comparison itself has not been run -- see [docs/evaluation-methodology.md](docs/evaluation-methodology.md), explicitly marked `PENDING`.
- **External user validation** (non-technical users, students, a PM, a developer, a researcher, a marketer) has not happened -- see [docs/user-validation-protocol.md](docs/user-validation-protocol.md), explicitly marked `PENDING`.

None of the above is invented; where a result doesn't exist yet, it's labeled `PENDING`, not omitted or implied.

## Known limitations / what's still pending

- **Not yet published to PyPI.** The GitHub repository is public and releases ship a wheel and sdist directly; install those, or `pip install -e .` from a clone.
- **Cross-platform CI is green** on Ubuntu/Windows/macOS x Python 3.11-3.13 as of this release -- see `.github/workflows/ci.yml` and the [Actions tab](https://github.com/MazenAbbas/groundspec/actions) for the actual run history.
- **The 30-scenario evaluation corpus ([eval/scenarios/scenarios.json](eval/scenarios/scenarios.json)) and its metrics ([eval/metrics.py](eval/metrics.py)) are built and unit-tested, but the 3-arm baseline comparison itself has not been run against a live model** -- seven scenarios are already mechanically checked against this repository's own deterministic tests (see each scenario's `verified_by` field); the rest are marked `requires_model_run` and PENDING. See [docs/evaluation-methodology.md](docs/evaluation-methodology.md).
- **The Meta-Skill has one genuine live-run evaluation (one scenario) and three constructed examples**, not a full evaluation suite -- see [Current evaluation status](#current-evaluation-status).
- **External user validation (non-technical users, students, a PM, a developer, a researcher, a marketer) has not happened.** See [docs/user-validation-protocol.md](docs/user-validation-protocol.md) for the planned protocol.
- **Only three domain packs exist** (software, research, content); no medical/legal/financial packs are shipped, by design (see Product boundaries).
- **The rule pack format supports a single file only** (no directories or archives), which sidesteps zip-slip/path-traversal risk in archive extraction entirely rather than solving it -- see [docs/threat-model.md](docs/threat-model.md).
- **The Meta-Skill's export safety checks a symlink at the destination and its immediate parent, not the full ancestor chain** -- see [docs/threat-model.md](docs/threat-model.md).

## Documentation

- [docs/architecture.md](docs/architecture.md) -- system design and the deterministic/model-dependent boundary
- [docs/schema-reference.md](docs/schema-reference.md) -- every Task Contract field
- [docs/rule-pack-authoring.md](docs/rule-pack-authoring.md) -- writing your own rule packs
- [docs/adapter-guide.md](docs/adapter-guide.md) -- how the Claude/Codex/generic adapters work
- [docs/threat-model.md](docs/threat-model.md) -- assets, attackers, mitigations, remaining risk
- [docs/evaluation-methodology.md](docs/evaluation-methodology.md) -- metrics, scenarios, and what's pending
- [docs/user-validation-protocol.md](docs/user-validation-protocol.md) -- the planned external testing protocol
- [examples/](examples/) -- ten worked v0.1-style scenarios, each validated by the test suite
- [examples/metaskill/](examples/metaskill/) -- four Meta-Skill scenarios, including one genuine live dry run
- [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CHANGELOG.md](CHANGELOG.md)

## License

[MIT](LICENSE).
