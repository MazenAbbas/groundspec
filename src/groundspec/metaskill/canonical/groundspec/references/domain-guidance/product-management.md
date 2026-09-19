# Domain guidance: product management

Select `--domain product-management` for PRDs, product discovery, MVP definition, roadmap decisions, launch criteria, and go/no-go plans. Read the pack's actual rules/gates/questions with `groundspec pack inspect product-management` (or the guidance file bundled inside the pack itself) for the full detail -- this file is the Meta-Skill-facing summary of when and how to use it.

## When this fits, and when it doesn't

Fits: "write a PRD," "should we build X," "define the MVP for Y," "what should our launch criteria be." Does **not** fit a small implementation task whose requirements are already fully specified -- that's `software` alone; pulling in this pack's clarification checklist for a five-minute code change adds ceremony with no payoff. Combine with `research` when the PRD genuinely needs supporting evidence gathered as part of the task; combine with `software` when the request also authorizes starting implementation, not just producing the document.

## The clarification checklist

Treat each of these as at least `high_value` unless the request already answers it: problem vs. proposed solution, target user, geography, product type, business model, monetization, launch scope, stakeholder/audience, regulated context, success horizon, research authorization, and document-only vs. implementation authorization. This is the product-management-specific superset of `clarification-policy.md`'s own PRD checklist (geography, business model, persona, monetization, language, scope) -- both apply; this pack's version doesn't replace the general one.

## Evidence discipline

Market-wide data is not target-segment evidence -- a national statistic supports a claim about the whole market, not automatically your specific segment; record them as separate `status.claim_ledger` entries. A persona is researched or assumed, never presented as observed. A product threshold (conversion rate, retention target, sample size) is sourced or model-evaluated, never ambiguous -- label `MODEL_EVALUATED` unless you actually opened and read an external benchmark. A regulatory claim keeps its source's conditions (see `execution-and-verification.md`'s ZATCA VAT example).

## Completion gates this pack contributes

Six gates, fed by `evidence.json` fields you (or a human reviewer) must populate honestly -- `groundspec` cannot itself detect "this claim is unlabeled" or "this threshold is dressed up as a benchmark" from contract structure alone:

| `evidence.json` field | Effect when `true` |
|---|---|
| `pm_material_decision_silently_defaulted` | FAIL |
| `pm_unlabeled_material_claim_in_problem_statement` | INCOMPLETE |
| `pm_market_wide_data_presented_as_segment_evidence` | FAIL |
| `pm_model_threshold_presented_as_benchmark` | FAIL |
| `pm_critical_assumption_without_validation_plan` | PASS_WITH_CAVEATS |
| `pm_regulatory_claim_missing_evidence_classification` | INCOMPLETE |

Report each triggered gate's rationale verbatim in your final report, exactly like a hard-constraint failure. An honestly-disclosed critical assumption with no validation plan yet is not a defect -- it earns `PASS_WITH_CAVEATS`, not a failure.
