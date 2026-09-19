# Execution, evidence, and verification

## Exact field names for `status.verified_facts` / `status.unverified_claims` / `status.residual_risks`

Get these exactly right the first time -- two independent forward tests of this Skill both had their first `groundspec validate` fail on these field names, since the shapes weren't spelled out here before (only in the raw JSON Schema, `task_contract.v0_3_0.schema.json`, which is a fallback, not the primary reference):

```toml
[[status.verified_facts]]
statement = "..."
evidence_label = "VERIFIED"   # or MEASURED / SOURCE_VERIFIED / USER_CONFIRMED / HUMAN-REVIEWED
source = "..."                # optional

[[status.unverified_claims]]
statement = "..."
reason = "..."                 # required -- not evidence_label alone
evidence_label = "ASSUMPTION"  # optional; or MODEL-EVALUATED / RESEARCH_NEEDED / PROPOSED / PENDING_EXTERNAL_VALIDATION / OUT_OF_SCOPE

[[status.residual_risks]]
risk = "..."                    # NOT "description"
severity = "critical"           # low / medium / high / critical
mitigation = "..."               # optional
affects_deliverable_validity = false  # optional, defaults true -- see below

[[status.claim_ledger]]          # new in contract schema 0.4.0 -- see "The claim ledger" below
claim_id = "..."
claim = "..."
evidence_label = "RESEARCH_NEEDED"  # MEASURED / PRIMARY_SOURCE_VERIFIED / SECONDARY_SOURCE_SUPPORTED /
                                     # USER_CONFIRMED / MODEL_EVALUATED / ASSUMPTION / RESEARCH_NEEDED
evaluator_type = "ai_model"          # deterministic_tool / human_reviewer / ai_model / user
scope_and_qualifiers = "..."         # required; conditions/exceptions preserved, or "none" if truly unconditional
affects = ["market_size"]            # optional; which material dimension(s) this claim affects
```

If you'd rather avoid the TOML array-of-tables ordering footgun below entirely, inline-table array syntax is equally valid and schema-identical: `status.verified_facts = [{statement = "...", evidence_label = "VERIFIED"}]`. Both forms produce the same JSON; use whichever is easier for your editing tool to get right.

## The `evidence.json` shape `groundspec evaluate` reads

```json
{
  "hard_constraint_results": {"<pack-id>:<rule-id>": true},
  "dimension_scores": {"<dimension>": 0.8},
  "acceptance_criteria_results": {
    "<criterion-id>": {"met": true, "evidence_label": "SOURCE_VERIFIED"}
  },
  "authorization_violations": [],
  "unmapped_material_claims": [],
  "pm_material_decision_silently_defaulted": false,
  "ds_unresolved_leakage_risk": false
}
```

- `hard_constraint_results`: for each applicable hard constraint `groundspec audit` listed, record whether it actually held. Omit one you never checked -- don't guess `true`.
- `dimension_scores`: for each of the contract's `quality.soft_objectives`, a 0.0-1.0 score, or omit the dimension entirely if there's genuinely no basis to score it (`groundspec evaluate` reports that as insufficient evidence, not a zero).
- `acceptance_criteria_results`: for each `acceptance.criteria` entry (at minimum, every `must`-priority one), either a plain `true`/`false` (legacy shape, still supported), or -- preferred -- `{"met": bool, "evidence_label": "<label>"}` so the evaluator can check the label matches the strength the criterion's own `verification_method` actually requires (see "Evidence taxonomy" below). Missing a `must` criterion here produces `INCOMPLETE`.
  **Which verification methods demand real evidence, and which accept a self-review:** `automated_test`, `reproducible_command`, `static_analysis`, and `external_reference_check` all demand real, independent evidence -- a weak label (`MODEL-EVALUATED`/`PROPOSED`/`ASSUMPTION`/`RESEARCH_NEEDED`) on one of these produces `INCOMPLETE`, not a silent `PASS` (see `test_model_evaluated_label_is_inadequate_for_automated_test_criterion`). `manual_inspection` and `user_confirmation`, by contrast, are *defined* as judgment-based -- a `MODEL-EVALUATED` label is the expected, adequate evidence for a `manual_inspection` criterion (it is what "the executor inspected and judged it" actually means), and this is treated as adequate, not weak. Two independent forward tests both had to infer this distinction because it wasn't spelled out before; do not assume `manual_inspection` demands the same evidence strength as `automated_test`.
