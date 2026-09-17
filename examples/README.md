# Examples

Ten scenarios, each a real `contract.toml` validated and exercised by `tests/integration/test_examples.py` (run `pytest tests/integration/test_examples.py -v` to see every assertion execute against these exact files). They are not decorative: if you edit a contract here in a way that breaks its scenario, the test suite fails.

| # | Scenario | What it demonstrates |
|---|----------|----------------------|
| [01](01-food-delivery-mvp/contract.toml) | "I want a food delivery app" -> MVP scope | A vague product idea compiled into non-goals, a walking-skeleton goal, and one checkable acceptance criterion instead of an unbounded feature list. |
| [02](02-market-research/contract.toml) | "research whether this market is promising" -> research contract | A research domain pack requiring sourced, dated claims and explicit surfacing of contradictory evidence. |
| [03](03-linkedin-launch-post/contract.toml) | "write a LinkedIn launch post" -> content contract | A content domain pack plus the external-communication risk overlay, requiring explicit confirmation before anything is actually published. |
| [04](04-five-minute-constrained-task/contract.toml) | A five-minute constrained task | A tight, explicit budget (5 minutes, 3 execution iterations) on a genuinely small task -- proof the framework does not force heavyweight process onto small work. |
| [05](05-high-risk-medical-escalation/contract.toml) | A high-risk task requiring escalation | The `high_stakes_regulated` overlay firing its hard constraints (no dosage recommendation, no automatic action) and a named escalation condition routing to a licensed prescriber. |
| [06](06-contradictory-requirements/contract.toml) | Contradictory user requirements | "One paragraph" vs. "full detail on all 12 findings," logged as a blocking open question with an explicit, recorded resolution rather than silently picking one side. |
| [07](07-insufficient-evidence/contract.toml) | Insufficient evidence | A [result/evidence.json](07-insufficient-evidence/result/evidence.json) where one rubric dimension has no evidence at all; the scorer excludes it from the denominator and reports it as insufficient rather than guessing a number. |
| [08](08-partial-completion-correct/contract.toml) | Partial completion is the *correct* result | 23 of 40 reports migrated before the time budget ran out, reported as `completion_status: partial` with `omitted_work` filled in -- and a second test proves the same status would be *rejected* if it claimed `complete` instead. |
| [09](09-domain-rule-vs-style-preference/contract.toml) | A domain rule vs. a style preference | A project-layer rule pack ([project-packs/](09-domain-rule-vs-style-preference/project-packs/project-style-preference-example.json)) asking to ignore the platform's length limit, which shares a `conflict_key` with the content domain pack's format rule -- the domain rule wins deterministically by layer precedence, and the conflict is recorded, not silently dropped. |
| [10](10-unauthorized-external-action/contract.toml) | A request for an unauthorized external action | "Post this on the public forum using my account" is compiled into a contract that grants only *drafting*, requires per-post confirmation before publishing, and names a stop condition -- so the contract itself, not just good intentions, blocks the unapproved publish. |

## Why these are hard to get right with a plain prompt

A one-shot instruction to an AI ("write a LinkedIn post", "research this market") gives the model no durable place to record *what was assumed*, *what was explicitly deferred*, *what still needs confirmation*, or *what "done" means* -- so a long conversation drifts, a contradiction gets silently resolved in whatever direction the model guessed, and a partial result gets reported as if it were complete. Each contract above is the same request, but with those decisions made explicit, machine-checkable, and auditable after the fact via `groundspec audit`/`groundspec evaluate`.

## What this does not solve

None of these contracts make the underlying model more capable, verify claims it can't actually observe, or replace a qualified professional for scenario 05. They make the *task specification* auditable; whether the AI executing against it actually complies is still something a human or `groundspec evaluate` has to check afterward, using real evidence -- see [docs/architecture.md](../docs/architecture.md) for the deterministic/model-dependent boundary this relies on.
