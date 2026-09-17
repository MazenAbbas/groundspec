# Regression: v0.2.0rc1 Guided-mode food-delivery PRD

## Origin

An independent user test of `v0.2.0rc1` invoked the Meta-Skill in Guided mode:

> Use Groundspec in Guided mode to create a PRD for a Saudi university-student food-delivery application. Clearly separate verified facts, assumptions, and items requiring external research. Do not publish anything or perform any external action.

The run: asked zero clarification questions while silently defaulting several materially outcome-changing product decisions (pilot city, standalone-vs-partnership, persona, payments, language, monetization); made ten web searches despite the explicit "do not perform any external action" instruction; recorded a self-review as a verified fact for a criterion that admittedly hadn't been checked (the underlying source "had not been read in full"); asserted "no source exists" from a single bounded search; used row/label counts as proof of semantic correctness; and reported `Completion state: PASS` despite an unresolved critical risk, model-self-evaluated criteria, and the authorization violation. Full defect list: this repo's PR history / `CHANGELOG.md`'s `[0.2.0rc2]` entry.

## What's fixed, and where the fix actually lives

None of this is fixable by only rewording a prompt more emphatically -- see the corresponding commits: contract schema `0.3.0` (evidence taxonomy split, `scope.assumptions.safe_default` now `const: true`, `residual_risk.affects_deliverable_validity`), `groundspec.metaskill.completion` (authorization/critical-risk gating, evidence-adequacy checking), and the Meta-Skill content (`execution-and-verification.md`, `clarification-policy.md`, `domain-guidance/research-and-analysis.md`).

## Fixtures in this directory

- `contract_defective.toml` -- schema `0.2.0`, reproduces the *exact* self-review-as-verified-fact pattern from the live test. Valid under `0.2.0` (the hole that existed); the paired test proves the identical document is rejected under `0.3.0`.
- `contract_corrected.toml` -- schema `0.3.0`, a plausible corrected run: one compact clarification question covering the most material choices (scope/business-model/research-authorization), the remaining high-value items explicitly recorded as deferred open questions (never silently folded into assumptions), the user's authorization boundary recorded verbatim, a `RESEARCH_NEEDED`-labeled claim with correctly bounded language ("could not be checked" — not "no source exists"), and one `severity: critical` residual risk explicitly marked `affects_deliverable_validity: false` with a stated reason (a deliberate, documented instance of "a critical finding the exploration was asked to produce," not a defect).
- `evidence_defective.json` -- evaluate-time evidence reproducing the observed failure: an authorization violation (the ten searches) and two 'must' criteria whose `automated_test` verification method was "satisfied" only by `MODEL-EVALUATED` self-review.
- `evidence_corrected.json` -- the same criteria, adequately evidenced, no authorization violation.

## What the paired test (`tests/integration/test_regression_food_delivery_guided_mode.py`) actually checks

Deterministically, against real code, not by searching for a sentence:

1. `contract_defective.toml` validates under schema `0.2.0` but the identical document (schema bumped to `0.3.0`) fails validation on exactly the `MODEL-EVALUATED`-in-`verified_facts` field -- the self-review-as-fact pattern is now structurally impossible, not just discouraged.
2. `contract_corrected.toml` validates cleanly under `0.3.0` and its `scope.open_questions` actually cover the required checklist (scope, business model, persona, payments, language, monetization) with the right classifications -- not just present, but classified `blocking`/`high_value` as appropriate, and none silently missing.
3. `routing.authorization.boundaries` contains the user's stated prohibition, unedited.
4. `evidence_defective.json` run through `derive_completion_state` produces `FAIL` (authorization violation) -- never `PASS` or `PASS_WITH_CAVEATS`.
5. `evidence_corrected.json` run through the same path, against the same contract, produces `PASS` or `PASS_WITH_CAVEATS` -- proving the hardened gates don't just fail everything unconditionally, and specifically that the critical-but-not-validity-affecting residual risk does not block completion.
6. Reversing `contract_corrected.toml`'s residual risk to the default (omit `affects_deliverable_validity`, i.e. let it default to `true`) flips the same evidence from passing to `FAIL` -- proving the critical-risk gate actually engages when it's supposed to.
7. The `RESEARCH_NEEDED` claim's `reason` text is checked for the bounded framing (does not claim non-existence), and structurally, that no `unverified_claims` entry's `evidence_label` ever leaks into `verified_facts`'s enum (schema-enforced, re-asserted here for this specific document).