- `authorization_violations`: a list of plain-language descriptions of anything done that the contract's `routing.authorization` didn't actually permit. Empty list if none. Any non-empty list forces `FAIL` regardless of everything else -- see "Authorization" below.
- `unmapped_material_claims` (new): a list of plain-language descriptions of material factual claims that appear in the deliverable but have **no** corresponding entry in `status.claim_ledger` -- see "The claim ledger" below. Empty list if every material claim you made has a ledger entry. Any non-empty list forces `INCOMPLETE` -- you don't get to assert a market-size number, a competitor-capability claim, or a regulatory conclusion with no evidence record behind it at all and still call the result done, even provisionally.
- **Domain Pack completion-gate fields** (schema 0.4.0+ with the Domain Pack SDK): if `routing.domain_packs` selects a pack that declares its own `completion-gates.toml` (currently `product-management` and `data-science-ml`), populate the boolean fields it documents -- e.g. `pm_material_decision_silently_defaulted`, `ds_unresolved_leakage_risk` -- honestly. `groundspec evaluate` reads them, applies any triggered gate on top of the core completion state (a pack gate can only make the result *more* severe, never less), and prints each triggered gate's rationale. Find the exact field names for a given pack with `groundspec pack inspect <pack-id>` or that pack's own bundled guidance file -- never guess a field name; an unrecognized key is silently ignored (it evaluates to "not present," i.e. `false`-like), which is why getting the name exactly right matters for the gate to actually mean anything.

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

## The claim ledger -- provenance for material factual claims (contract schema 0.4.0+)

`status.verified_facts`/`status.unverified_claims` (above) are short status-report lines. `status.claim_ledger` is different: it is the citable, reproducible evidence record behind a **material factual claim** -- one that affects the problem definition, market size, legal/regulatory feasibility, financial feasibility, risk severity, product scope, an acceptance threshold, or a go/no-go recommendation. A live test produced a PRD whose problem statement ("university students have narrower budgets and more rigid schedules than other segments, and major platforms don't optimize for this") and a market-size/competitor-capability claim were asserted with no evidence record of any kind, and reported `PASS` anyway -- this is what closes that gap.

**When a claim is material, it needs a `status.claim_ledger` entry before you report an unconditional `PASS`.** Purely stylistic or connective prose does not; don't try to classify every sentence. If you assert something that would change the reader's problem definition, their sense of market size, whether the plan is legally/financially feasible, how severe a risk is, what's in scope, an acceptance threshold, or a go/no-go call -- that assertion needs a ledger entry. A material claim with no entry goes into `evidence.json`'s `unmapped_material_claims` and forces `INCOMPLETE` (see above); no need to hunt for the last unlabeled adjective, but don't skip an entry just because writing it is friction.

```toml
[[status.claim_ledger]]
claim_id = "student-budget-narrower"
claim = "University students in the target market have narrower discretionary budgets than the general population"
evidence_label = "RESEARCH_NEEDED"      # see the label table below
evaluator_type = "ai_model"
scope_and_qualifiers = "Directional claim only; no specific figures asserted. Not verified against local survey/spending data."
affects = ["problem_definition"]
# source_url / source_title / access_date / excerpt_or_locator / source_type / authority_level /
# limitations are all optional here -- they become REQUIRED (schema-enforced) only for
# PRIMARY_SOURCE_VERIFIED / SECONDARY_SOURCE_SUPPORTED, see below.
```

**The seven claim-ledger evidence labels** (a different, more granular enum than `verified_facts`/`unverified_claims` above -- this one carries full source provenance):

| Label | Use when | Citation required? |
|---|---|---|
| `MEASURED` | A concrete local/deterministic measurement (a count, a size, a timing). | No -- `authority_level` is schema-forced to `not_applicable`. |
| `PRIMARY_SOURCE_VERIFIED` | You actually opened an official/primary source (government body, statute, official regulation or guidance, primary document) and it directly supports this exact claim, including its qualifiers. | Yes -- `source_url`, `source_title`, `access_date`, `excerpt_or_locator`, `source_type` are all schema-required, and `authority_level` is schema-forced to `primary_official`. |
| `SECONDARY_SOURCE_SUPPORTED` | You actually opened a professional advisory article, reputable news report, market report, or academic paper and it supports the claim, offered as context/provisional support only -- never as final legal/regulatory/financial confirmation. | Yes -- same four citation fields required, and `authority_level` is schema-forced to `secondary_professional` or `secondary_general` (never `primary_official` -- this is what makes "secondary source presented as authoritative" a schema violation, not a style note). If `affects` includes `legal_or_regulatory_feasibility`, `limitations` is also schema-required and must actually say official confirmation is still needed. |
| `USER_CONFIRMED` | The user explicitly confirmed this themselves. | No. |
| `MODEL_EVALUATED` | Your own judgment/self-review. Never promotable to a stronger label by restating it more confidently. | No -- `authority_level` forced to `not_applicable`. |
| `ASSUMPTION` | A recorded, stated assumption -- not evidence. | No. |
| `RESEARCH_NEEDED` | A bounded search found no suitable source. State the search's actual scope; never that no source exists. | No. |

**A search-result snippet, an index page, an inaccessible paper, or a report you did not open is never `PRIMARY_SOURCE_VERIFIED` or `SECONDARY_SOURCE_SUPPORTED`** -- if you have not opened and read the specific passage, the honest label is `RESEARCH_NEEDED` or `MODEL_EVALUATED`, exactly as for `SOURCE_VERIFIED` above.

**For legal, regulatory, tax, financial, medical, safety, and compliance claims specifically:** prefer the responsible government body, regulator, statute, official regulation, or official guidance (`PRIMARY_SOURCE_VERIFIED`). A professional advisory article or reputable news report may be recorded as `SECONDARY_SOURCE_SUPPORTED`, with its lower authority disclosed via `authority_level` and its limitation stated explicitly -- do not reject secondary sources outright; their role is provisional context, not final confirmation, and the schema requires you to say so via `limitations` rather than silently upgrade them. Never invent a legal conclusion by generalizing from an adjacent regulation you didn't actually check.

