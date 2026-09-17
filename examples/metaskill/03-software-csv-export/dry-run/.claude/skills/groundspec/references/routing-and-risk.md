# Routing and risk

Don't restate the rule packs' contents here -- read them with `groundspec pack validate` or by inspecting the pack files if you need the exact requirement text. This file is only about *which* packs and overlays to select for a given request.

## Domain packs (`--domain`, one or more)

- `software` -- building, changing, or reviewing code, CLIs, APIs, infrastructure, or a technical product.
- `research` -- answering a factual/evidentiary question, market or literature analysis, evaluating options against evidence.
- `content` -- writing or reviewing anything meant to be read by an external audience: posts, marketing copy, documentation for publication, announcements.

A request can span more than one (e.g. "build a feature and announce it" is `software` + `content`). If none obviously fit, it's fine to select none -- `core-invariants` and the selected risk overlays still apply on their own.

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

## After selecting: let the deterministic engine do the rest

`groundspec audit <contract>` resolves every pack you selected (core invariants always included, automatically) in strict precedence order (core > risk overlay > domain > project) and reports:
- every applicable hard constraint, tagged mechanically-checkable vs. needs-human/model-judgment;
- any precedence conflict between rules sharing a `conflict_key`, with a deterministic explanation of which one wins and why.

A reported conflict is not itself a problem to fix -- it's the system working as designed (see the repo's `examples/09-domain-rule-vs-style-preference` for what a real one looks like). Read the conflict's explanation and make sure the *winning* rule is actually the behavior you want; if it isn't, that's a signal the domain pack selection or the request's own constraints need revisiting, not that the conflict report is wrong.

## `routing.risk_level`

Set this to the overall gating severity implied by the highest-severity overlay present: `low` for `informational` alone, `medium` for `filesystem_mutation`/`external_communication`, `high` for `destructive_irreversible`/`security_sensitive`/`personal_data`, `critical` for `high_stakes_regulated`. This is a starting heuristic, not a rule the engine enforces automatically -- use judgment when a request combines overlays in an unusual way.
