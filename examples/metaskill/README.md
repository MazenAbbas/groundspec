# Meta-Skill examples

Four scenarios demonstrating the Groundspec Meta-Skill (`groundspec skill export`), one per required example type. **They are not all the same kind of evidence** -- read the distinction below before citing any of them.

| # | Scenario | Mode / Intent | Evidence type |
|---|----------|----------------|---------------|
| [01](01-food-delivery-ksa-university-prd/) | Guided-mode PRD for a food-delivery app for university students in Saudi Arabia, with highest-risk assumptions ranked | Guided / contract-only | **Constructed** |
| [02](02-image-dataset-validation-approaches/) | Compare 3 local-first image-dataset validation approaches under a 4-hour budget, evidence separated from inference | Guided / contract-only | **Constructed** |
| [03](03-software-csv-export/) | Add CSV export to an existing Python CLI without breaking its JSON contract | Guided / plan-and-execute | **Live dry run** |
| [04](04-audit-linkedin-launch-post/) | Audit an existing LinkedIn launch post; verify every measurable claim | Audit / audit-existing | **Constructed** |

## Constructed vs. live dry run -- what each actually proves

**Constructed** (01, 02, 04): these contracts were authored during Meta-Skill development to demonstrate the target *shape* of a compiled contract for that scenario type -- realistic assumptions, correctly classified open questions, real acceptance criteria run through the real schema validator. Each one's `session-notes.md` says so explicitly. They prove the contract format can represent these scenarios correctly. **They do not prove a model, given only the raw request, would actually produce this contract** -- that would require a live run, which these three did not have (see `docs/evaluation-methodology.md` for why the full 3-arm comparison across all four scenarios remains `PENDING`).

**Live dry run** (03): a fresh, isolated subagent with no memory of the engineering conversation was handed only the exported Skill files and the raw request, and used the real `groundspec` CLI against a real (small) fixture CLI to actually do the work -- see [`dry-run-report.md`](03-software-csv-export/dry-run-report.md) for the full report, independently re-verified command-by-command afterward, model/date/evaluator labeled per the project's evidence-labeling discipline. This is the one scenario here backed by a genuine end-to-end run rather than a constructed example -- and it's also the one that found and fixed four real gaps in the Skill's own instructions (documented in that report), which a constructed example by definition cannot do.

## What none of these four claim

None of them claim Groundspec automatically possesses real-world facts, private data, or live research it hasn't actually gathered. Where a constructed example's contract mentions a market or a claim, its `session-notes.md`/`scope.assumptions` are explicit that the number is illustrative, not verified -- see e.g. 01's "no fabricated market data" acceptance criterion, which is itself part of what a real invocation would need to satisfy, not something these notes are exempt from.
