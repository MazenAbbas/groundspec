# Clarification policy

## There is no universal rule that Guided mode must always ask questions

Clarification is required exactly when an unresolved choice is **both** materially outcome-changing **and** not safely inferable from the request -- never as a blanket "Guided mode asks N questions" ritual, and never skipped just because asking feels like friction. A request with no such choice needs zero questions, in any mode. A request with several needs them raised, even in Quick mode, within budget.

## Classify every missing piece of information, then act on the class

| Class | `scope.open_questions[].classification` value | Meaning | Action |
|---|---|---|---|
| Blocking | `blocking` | No useful progress is possible without an answer -- guessing risks building the wrong thing entirely. | Ask. Always. Before contract construction. |
| High-value | `high_value` **(requires `contract_schema_version: "0.2.0"` or later -- see below)** | Not strictly blocking, but the answer would materially change the deliverable and a wrong guess is costly to undo. | Ask, if the question budget (below) allows it. If it doesn't, record it anyway -- see "A high-value item must never silently disappear" below. It must never be quietly folded into an assumption instead. |
| Defaultable | `important_defaultable` | A safe, stated default preserves the user's likely intent. | Do not ask. Apply the default and record it in `scope.assumptions` -- see "Recording an assumption" below. |
| Optional | *(not recorded)* | Doesn't materially change the result either way. | Do not ask. Don't even mention it, and don't record it in the contract at all. |

Use the exact schema enum value in the second column when writing `scope.open_questions[].classification` -- the prose names above (blocking/high-value/defaultable/optional) are for talking about the policy, not literal field values.

**Schema version note:** `high_value` exists in `contract_schema_version: "0.2.0"` and `"0.3.0"`. If `groundspec create` on this installation still defaults to `"0.1.0"` (check with `groundspec doctor` or by looking at a freshly created contract), set `contract_schema_version` to `"0.3.0"` by hand before validating -- do not fall back to recording a high-value item as `important_defaultable` instead; that reclassification is exactly the failure mode this policy exists to prevent (see below).

For each item, ask: would the answer materially change the deliverable? Does a safe default exist? Can it be discovered from context already given? Would guessing create real risk (cost, irreversibility, safety, publication)? A `yes` to the first and a `no` to the second usually means blocking or high-value; a genuinely safe default pushes it to defaultable.

## A concrete checklist: requests that scope a product, plan, or PRD

A request to plan, scope, or write a PRD for a product or service is a specific, common, high-stakes pattern where under-asking is easy and costly. For this pattern, treat every one of the following as at least `high_value` by default (not automatically `blocking` -- but never silently downgraded to `important_defaultable` either) unless the request already answered it:

- **geographic/market scope** (one city vs. a region vs. national vs. global; one segment vs. everyone);
- **business model shape** (a standalone product vs. an integration/partnership with an existing platform or institution);
- **target persona/segment** (who specifically, not just a broad category);
- **monetization and payment model** (how it makes money, and how users pay);
- **language/localization** (which language(s) the product and its users actually operate in);
- **overall scope of the ask itself** (a research-only concept exploration vs. a specific, buildable launch plan -- these produce very different deliverables from the same one-line request).

This list exists because a real test of this Skill defaulted every one of these for a food-delivery PRD without asking or recording them as open questions at all -- see the regression fixture referenced from this repo's test suite. It is a floor, not a ceiling: a different domain will have its own near-universally-material dimensions (see `domain-guidance/*.md`), and a request that already answers several of these doesn't need to re-ask them.

## A high-value item must never silently disappear

If the question budget doesn't allow asking a `high_value` item, it still gets an entry in `scope.open_questions` with `classification: "high_value"` and `resolution_status: "defaulted"`, with `default_applied` stating exactly what was assumed instead and why. **It does not get merged into `scope.assumptions`, because `scope.assumptions` is reserved for items that were genuinely safe to default (see below) -- a high-value item is, by definition, not one of those.** State these back to the user in plain language in your response, not just buried in the contract file: "I assumed X for now because Y; the biggest open question is Z" costs one sentence and prevents the user from mistaking a forced default under budget pressure for a considered, safe choice.

## Question budgets by mode

- **Quick mode:** at most 3 questions total, and only `blocking` + the highest-value `high-value` items, ranked by expected reduction in failure risk versus the user's time cost. If more than 3 items are genuinely blocking, that's a signal the request itself needs to be narrowed before anything else -- say so, rather than asking a wall of questions.
- **Guided mode:** no fixed cap in the policy itself, but still prioritized -- ask the highest-value questions first, and stop once remaining questions would cost more user time than the expected risk reduction is worth. Group related choices into one compact question where they're related (e.g. geographic scope + business model shape can often be one question with a few options, not two separate round trips). **Hard backstop against a runaway clarification loop:** never exceed the contract's own `budget.max_clarification_questions` (set on the contract you're building, default 3 -- raise it explicitly if the task genuinely warrants more, but that's a deliberate choice recorded in the contract, not an open-ended loop). Hitting the cap with genuinely-blocking questions still unanswered means: stop, tell the user the request needs to be narrowed, and do not keep generating more questions past the limit.
- **Audit mode:** don't ask clarification questions about the artifact being audited at all -- report ambiguity as a *finding*, not a question. (You may still ask the user what remediation they want, once findings are reported.)

## Avoid both failure modes

1. **Twenty questions before doing anything.** If you're about to ask a fourth question in Quick mode, or an unbounded string of questions in Guided mode, stop and either apply a documented default or record the item as a deferred `high_value` open question (see above) and state the trade-off you're proceeding under.
2. **Silent assumptions that materially change the result.** Never quietly pick an answer to a `blocking` or `high_value` question just because asking (or even recording it) feels like friction. When in doubt about whether something is safely `important_defaultable` versus `high_value`, use the checklist above and the "Recording an assumption" test below -- and default to treating it as `high_value` when unsure, not the reverse.

## Recording an assumption

Every `important_defaultable` item that gets defaulted goes into `scope.assumptions` as `{statement, confidence, safe_default}`:
- `statement`: what was assumed, stated as a fact-shaped sentence.
- `confidence`: `low` / `medium` / `high` -- how sure you are this matches the user's actual intent.
- `safe_default`: **must be `true`** (contract schema 0.3.0+ enforces this at the schema level -- a document with `safe_default: false` will fail validation). This is deliberate: recording something as an assumption is itself a claim that defaulting it was safe. If an item is convenient to default but you cannot honestly claim it was safe, it does not belong in `scope.assumptions` at all -- it belongs in `scope.open_questions` as `high_value` (see above), not as an assumption with a dishonest safety claim attached.

State the important assumptions back to the user in plain language, not just buried in the TOML.

## High-risk actions are never behind a default

Publishing externally, spending money, deleting or overwriting something that can't be recovered, changing an account or its permissions, sending a message on the user's behalf, deploying to production, handling sensitive/personal data, **or accessing the network for any reason (including read-only research)**: these are never `defaultable`, regardless of how obvious the "right" choice seems. Either they are already covered by an explicit `routing.authorization.granted_permissions` entry the user gave up front, or they go through `routing.authorization.requires_confirmation_for` and get confirmed at the specific moment they're about to happen -- see `execution-and-verification.md`, whose "Authorization" section defines exactly what counts as an external action.
