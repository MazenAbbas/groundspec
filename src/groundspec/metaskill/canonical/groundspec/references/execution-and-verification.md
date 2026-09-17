# Execution, evidence, and verification

## The `evidence.json` shape `groundspec evaluate` reads

```json
{
  "hard_constraint_results": {"<pack-id>:<rule-id>": true},
  "dimension_scores": {"<dimension>": 0.8},
  "acceptance_criteria_results": {"<criterion-id>": true}
}
```

- `hard_constraint_results`: for each applicable hard constraint `groundspec audit` listed, record whether it actually held. Omit one you never checked -- don't guess `true`.
- `dimension_scores`: for each of the contract's `quality.soft_objectives`, a 0.0-1.0 score, or omit the dimension entirely if there's genuinely no basis to score it (`groundspec evaluate` reports that as insufficient evidence, not a zero).
- `acceptance_criteria_results`: for each `acceptance.criteria` entry (at minimum, every `must`-priority one), a literal `true`/`false` for whether it was actually verified. Missing a `must` criterion here is what produces `INCOMPLETE` below -- it is not the same as `false`.

## Completion states, mechanically derived

`groundspec.metaskill.completion.derive_completion_state` computes exactly one of these from the inputs above -- report that value verbatim, don't paraphrase it:

- **`BLOCKED`** -- a `blocking`-classified open question is still unresolved. Nothing below matters until it's answered.
- **`FAIL`** -- a hard constraint that applied did not hold, or a `must` acceptance criterion was checked and failed.
- **`INCOMPLETE`** -- at least one `must` acceptance criterion has no recorded result. This is deliberately distinct from `FAIL`: it means "not enough evidence to say," not "verified wrong."
- **`PASS_WITH_CAVEATS`** -- every `must` criterion passed and every applicable hard constraint held, but `status.budget_expired` is true. Time pressure is a standing reason to distrust unexplored edge cases even when everything actually checked came back clean.
- **`PASS`** -- every `must` criterion passed, every applicable hard constraint held, no blocking questions remain, and the budget wasn't exhausted.

Soft-objective scores (`dimension_scores`) never change this state -- they're an improvable quality signal reported alongside it, never a gate (same principle as the deterministic engine's hard-constraint-beats-soft-score rule).

There is no path to `PASS` that only requires producing confident-sounding output. If you find yourself wanting to report `PASS` without a `true` result recorded for every `must` criterion, the honest state is `INCOMPLETE`.

## Bounded revision

On `FAIL` or `INCOMPLETE`, revise and retry -- but only up to the contract's `budget.max_execution_iterations`. Once exhausted, stop and report the actual state (`INCOMPLETE`/`FAIL`/`BLOCKED`) with `status.omitted_work` describing exactly what wasn't finished. Never spend the reserved verification fraction (`budget.reserved_verification_fraction`) on additional revision attempts instead of on checking the result.

## Authorization gates -- stop and ask, every time, per action

None of the following may proceed on an inferred or previously-given approval; each specific instance needs its own explicit confirmation at the moment it's about to happen:

- publishing or posting anything externally;
- spending money or committing to a purchase;
- an irreversible or destructive action (deleting data, force-pushing, dropping a table, overwriting the only copy of something);
- changing an account, its credentials, or its permissions;
- sending a message on the user's behalf;
- deploying to production or otherwise affecting a live/shared system;
- collecting, combining, or exporting sensitive or personal data beyond what the task strictly requires.

If the contract's `routing.authorization.granted_permissions` doesn't explicitly cover the specific action, or the action is listed in `routing.authorization.requires_confirmation_for`, stop and ask before doing it -- regardless of mode, and regardless of how much of the task is otherwise already approved.

## Reporting

The final report states, at minimum: the completion state, which acceptance criteria were verified and how, which assumptions were made and why they were judged safe, what remains uncertain, and any residual risk. Use the evidence labels the compiled contract itself defines (VERIFIED, MEASURED, MODEL-EVALUATED, HUMAN-REVIEWED, PROPOSED, PENDING_EXTERNAL_VALIDATION, OUT_OF_SCOPE) -- never a stronger label than the evidence actually supports. Do not persist chain-of-thought reasoning anywhere in the contract or the report; persist only the decisions, assumptions, evidence references, completion state, and the user-visible rationale for each.
