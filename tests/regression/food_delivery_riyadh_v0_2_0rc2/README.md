# Regression: Riyadh university-student food-delivery PRD (v0.2.0rc2)

## Origin

A second independent user test invoked the Meta-Skill:

> Create a PRD for a university-student food-delivery application, in one city near one university.

The run produced a structurally strong PRD and reported `Completion state: PASS`. Independent review found the unconditional `PASS` too generous. Observed defects:

1. The problem statement asserted that university students have narrower budgets and more rigid schedules, and that major platforms do not optimize for these needs -- material claims with no evidence label and no evidence record of any kind.
2. The user asked for "one city near one university" but did not name the city; the Skill silently selected Riyadh and King Saud University and wrote them into the PRD's scope as a confirmed decision, not an illustrative anchor -- a materially outcome-changing choice (market size, regulation, operations, merchant supply, validation design), not a harmless presentation default.
3. The PRD generalized Saudi ZATCA's e-marketplace VAT deemed-supplier treatment into an unconditional rule, dropping the actual conditions (supplier residency/VAT-registration status, among others).
4. A legal/transport claim about delivery riders was supported only by secondary reporting but treated as a binding, verified regulatory fact -- the corresponding official regulatory source was never inspected.
5. The evidence appendix named sources without consistently preserving a direct URL, title, publication/access date, or supporting excerpt.
6. Market reports and news pages were treated as equivalent to official sources -- "source verified" meant only "a page was opened," which a reader could reasonably mistake for "the claim is authoritative."
7. Model-generated thresholds (e.g. a suggested conversion target) were presented in a way that could be mistaken for a sourced industry benchmark.

The honest completion state should have been `PASS_WITH_CAVEATS`, not unconditional `PASS`.

## What's fixed, and where the fix actually lives

Contract schema `0.4.0` adds `status.claim_ledger` and its `claim_record` shape (`src/groundspec/schema/task_contract.v0_4_0.schema.json`): a structured, provenance-carrying evidence record with a 7-label taxonomy (`MEASURED`/`PRIMARY_SOURCE_VERIFIED`/`SECONDARY_SOURCE_SUPPORTED`/`USER_CONFIRMED`/`MODEL_EVALUATED`/`ASSUMPTION`/`RESEARCH_NEEDED`), schema-enforced citation completeness for the two source-backed labels, and a schema-enforced `authority_level` that makes "secondary source presented as primary/official" a validation error, not a style mistake. `groundspec.metaskill.completion` gained `has_unmapped_material_claims` (a material claim with no ledger entry forces `INCOMPLETE`) and `claim_ledger_has_disclosed_material_limitations` (a material claim resting on secondary support, model judgment, an assumption, or a research gap forces `PASS_WITH_CAVEATS`, never a bare `PASS`). The Meta-Skill content (`execution-and-verification.md`'s "claim ledger" section, `clarification-policy.md`'s "illustrative anchor is not a decision" section, `domain-guidance/research-and-analysis.md`'s authority-aware-evidence note) documents exactly how and when to use all of this.

## Fixtures in this directory

- `contract_defective.toml` -- schema `0.3.0` (pre-claim-ledger), reproducing the exact pattern from the live test: Riyadh/King Saud University baked directly into `brief.raw_user_brief`/`brief.goal` with zero corresponding `scope.open_questions` entry; a conditional ZATCA rule generalized and recorded as a flatly `VERIFIED` fact backed only by "general knowledge," not a real source; and the student-budget/competitor claims present only as PRD prose, with no evidence record anywhere in the contract (0.3.0 has no field that could hold one even if someone tried).
- `contract_corrected.toml` -- schema `0.4.0`. The pilot city/campus is recorded as a `high_value` open question, `resolution_status: "answered"` -- Riyadh/King Saud University end up in the same place, but *confirmed*, not assumed. `status.claim_ledger` has five entries: the student-budget claim and the competitor-gap claim as `RESEARCH_NEEDED`; the ZATCA VAT claim as `SECONDARY_SOURCE_SUPPORTED` with full citation, preserved conditions in `scope_and_qualifiers`, and a `limitations` string stating official confirmation is still required; the rider-classification claim as `SECONDARY_SOURCE_SUPPORTED` similarly; and a suggested conversion-target threshold as `MODEL_EVALUATED`. One `severity: critical` residual risk (both regulatory claims resting on secondary sources only) is explicitly marked `affects_deliverable_validity: false` with a stated reason -- a disclosed limitation of a first-draft PRD, not a defect in the analysis performed.
- `evidence_defective.json` -- `unmapped_material_claims` lists the student-budget and competitor-gap claims (no ledger entry exists for either under 0.3.0).
- `evidence_corrected.json` -- `unmapped_material_claims` empty; all four acceptance criteria adequately evidenced for their declared verification methods.

## What the paired test (`tests/integration/test_regression_food_delivery_riyadh.py`) actually checks

Deterministically, against real code and real fixture structure, not by searching for one preferred sentence:

1. An unsupported budget/schedule claim and a competitor-capability claim without evidence: `evidence_defective.json`'s `unmapped_material_claims` is non-empty and running it through `derive_completion_state` never yields `PASS`/`PASS_WITH_CAVEATS` -- it yields `INCOMPLETE`.
2. Riyadh silently promoted from illustrative option to confirmed scope: the defective contract's brief text contains "Riyadh"/"King Saud University" with zero matching `scope.open_questions` entries; the corrected contract's `scope.open_questions` contains a `high_value` item covering the city/campus decision, `resolution_status: "answered"`.
3. A conditional ZATCA rule generalized: the defective contract's `verified_facts` entry states the rule with no qualifying language and cites no real source; the corrected contract's matching `claim_ledger` entry's `scope_and_qualifiers` preserves the actual conditions, and is labeled `SECONDARY_SOURCE_SUPPORTED` (not `VERIFIED`/`PRIMARY_SOURCE_VERIFIED`).
4. A secondary regulatory news source treated as primary official confirmation: mutating the corrected contract's rider-classification claim to `authority_level: "primary_official"` fails schema validation -- structurally impossible, not just discouraged in prose.
5. Missing direct URLs or supporting excerpts: removing `source_url` (or `excerpt_or_locator`) from either `SECONDARY_SOURCE_SUPPORTED` entry fails schema validation.
6. Model-generated thresholds presented as sourced benchmarks: the conversion-target claim is labeled `MODEL_EVALUATED`, and attempting to relabel it `SECONDARY_SOURCE_SUPPORTED` without adding a real citation fails schema validation.
7. Unconditional `PASS` despite those defects: `evidence_defective.json` against `contract_defective.toml`'s pipeline never reaches `PASS`; `evidence_corrected.json` against `contract_corrected.toml` reaches exactly `PASS_WITH_CAVEATS` (never a bare `PASS`, because the ledger's disclosed secondary-sourced and research-needed material claims are real, honest limitations, not hidden ones) -- and removing all weak-labeled material claims from the ledger (keeping only the two strong ones) while re-running the same otherwise-clean evidence flips the result to a bare `PASS`, proving the gate is load-bearing in both directions.
