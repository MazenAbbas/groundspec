# Domain guidance: product management

Select `--domain product-management` for PRDs, product discovery, MVP definition, roadmap decisions, launch criteria, and go/no-go plans. Read this pack's actual structure with `groundspec pack inspect product-management` if you need the exact rule/gate text -- this file is about *when* and *how*, not a restatement of the pack's own machine-checkable content.

## When this pack fits, and when it doesn't

Fits: "write a PRD," "should we build X," "define the MVP for Y," "what should our launch criteria be." Does not fit a small implementation task whose requirements are already fully specified (that's `software` alone) -- pulling in `product-management`'s clarification checklist for a five-minute code change adds ceremony with no payoff, exactly the same principle `routing-and-risk.md` already states for `research`.

Combine with `research` when the PRD genuinely needs supporting evidence gathered as part of the task (see the shared example in `routing-and-risk.md`/`pack-authoring-guide.md`); combine with `software` when the request also authorizes starting implementation, not just producing the document.

## The clarification checklist (see `questions.toml` for the full, structured version)

Treat each of these as at least `high_value` per `clarification-policy.md`'s policy, unless the request already answers it: problem vs. proposed solution, target user, geography, product type, business model, monetization, launch scope, stakeholder/audience, regulated context, success horizon, research authorization, and document-only vs. implementation authorization. This list is a floor, not a ceiling -- `clarification-policy.md`'s own PRD checklist (geography, business model, persona, monetization, language, scope) already covers much of the same ground; this pack's version is the product-management-specific superset.

## Evidence discipline specific to this pack

- **Market-wide data is not target-segment evidence.** A national or industry-wide statistic supports a claim about the whole market, not automatically about your specific segment -- record them as separate `status.claim_ledger` entries (see `evidence-policy.toml`'s `market-size-vs-segment-evidence` policy). This is exactly the defect a live regression test found: a PRD that quoted a general food-delivery adoption statistic as if it specifically described university students.
- **A persona is researched or assumed, never presented as observed.** If you didn't talk to real users, say so -- `ASSUMPTION` in `scope.assumptions`, or a `status.claim_ledger` entry with an honest label, not silent authority.
- **A product threshold (conversion rate, retention target, sample size) is sourced or model-evaluated, never ambiguous.** Label it `MODEL_EVALUATED` unless you actually opened and read an external benchmark, and say so inline in the deliverable the first time the number appears -- readers should never have to open the contract to tell a real benchmark from a suggested starting point.
- **A regulatory claim keeps its conditions.** See `execution-and-verification.md`'s worked ZATCA VAT example -- the same discipline applies to any product-management claim that touches licensing, tax, labor classification, or similar regulated territory.

## Completion-gate behavior specific to this pack (see `completion-gates.toml`)

Six gates exist, fed by `evidence.json` fields this Skill (or a human reviewer) must populate honestly -- the CLI cannot itself detect "this claim is unlabeled" or "this threshold is dressed up as a benchmark" from contract structure alone:

- `pm_material_decision_silently_defaulted` -- FAILs the run. A materially outcome-changing decision defaulted without disclosure is a violated instruction, not a quality issue.
- `pm_unlabeled_material_claim_in_problem_statement` -- downgrades to INCOMPLETE.
- `pm_market_wide_data_presented_as_segment_evidence` -- FAILs the run (a misrepresentation of the evidence's actual scope).
- `pm_model_threshold_presented_as_benchmark` -- FAILs the run (mislabeling).
- `pm_critical_assumption_without_validation_plan` -- downgrades to PASS_WITH_CAVEATS (a disclosed gap in exploratory work is not a defect).
- `pm_regulatory_claim_missing_evidence_classification` -- downgrades to INCOMPLETE.

Report each triggered gate's `rationale` verbatim in your final report, exactly like a hard-constraint failure -- see `execution-and-verification.md`'s completion-state reporting discipline.

## What this pack does not do

It does not conduct user research, provide legal review, or substitute for business judgment about whether to actually build something -- it structurally requires that the *absence* of those things be disclosed, not that they be performed. A PRD that honestly says "persona is assumed, not researched; legal review of the regulated claim is still required" and discloses its critical risks can still reach `PASS_WITH_CAVEATS` -- that is the intended, honest outcome for exploratory product work, not a failure of the pack.
