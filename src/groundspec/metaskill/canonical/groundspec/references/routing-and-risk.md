# Routing and risk

Don't restate the rule packs' contents here -- read them with `groundspec pack validate` or by inspecting the pack files if you need the exact requirement text. This file is only about *which* packs and overlays to select for a given request.

## Domain packs (`--domain`, one or more)

- `software` -- building, changing, or reviewing code, CLIs, APIs, infrastructure, or a technical product.
- `research` -- answering a factual/evidentiary question, market or literature analysis, evaluating options against evidence.
- `content` -- writing or reviewing anything meant to be read by an external audience: posts, marketing copy, documentation for publication, announcements.
- `product-management` -- PRDs, product discovery, MVP definition, roadmap decisions, launch criteria, go/no-go plans. Not for a small implementation task whose requirements are already fully specified (that's `software` alone). See `domain-guidance/product-management.md`.
- `data-science-ml` -- classification, regression, clustering, recommendation, ranking, anomaly detection, time-series forecasting, computer vision, NLP, retrieval/RAG evaluation, model comparison, dataset preparation, exploratory modeling, or a production-readiness review. Validates plans/evidence/completion claims -- never trains or runs a model itself, and never requires a heavy dependency. See `domain-guidance/data-science-ml.md`.

A request can span more than one. Worked examples:

| Request | Packs |
|---|---|
| "Design a churn prediction experiment" | `data-science-ml` + `research` |
| "Add a prediction endpoint to an existing Python service" | `software` + `data-science-ml` |
| "Write a PRD for a campus delivery product" | `product-management` + `research` |
| "Audit a launch post about model accuracy" | `content` + `data-science-ml` |

If none obviously fit, it's fine to select none -- `core-invariants` and the selected risk overlays still apply on their own.

**Proposing a pack from a request's wording is model-dependent, not deterministic** -- see `pack-routing.md` and this Skill's own non-negotiables. You may recommend and explain a selection; only `groundspec pack resolve` actually validates that the selection is available, version-compatible, and free of conflicts before it becomes part of a Task Contract.

**Only select a domain pack whose rules actually fit the request's own goal, not just its subject matter.** `domain-research`'s hard constraints are written for a task whose `brief.goal` *is* an answerable research question -- selecting `research` for a task that only *needs some supporting research* (e.g. a PRD that would benefit from market data) pulls in a rule like "the research question is stated explicitly and is answerable" that doesn't fit the actual goal, and `groundspec audit` will list it as an applicable hard constraint you now have to somehow satisfy or explain. Two independent forward tests hit exactly this with a PRD-scoping task: one removed the `research` pack after seeing the mismatch in `audit`'s output; the other kept it and had to explicitly note the mismatch and its own judgment call rather than silently forcing a fit. Prefer the first approach -- if a selected pack's rules don't fit the actual goal, remove the pack rather than reinterpreting the goal or the rule to make them match. If research is genuinely a supporting need rather than the goal itself, that's better handled by actually doing (or explicitly deferring, per `RESEARCH_NEEDED`) the research within whatever domain pack does fit, not by adding `research` for its own sake.

## Risk overlays (`--risk-overlay`, one or more; always include at least one)

| Overlay | Select when the request involves |
|---|---|
| `informational` | Pure read/produce work with no side effects. Include this by default when nothing else applies. |
| `external_communication` | Anything that will be sent, posted, or published where someone other than the requester sees it. |
| `filesystem_mutation` | Writing, moving, deleting, or restructuring files or repository state. |
| `destructive_irreversible` | An operation that destroys data or can't be cleanly undone (force-push, hard delete, dropping a table, overwriting the only copy of something). |
| `security_sensitive` | Building or running security tooling, credential handling, anything dual-use (offense/defense). Requires a recorded authorization context -- see the pack's own hard constraint before proceeding. |
| `high_stakes_regulated` | Medical, legal, financial, or safety-consequential territory. Triggers mandatory disclosures and an escalation condition -- see `execution-and-verification.md`. |
| `personal_data` | Reading, combining, or producing data about an identifiable person. |

When more than one applies, include all of them -- overlays are additive, not exclusive.

## Multi-pack composition: resolve before you build the contract

Once you've proposed which pack(s) fit, run `groundspec pack resolve --pack <id> [--pack <id> ...]` before `groundspec create` -- this is the Deterministic Pack Resolver from the state machine above. It reports, for real, not from judgment:

- the exact packs and versions selected, including any pulled in as dependencies;
- conflicts, each classified as `resolvable_by_precedence` (informational -- e.g. a shadowed pack or a completion-gate collision broken by declared `priority`; report it, don't treat it as an error), `requires_user_decision` (genuinely ambiguous -- e.g. two packs' completion gates disagree with no priority to break the tie; stop and ask), or the resolve command failing outright (an explicit `conflicts` declaration between two packs, a cross-pack duplicate rule id, an impossible/unsatisfied version range, or a dependency cycle -- none of these are choices you get to make silently; report the failure and its exact message).

`--json` gives a stable machine-readable form if you need to reason about the result programmatically. `groundspec pack lock --pack <id> [--pack <id> ...]` writes a `groundspec.lock` recording the exact resolved pack IDs/versions/content-hashes for reproducibility -- write one whenever the task's own record should be able to reproduce exactly which pack versions were in effect.

**An unofficial pack (project-local under `.groundspec/packs/`, or user-local) can never silently shadow an official one with the same id.** `pack resolve`/`pack lock` refuse this by default; a shadow requires an explicit `--allow-shadow <pack-id>`, and even then it's reported, not hidden. Never pass that flag on your own initiative -- surface the shadow to the user and let them decide.

## After resolving: let the deterministic engine do the rest

`groundspec audit <contract>` resolves every pack you selected (core invariants always included, automatically) in strict precedence order (core > risk overlay > domain > project) and reports:
- every applicable hard constraint, tagged mechanically-checkable vs. needs-human/model-judgment;
- any precedence conflict between rules sharing a `conflict_key`, with a deterministic explanation of which one wins and why.

A reported conflict is not itself a problem to fix -- it's the system working as designed (see the repo's `examples/09-domain-rule-vs-style-preference` for what a real one looks like). Read the conflict's explanation and make sure the *winning* rule is actually the behavior you want; if it isn't, that's a signal the domain pack selection or the request's own constraints need revisiting, not that the conflict report is wrong.

If the selected pack(s) declare completion gates (`product-management` and `data-science-ml` both do), `groundspec evaluate` applies them on top of the core completion state -- see `execution-and-verification.md`'s per-pack sections for the exact `evidence.json` fields each gate reads.

## `routing.risk_level`

Set this to the overall gating severity implied by the highest-severity overlay present: `low` for `informational` alone, `medium` for `filesystem_mutation`/`external_communication`, `high` for `destructive_irreversible`/`security_sensitive`/`personal_data`, `critical` for `high_stakes_regulated`. This is a starting heuristic, not a rule the engine enforces automatically -- use judgment when a request combines overlays in an unusual way.
