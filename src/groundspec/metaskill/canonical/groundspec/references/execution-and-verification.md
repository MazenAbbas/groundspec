# Execution, evidence, and verification

## The `evidence.json` shape `groundspec evaluate` reads

```json
{
  "hard_constraint_results": {"<pack-id>:<rule-id>": true},
  "dimension_scores": {"<dimension>": 0.8},
  "acceptance_criteria_results": {
    "<criterion-id>": {"met": true, "evidence_label": "SOURCE_VERIFIED"}
  },
  "authorization_violations": []
}
```

- `hard_constraint_results`: for each applicable hard constraint `groundspec audit` listed, record whether it actually held. Omit one you never checked -- don't guess `true`.
- `dimension_scores`: for each of the contract's `quality.soft_objectives`, a 0.0-1.0 score, or omit the dimension entirely if there's genuinely no basis to score it (`groundspec evaluate` reports that as insufficient evidence, not a zero).
- `acceptance_criteria_results`: for each `acceptance.criteria` entry (at minimum, every `must`-priority one), either a plain `true`/`false` (legacy shape, still supported), or -- preferred -- `{"met": bool, "evidence_label": "<label>"}` so the evaluator can check the label matches the strength the criterion's own `verification_method` actually requires (see "Evidence taxonomy" below). Missing a `must` criterion here produces `INCOMPLETE`; a weak label on a criterion whose `verification_method` demands real evidence *also* produces `INCOMPLETE`, not a silent `PASS` -- see `test_model_evaluated_label_is_inadequate_for_automated_test_criterion` in this repo's test suite for exactly this case.
- `authorization_violations`: a list of plain-language descriptions of anything done that the contract's `routing.authorization` didn't actually permit. Empty list if none. Any non-empty list forces `FAIL` regardless of everything else -- see "Authorization" below.

## Evidence taxonomy -- use the right label, every time

`status.verified_facts[].evidence_label` and `status.unverified_claims[].evidence_label` are two *different*, schema-enforced enums (contract schema 0.3.0+). This is not a style preference -- the schema will reject a document that gets this wrong.

**`status.verified_facts` may only use a label that means real, independent verification actually happened:**

| Label | Use when |
|---|---|
| `VERIFIED` | You directly executed or inspected the thing and observed the result yourself. |
| `MEASURED` | A concrete number was computed/measured (a test count, a timing, a size). |
| `SOURCE_VERIFIED` | You actually opened an external source and read the specific passage supporting the claim. **A search-result snippet, a title, an abstract, or an index entry is not enough** -- if you have not opened and read the relevant content, this is not the label, even if the source is real and even if you're confident it says what you think. |
| `USER_CONFIRMED` | The user explicitly confirmed this themselves, in this conversation. |
| `HUMAN-REVIEWED` | A human (not the executing model) reviewed and confirmed it. |

**`status.unverified_claims` takes everything else**, via its own optional `evidence_label`:

| Label | Use when |
|---|---|
| `MODEL-EVALUATED` | You (the executing model) judged this yourself -- your own assessment, not independent verification. This label -- and only this section of the contract -- is where a self-review belongs. It must never appear on a `verified_facts` entry, and the schema will reject it if you try. |
| `ASSUMPTION` | A recorded assumption from `scope.assumptions`, restated here for the report. Not evidence. |
| `RESEARCH_NEEDED` | A bounded search was performed and did not turn up a suitable source. **The claim you may make is "no suitable source was found in the searches performed during this session" -- never "no source exists."** The latter is a claim about reality that a bounded search cannot support; state the search's actual scope (what was searched, when) instead of generalizing beyond it. |
| `PROPOSED` | A suggestion or option, not a claim about the world. |
| `PENDING_EXTERNAL_VALIDATION` | Awaiting a check this session couldn't perform (e.g. a live model comparison, a human study). |
| `OUT_OF_SCOPE` | Explicitly not being addressed by this task. |

If you're unsure whether something is `VERIFIED`/`SOURCE_VERIFIED` or `MODEL-EVALUATED`, ask yourself: *did I actually open, run, or read the specific thing, or did I reason about it / see a summary of it?* The former is verified; the latter is model-evaluated, full stop, regardless of how confident the reasoning is.

## Structural checks are not semantic proof

A count, a grep, a "found N rows" -- these prove a file exists, a minimum number of rows exists, or an expected identifier is present. **They do not prove** that a threshold is actually measurable, that a cited source supports the specific claim attached to it, that reasoning is correct, that every risk is properly categorized, or that a label was applied accurately to the row it's attached to. If an acceptance criterion's `evidence_required` describes a semantic property (e.g. "every row has a valid metric and threshold"), a row-count check does not satisfy it -- you must actually inspect the rows (or a representative, disclosed sample of them) and say so, or label the criterion's result honestly as unmet/incomplete rather than passing it on a count alone.

## `groundspec evaluate` prints two separate lines -- don't conflate them

```
Verdict: insufficient_evidence
Completion state: PASS
```

`Verdict:` is the soft-objective rubric's own summary (from `quality.soft_objectives`/`dimension_scores`) -- `insufficient_evidence` there just means no soft objectives were scored (often because none were declared on the contract at all), and it is informational only. `Completion state:` is the one that actually gates PASS/FAIL/etc., per the rules below. Seeing `Verdict: insufficient_evidence` next to `Completion state: PASS` is normal and correct when a contract has no `quality.soft_objectives` -- it is not a contradiction, and it is never a reason to invent `dimension_scores` just to make the verdict line say something else. Report both lines verbatim in your final report; don't paraphrase the verdict line as if it were the gating result.

