# Clarification policy

## Classify every missing piece of information, then act on the class

| Class | Meaning | Action |
|---|---|---|
| `blocking` | No useful progress is possible without an answer -- guessing risks building the wrong thing entirely. | Ask. Always. Before contract construction. |
| `high-value` | Not strictly blocking, but the answer would materially change the deliverable and a wrong guess is costly to undo. | Ask, if the question budget (below) allows it. |
| `defaultable` | A safe, stated default preserves the user's likely intent. | Do not ask. Apply the default and record it in `scope.assumptions` with its confidence and why it's safe. |
| `optional` | Doesn't materially change the result either way. | Do not ask. Don't even mention it unless the user asks. |

For each item, ask: would the answer materially change the deliverable? Does a safe default exist? Can it be discovered from context already given? Would guessing create real risk (cost, irreversibility, safety, publication)? A `yes` to the first and a `no` to the second usually means `blocking` or `high-value`; a safe default pushes it to `defaultable`.

## Question budgets by mode

- **Quick mode:** at most 3 questions total, and only `blocking` + the highest-value `high-value` items, ranked by expected reduction in failure risk versus the user's time cost. If more than 3 items are genuinely blocking, that's a signal the request itself needs to be narrowed before anything else -- say so, rather than asking a wall of questions.
- **Guided mode:** no fixed cap, but still prioritized -- ask the highest-value questions first, and stop once remaining questions would cost more user time than the expected risk reduction is worth. Group related questions together instead of a back-and-forth per field.
- **Audit mode:** don't ask clarification questions about the artifact being audited at all -- report ambiguity as a *finding*, not a question. (You may still ask the user what remediation they want, once findings are reported.)

## Avoid both failure modes

1. **Twenty questions before doing anything.** If you're about to ask a fourth question in Quick mode, or an unbounded string of questions in Guided mode, stop and either apply a documented default or state the trade-off you're proceeding under.
2. **Silent assumptions that materially change the result.** Never quietly pick an answer to a `blocking` question just because asking feels like friction. When in doubt about whether something is `blocking` or `defaultable`, treat it as the more cautious of the two only if a wrong guess would be expensive or hard to reverse -- otherwise default it and move on.

## Recording every assumption

Every `defaultable` item that gets defaulted, and every `optional` item worth a one-line note, goes into `scope.assumptions` as `{statement, confidence, safe_default}`:
- `statement`: what was assumed, stated as a fact-shaped sentence.
- `confidence`: `low` / `medium` / `high` -- how sure you are this matches the user's actual intent.
- `safe_default`: `true` only if acting on it without confirmation preserves intent at acceptable risk; if an assumption is convenient but risky, set this `false` and treat the item as `high-value` (ask) instead of quietly defaulting it.

State the important assumptions back to the user in plain language, not just buried in the TOML -- "I'm assuming X because Y; tell me if that's wrong" costs one sentence and prevents silent drift.

## High-risk actions are never behind a default

Publishing externally, spending money, deleting or overwriting something that can't be recovered, changing an account or its permissions, sending a message on the user's behalf, deploying to production, or handling sensitive/personal data: these are never `defaultable`, regardless of how obvious the "right" choice seems. Either they are already covered by an explicit `routing.authorization.granted_permissions` entry the user gave up front, or they go through `routing.authorization.requires_confirmation_for` and get confirmed at the specific moment they're about to happen -- see `execution-and-verification.md`.
