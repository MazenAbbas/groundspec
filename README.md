# Groundspec

*A requirements compiler and verification framework for AI agent tasks.*

**Status: pre-release candidate (v0.1.0rc1).** The deterministic core, rule engine, three domain packs, CLI, and Claude Code / Codex / generic adapters are implemented and tested. Cross-platform CI, PyPI publication, and external user validation have not happened yet -- see [Known limitations](#known-limitations--whats-still-pending) below.

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

## The Task Contract

A contract is one JSON or TOML document validated against [`task_contract.v0_1_0.schema.json`](src/groundspec/schema/task_contract.v0_1_0.schema.json). Top-level sections: `brief` (raw request, normalized problem, goal, users, deliverables), `scope` (constraints, non-goals, assumptions, open questions), `routing` (domain packs, risk overlays, risk level, authorization), `quality` (hard constraints, soft objectives), `acceptance` (criteria with a verification method and required evidence per item), `budget` (time/iteration/tool/cost limits, plus a reserved verification fraction), `control` (stop/escalation conditions), and `status` (completion state, verified facts, unverified claims, remaining uncertainty, residual risks). Full field-by-field reference: [docs/schema-reference.md](docs/schema-reference.md).

## Hard constraints vs. the loss function

**Hard constraints** are binary pass/fail gates (e.g. "no secret may appear in an exported artifact"). A single violation blocks completion regardless of everything else. **Soft objectives** are a weighted rubric over explicitly-labeled dimensions (correctness, requirement coverage, evidence quality, usability, clarity, maintainability, efficiency, uncertainty handling, scope discipline, unsupported claims, acceptance-criteria completeness, resource overrun) -- see [`groundspec.scoring.rubric`](src/groundspec/scoring/rubric.py). The weights are explicit numbers with a stated source (default, domain pack, or user override); they are never claimed to be mathematically objective, a dimension with no evidence is reported as insufficient rather than scored as zero, and no combination of soft scores can ever overturn a failed hard constraint.

## Time, iteration, and budget model

Every contract declares a time budget, a clarification-question budget, planning/execution iteration budgets, a tool-call budget, an optional cost/token budget, and a **reserved verification fraction** -- a slice of the time budget that may never be spent on anything but final verification. See [`groundspec.budget.model`](src/groundspec/budget/model.py). When a budget runs out, the fixed priority order is: protect safety and hard constraints first, preserve the core deliverable, reduce optional depth, report omitted work explicitly, never skip required verification silently, and return incomplete rather than pretend completion -- enforced mechanically by `forbid_silent_skip_on_expiry`, not just documented as a hope.

## How are rule packs selected, and how are conflicts resolved?

Rules are layered, in fixed precedence order: **core invariants** (built in, universal) > **risk overlays** (selected by the contract's declared risk overlays: informational, external communication, filesystem mutation, destructive/irreversible, security-sensitive, high-stakes/regulated, personal data) > **domain packs** (software, research, or content -- selected by `routing.domain_packs`) > **project packs** (supplied locally via `--project-pack`). A lower layer never overrides a higher one. Two rules only conflict if they share an explicit `conflict_key` and disagree on their `requirement`; when that happens, the higher-precedence rule wins and the conflict -- winner, loser, and why -- is recorded, never silently dropped. See [`groundspec.rules.precedence`](src/groundspec/rules/precedence.py) and [examples/09-domain-rule-vs-style-preference](examples/09-domain-rule-vs-style-preference/) for a live instance of this resolving.

## Clarification algorithm

For each piece of missing information, the question is: would the answer materially change the deliverable, does a safe default exist, can it be discovered from context, and would guessing create real risk? Missing information is classified as **blocking** (no useful progress without it), **important but defaultable** (a safe default preserves intent -- apply it and record the assumption), or **optional** (doesn't materially change the result -- don't ask). This classification lives in `scope.open_questions[].classification` and `scope.assumptions[]` in the schema itself, so it's inspectable after the fact, not just a behavior the model is asked to follow. See [examples/06-contradictory-requirements](examples/06-contradictory-requirements/) for a worked case where two requirements conflict and the resolution is recorded rather than silently picked.

## Quickstart

```bash
pip install groundspec        # once published -- see "Known limitations" below
groundspec doctor             # confirm the install and bundled rule packs are healthy
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

`groundspec compile contract.toml --target claude-code --out .` writes `.claude/skills/<task_id>/SKILL.md` (short, frontmatter-only) plus `reference.md` (the full compiled brief), matching [Anthropic's documented Skill format](https://code.claude.com/docs/en/skills). Claude Code will discover it under the project's `.claude/skills/` directory.

## Using it in Codex

`groundspec compile contract.toml --target codex --out .` writes `.agents/skills/<task_id>/SKILL.md` plus `references/contract.md`, matching [OpenAI's documented Codex Skill format](https://learn.chatgpt.com/docs/build-skills). Codex also supports `AGENTS.md`-style instructions; the Skill format was chosen here as the closer analogue to a Claude Code Skill (see [docs/adapter-guide.md](docs/adapter-guide.md)).

## Using it with another AI

`groundspec compile contract.toml --target generic` writes a single Markdown prompt with an explicit "limitations of prompt-only enforcement" notice up front: there is no runtime enforcing a plain prompt, so paste it as a system/first-turn message and expect to re-paste it if the conversation runs long.

## Validating a contract

`groundspec validate contract.toml` runs strict schema validation (unknown keys rejected, no type coercion). `groundspec audit contract.toml` additionally resolves the applicable rule packs, reports precedence conflicts, checks budget/verification-reserve sanity, and lists every applicable hard constraint labeled as either mechanically checkable now or requiring human/model judgment -- it never claims to have verified something it can't observe.

## Authoring a rule pack

A rule pack is one JSON or TOML file validated against [`rule_pack.v0_1_0.schema.json`](src/groundspec/schema/rule_pack.v0_1_0.schema.json): a stable ID, a layer (`project` for anything you author locally), and a list of rules, each with an ID, purpose, scope, a small closed `applies_when` condition, severity, requirement, verification method, evidence requirement, and failure behavior. No code execution is possible anywhere in this format. Full guide: [docs/rule-pack-authoring.md](docs/rule-pack-authoring.md). Validate one with `groundspec pack validate path/to/pack.json`.

## How is my data handled?

Local-first, offline-capable after install, no telemetry, no analytics, no account, no remote storage. The CLI only reads the files you name on the command line and only writes to the output paths you specify. See [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md).

## What's experimental, and what still requires human review?

The rule content itself (which requirements belong in each domain pack, and their weights) reflects one reasonable starting design, not a validated standard -- see [Known limitations](#known-limitations--whats-still-pending). Every hard constraint whose `verification_method` is `manual_inspection`, `user_confirmation`, or `external_reference_check` requires a human or the executing AI Skill to actually check it; `groundspec audit`/`evaluate` will tell you which constraints these are, but cannot itself verify them. High-stakes domains (medical/legal/financial/safety) get only the general risk overlay in v0.1 -- see [Product boundaries](#product-boundaries) below.

## Product boundaries

Groundspec does not: make an incapable model capable; guarantee factual correctness or task success; replace domain expertise or required professional review; eliminate hallucinations; infer missing authorization; verify actions it cannot observe; make a malicious tool safe; turn a subjective preference into objective truth; support every profession (v0.1 ships three domain packs: software, research, content); execute any remote action without approval; or offer a hosted service or third-party rule-pack marketplace.

## Known limitations / what's still pending

- **Not yet published to PyPI or GitHub as public.** All commands above work from a local clone (`pip install -e .`).
- **Cross-platform CI is authored but its green-run history is not yet established** -- see `.github/workflows/ci.yml` and [docs/architecture.md](docs/architecture.md).
- **The evaluation corpus (30 scenarios, [eval/scenarios/scenarios.json](eval/scenarios/scenarios.json)) and its metrics ([eval/metrics.py](eval/metrics.py)) are built and unit-tested, but the 3-arm baseline comparison itself has not been run against a live model** -- seven scenarios are already mechanically checked against this repository's own deterministic tests (see each scenario's `verified_by` field); the rest are marked `requires_model_run` and PENDING. See [docs/evaluation-methodology.md](docs/evaluation-methodology.md).
- **External user validation (non-technical users, students, a PM, a developer, a researcher, a marketer) has not happened.** See [docs/user-validation-protocol.md](docs/user-validation-protocol.md) for the planned protocol.
- **Only three domain packs exist** (software, research, content); no medical/legal/financial packs are shipped, by design (see Product boundaries).
- **The rule pack format supports a single file only** (no directories or archives) in v0.1, which sidesteps zip-slip/path-traversal risk in archive extraction entirely rather than solving it -- see [docs/threat-model.md](docs/threat-model.md).

## Documentation

- [docs/architecture.md](docs/architecture.md) -- system design and the deterministic/model-dependent boundary
- [docs/schema-reference.md](docs/schema-reference.md) -- every Task Contract field
- [docs/rule-pack-authoring.md](docs/rule-pack-authoring.md) -- writing your own rule packs
- [docs/adapter-guide.md](docs/adapter-guide.md) -- how the Claude/Codex/generic adapters work
- [docs/threat-model.md](docs/threat-model.md) -- assets, attackers, mitigations, remaining risk
- [docs/evaluation-methodology.md](docs/evaluation-methodology.md) -- metrics, scenarios, and what's pending
- [docs/user-validation-protocol.md](docs/user-validation-protocol.md) -- the planned external testing protocol
- [examples/](examples/) -- ten worked scenarios, each validated by the test suite
- [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CHANGELOG.md](CHANGELOG.md)

## License

[MIT](LICENSE).
