# Evaluation methodology

## Status: harness and corpus built and tested; live model comparisons PENDING

This project has **not** run the 3-arm baseline comparison described below against a live model. Building that harness, writing 30 real scenarios, and defining the metrics as executable code is itself the v0.1.0rc1 deliverable for this phase (per the project's own scope discipline: "where model calls cannot be run reproducibly or affordably, build the harness, include fixtures, document the exact protocol, mark results pending, never invent performance improvements"). Nothing below should be read as a reported result.

## Why no live comparison ships in this release

The deterministic CLI core deliberately has no hosted-LLM dependency and makes no network calls (see `docs/architecture.md`). Running the comparison below requires an actual model (or several, across arms) to actually attempt each scenario, which is a reproducibility- and cost-sensitive step that belongs in a separate, explicitly-labeled evaluation run -- not baked into the package or its test suite, which must stay deterministic and offline.

## The corpus

[`eval/scenarios/scenarios.json`](../eval/scenarios/scenarios.json): 30 scenarios across `software`, `research`, `content`, and a cross-cutting `security` group, covering every scenario type required by this project's evaluation design: clear request, vague request, contradictory request, missing critical information, missing optional information, unsafe request, high-stakes request, short time budget, excessive requested scope, unsupported factual claims, need for external research, need for explicit authorization, task that should be refused only in part, task that should stop incomplete, adversarial prompt injection, malicious rule pack, and an attempt to override rule precedence. Coverage of every declared type is enforced by `tests/integration/test_eval_corpus.py::test_every_declared_scenario_type_is_covered_by_at_least_one_scenario`.

Each scenario has an `evaluability` field:

- **`mechanically_checkable_now`** (7 of 30): the expected behavior is already exercised by a real, passing test elsewhere in this repository (its `verified_by` field names the exact test or example, and `test_eval_corpus.py` checks that path actually exists). These are the scenarios where "does the deterministic engine do the right thing" has an actual, current answer: `sw-stop-incomplete`, `res-stop-incomplete`, `cont-unsafe-deceptive`, `cont-needs-authorization`, `sec-malicious-rule-pack`, `sec-override-precedence`.
- **`requires_model_run`** (23 of 30): answering "did the system behave correctly" requires a model to actually attempt the scenario from a raw brief, which this release does not run.

## The metrics

[`eval/metrics.py`](../eval/metrics.py) implements, as pure and unit-tested functions:

- `clarification_precision` -- of the questions asked, what fraction were actually necessary (undefined, not zero, when none were asked).
- `unnecessary_question_count` / `missed_blocking_question_count`.
- `hard_constraint_violation_rate`, `unsafe_assumption_rate`, `unsupported_claim_rate` -- each undefined (not zero) when the denominator is zero, so a scenario with nothing applicable doesn't silently look perfect.
- `scope_creep_rate` -- ratio of deliverables actually produced to deliverables the contract scoped.
- `correct_incompleteness_reporting` -- mirrors `groundspec.budget.model.forbid_silent_skip_on_expiry`'s invariant, so the same honesty check that's enforced mechanically for real contracts can also be scored across a run of scenario attempts.

These functions are ready to score real run records the moment a harness produces them; today they are exercised only with synthetic inputs in `tests/unit/test_eval_metrics.py`, which proves the arithmetic is correct, not that any model has been evaluated.

## The planned 3-arm protocol (not yet executed)

For each `requires_model_run` scenario:

1. **Arm A -- raw prompt.** Give the model the scenario's `input_brief` verbatim, nothing else.
2. **Arm B -- conventional improved prompt.** Give the model a hand-written, generic "be thorough, ask clarifying questions, cite sources" system prompt plus the brief.
3. **Arm C -- groundspec framework.** Have the model (or a human) compile the brief into a Task Contract via `groundspec create`/manual authoring, validate it, compile it via the appropriate adapter, and execute against the compiled Skill.

Score each arm's output on: goal accuracy, requirements coverage, clarification precision, unnecessary-question count, unsafe-assumption count, hard-constraint violation rate, unsupported-claim rate, acceptance-test quality, evidence completeness, scope-creep rate, user effort, token/context overhead, time to usable output, and correct-incompleteness reporting -- using the functions in `eval/metrics.py` plus blinded human scoring for the qualitative dimensions (goal accuracy, acceptance-test quality) that cannot be reduced to a formula. Blinding matters here specifically because this project's own author would otherwise be scoring their own framework's output.

## What would make a comparison result trustworthy

- Fixed model and fixed sampling parameters across all three arms for a given scenario, run more than once given LLM output variance.
- Blinded scoring: whoever scores an output should not know which arm produced it.
- Reporting failures and ties honestly, not only wins -- a scenario type where the framework's structure doesn't matter (e.g. a fully unambiguous `clear_request`) should show no meaningful difference, and that's a valid, useful finding, not something to omit.
- The `security` scenarios are not really a 3-arm comparison target at all: `sec-malicious-rule-pack` and `sec-override-precedence` are properties of the deterministic engine itself, already verified above, and don't depend on which "arm" is used.

## Test coverage of the harness itself

- `tests/unit/test_eval_metrics.py` -- every metric function, including its zero-denominator/no-questions-asked edge cases.
- `tests/integration/test_eval_corpus.py` -- corpus has ≥30 scenarios, every scenario has all required fields and a unique id, every declared scenario type is used and every used type is declared, and every `mechanically_checkable_now` scenario's `verified_by` pointer resolves to a real path in this repository.

## Do not optimize the framework only for its own fixtures

The 30 scenarios above were written to represent realistic requests across three domains, not selected or tuned after seeing how groundspec performs against them -- there is no performance number yet to have tuned against. If a future evaluation run shows the framework doing well on scenarios that resemble these but poorly on materially different ones, that's a sign the corpus needs to grow, not a reason to declare success early.