## Completion states, mechanically derived

`groundspec.metaskill.completion.derive_completion_state` computes exactly one of these -- report that value verbatim, don't paraphrase it:

- **`BLOCKED`** -- a `blocking`-classified open question is still unresolved. Nothing below matters until it's answered.
- **`FAIL`** -- any of: an explicit authorization boundary was violated (`authorization_violations` non-empty); a hard constraint that applied did not hold; a `must` acceptance criterion was checked and failed; or an unresolved residual risk is both `severity: critical` and marked (or defaulted -- see below) as affecting the deliverable's own validity.
- **`INCOMPLETE`** -- at least one `must` acceptance criterion has no recorded result, *or* has only a weak evidence label (`MODEL-EVALUATED`/`PROPOSED`/`ASSUMPTION`/`RESEARCH_NEEDED`) where its own `verification_method` demanded real evidence. This is deliberately distinct from `FAIL`: it means "not enough evidence to say," not "verified wrong."
- **`PASS_WITH_CAVEATS`** -- every gate above cleared, but `status.budget_expired` is true. Time pressure is a standing reason to distrust unexplored edge cases even when everything actually checked came back clean.
- **`PASS`** -- every gate above cleared and the budget wasn't exhausted.

Soft-objective scores (`dimension_scores`) never change this state -- they're an improvable quality signal reported alongside it, never a gate (same principle as the deterministic engine's hard-constraint-beats-soft-score rule).

**Critical risk vs. a critical *finding*:** a `status.residual_risks` entry with `severity: critical` blocks `PASS` only when it also affects the deliverable's own validity (`affects_deliverable_validity`, which **defaults to true if you don't set it** -- omitting the field is not a way to dodge the gate). If the critical item is itself a legitimate output the user asked for (e.g. "identify the highest-risk assumptions" and you correctly identified a genuinely severe one), set `affects_deliverable_validity: false` explicitly and say why in the risk's own text -- don't leave it to default, and don't use this escape hatch for a risk that actually does undermine whether the deliverable can be trusted as delivered.

There is no path to `PASS` that only requires producing confident-sounding output. If you find yourself wanting to report `PASS` without a `true`-and-adequately-evidenced result for every `must` criterion, the honest state is `INCOMPLETE`.

## Bounded revision

On `FAIL` or `INCOMPLETE`, revise and retry -- but only up to the contract's `budget.max_execution_iterations`. Once exhausted, stop and report the actual state (`INCOMPLETE`/`FAIL`/`BLOCKED`) with `status.omitted_work` describing exactly what wasn't finished. Never spend the reserved verification fraction (`budget.reserved_verification_fraction`) on additional revision attempts instead of on checking the result.

## Authorization -- what counts as "external," and what to do about it

**Network access, web search, web fetches, API calls, sending messages, publishing, purchases, and any remote mutation are all external actions.** Read-only research (a web search, fetching a page) may carry lower risk than a mutation, but it is still external and still gated the same way. There is no reading of "don't perform external actions" under which network research is exempt.

None of the following may proceed on an inferred or previously-given approval; each specific instance needs its own explicit confirmation at the moment it's about to happen, unless the user's own request already, explicitly, unambiguously covers exactly that action:

- any network access: web search, web fetch, an API call, or any other outbound request;
- publishing or posting anything externally;
- spending money or committing to a purchase;
- an irreversible or destructive action (deleting data, force-pushing, dropping a table, overwriting the only copy of something);
- changing an account, its credentials, or its permissions;
- sending a message on the user's behalf;
- deploying to production or otherwise affecting a live/shared system;
- collecting, combining, or exporting sensitive or personal data beyond what the task strictly requires.

**If the user prohibits all external actions** (however phrased -- "don't publish anything or perform any external action," "stay local," "no internet"), that prohibition covers network research too. Do not perform it. If external research would have materially improved the result, you have exactly two honest options: ask one concise permission question before proceeding (see `clarification-policy.md`), or proceed entirely locally and mark every claim that would have benefited from that research `RESEARCH_NEEDED` (see "Evidence taxonomy" above) rather than silently researching anyway or silently guessing.

**Never silently rewrite the user's authorization boundary inside the generated contract.** If the user stated a boundary in their own words, record it in `routing.authorization.boundaries` close to verbatim -- do not translate "don't do any external action" into a narrower boundary (like "don't publish") that happens to permit something convenient to do. If what you did during execution turns out not to have actually respected the stated boundary, that is an `authorization_violations` entry in `evidence.json`, reported honestly, not something to omit from the report.

For everything else not explicitly stated by the user: if the contract's `routing.authorization.granted_permissions` doesn't explicitly cover the specific action, or the action is listed in `routing.authorization.requires_confirmation_for`, stop and ask before doing it -- regardless of mode, and regardless of how much of the task is otherwise already approved.

## Reporting

The final report states, at minimum: the completion state, which acceptance criteria were verified and how (with their evidence labels), which assumptions were made and why they were judged safe to default (never an assumption that wasn't actually safe -- see `clarification-policy.md`), what remains uncertain, and any residual risk (with whether it affects this deliverable's validity). Use the evidence labels defined above -- never a stronger label than the evidence actually supports, and never `MODEL-EVALUATED`/`ASSUMPTION`/`RESEARCH_NEEDED`/`PROPOSED`/`PENDING_EXTERNAL_VALIDATION`/`OUT_OF_SCOPE` on anything reported as a verified fact. Do not persist chain-of-thought reasoning anywhere in the contract or the report; persist only the decisions, assumptions, evidence references, completion state, and the user-visible rationale for each.