**Conditional claims must keep their conditions.** If a source states a rule with exceptions, jurisdiction limits, dates, thresholds, or supplier/scope categories, `scope_and_qualifiers` must actually restate them -- not "none" when the source clearly says "unless X." A real example: Saudi ZATCA's e-marketplace VAT deemed-supplier treatment is conditional (it turns on the underlying supplier's residency and VAT-registration status, among other things). "All food-delivery marketplaces are deemed suppliers and must issue every invoice" rewrites a conditional rule as a universal one and is unacceptable, even as a `MODEL_EVALUATED` claim. "Deemed-supplier treatment may apply to this marketplace model in certain supplier scenarios (e.g. a resident, non-VAT-registered supplier); no primary ZATCA document was inspected, so professional/official confirmation for this exact operating model is still needed" is the acceptable shape -- qualifiers preserved, authority level disclosed, limitation stated. The schema cannot detect a generalized conditional rule from prose alone (`scope_and_qualifiers` is a free-text field); this is a discipline this Skill must apply itself, not something `groundspec validate` can catch for you.

**Model-generated thresholds are not sourced benchmarks.** A suggested conversion target, retention target, survey threshold, or sample size you derived yourself is `MODEL_EVALUATED` (or `ASSUMPTION` if it's a stated starting point), never `SECONDARY_SOURCE_SUPPORTED`, even if it resembles a number you've seen in industry contexts. Present it in the deliverable in a way that cannot be mistaken for a sourced figure (e.g. "target -- not benchmarked against an external source").

**Direct citations, not citations to a search:** for any `PRIMARY_SOURCE_VERIFIED`/`SECONDARY_SOURCE_SUPPORTED` claim, the deliverable itself should give the reader a usable citation: title, publisher, direct URL, access date, evidence class, and the relevant excerpt or section/page locator -- never a citation to a search-results page. Never put secrets, tokens, private URLs, local absolute paths, or personal browsing history into `source_url` or anywhere else in the ledger.

**Presentation:** when you write the actual deliverable (not just the contract), visually distinguish primary-official evidence, secondary support, user decisions, assumptions, model-evaluated recommendations, and research-needed items from each other -- a reader should never have to open the contract to tell a sourced fact from a model guess.

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
- **`INCOMPLETE`** -- at least one `must` acceptance criterion has no recorded result, *or* has only a weak evidence label (`MODEL-EVALUATED`/`PROPOSED`/`ASSUMPTION`/`RESEARCH_NEEDED`) where its own `verification_method` demanded real evidence, *or* `evidence.json`'s `unmapped_material_claims` is non-empty (a material factual claim with no `status.claim_ledger` entry at all -- see "The claim ledger" above). This is deliberately distinct from `FAIL`: it means "not enough evidence to say," not "verified wrong."
- **`PASS_WITH_CAVEATS`** -- every gate above cleared, but at least one of: `status.budget_expired` is true; at least one `high_value` open question was resolved by defaulting rather than by the user actually answering it; or at least one material claim in `status.claim_ledger` rests on disclosed secondary support, model judgment, a stated assumption, or a bounded research gap rather than strong evidence (`MEASURED`/`PRIMARY_SOURCE_VERIFIED`/`USER_CONFIRMED`) -- see `claim_ledger_has_disclosed_material_limitations`. Time pressure, an unconfirmed material judgment call, and an under-evidenced material claim are all standing reasons to distrust whether the deliverable fully matches actual intent, even when everything you *did* check came back clean. Note this applies even to items you disclosed responsibly (a stated default, a properly-labeled and properly-qualified secondary source) -- doing that is still the correct thing to do (see `clarification-policy.md` and "The claim ledger" above), it just means the honest completion state is "passed, with caveats," not a bare "passed."
- **`PASS`** -- every gate above cleared, the budget wasn't exhausted, and every material claim is backed by strong evidence with no disclosed limitation.

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

The final report states, at minimum: the completion state, which acceptance criteria were verified and how (with their evidence labels), which assumptions were made and why they were judged safe to default (never an assumption that wasn't actually safe -- see `clarification-policy.md`), what remains uncertain, any residual risk (with whether it affects this deliverable's validity), and every material claim's ledger entry (with its evidence label and authority level, where applicable). Use the evidence labels defined above -- never a stronger label than the evidence actually supports, and never `MODEL-EVALUATED`/`ASSUMPTION`/`RESEARCH_NEEDED`/`PROPOSED`/`PENDING_EXTERNAL_VALIDATION`/`OUT_OF_SCOPE` on anything reported as a verified fact, and never `PRIMARY_SOURCE_VERIFIED`/`SECONDARY_SOURCE_SUPPORTED` on a claim-ledger entry whose source you didn't actually open and read. Do not persist chain-of-thought reasoning anywhere in the contract or the report; persist only the decisions, assumptions, evidence references, completion state, and the user-visible rationale for each.
