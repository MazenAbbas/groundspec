# Domain Pack backlog

This release (`v0.3.0rc1`) ships two official Domain Packs, `product-management` and `data-science-ml`, on top of the new Domain Pack SDK. It deliberately does not attempt every possible professional domain -- see `docs/architecture.md`'s Domain Pack SDK section for why the platform, not an ever-growing Meta-Skill, is the intended way to add more.

## Planned ordinary packs (no special review requirements beyond the existing pack-authoring process)

Listed in no particular priority order; each would follow the same shape as `product-management`/`data-science-ml` (`pack.toml` manifest, a rules file, optional `questions.toml`/`evidence-policy.toml`/`acceptance-templates.toml`/`completion-gates.toml`, a guidance reference, and `tests/scenarios.toml`):

- `data-engineering` -- pipeline design, data-quality checks, schema evolution, batch vs. streaming trade-offs.
- `ux-research` -- study design, participant recruitment disclosure, qualitative-vs-quantitative evidence labeling, usability-finding severity.
- `education-learning` -- curriculum/assessment design, learning-objective alignment, accessibility of instructional material.
- `cybersecurity-defensive` -- defensive security posture reviews, detection engineering, incident-response runbooks -- explicitly defensive-only; would need its own authorization-context and dual-use-disclosure rules analogous to the existing `security_sensitive` overlay, scoped tighter than the general overlay.
- `business-analysis` -- requirements elicitation, process modeling, stakeholder-conflict resolution, cost-benefit framing.
- `operations` -- runbooks, SLOs/SLAs, on-call/incident process, change-management gates.
- `technical-writing` -- documentation structure, audience-appropriateness, accuracy-vs-source-material checks.
- `marketing-strategy` -- positioning, channel strategy, campaign measurement -- distinct from the existing `content` pack, which covers the copy/publication act itself, not the strategic plan behind it.
- `career-development` -- resume/interview preparation, skill-gap analysis -- would need care that it never drifts into personalized financial or legal advice about employment contracts.
- `startup-validation` -- problem/solution validation methodology, would substantially overlap `product-management` and `research`; likely implemented as a thin pack that mostly composes the two via `dependencies` rather than duplicating their rules.
- `quality-assurance` -- test strategy, coverage rationale, defect triage -- distinct from `software`'s existing `tests-scaled-to-risk-and-actually-run` rule, which is about *a* task's own testing, not QA as its own discipline.

## Domains that must not ship as ordinary packs

Medical, legal, and investment-advice domains are **not** planned as ordinary Domain Packs, and this project will not add them as such. A pack in one of these domains would need, at minimum, before it could responsibly ship:

- **Expert review of the pack's own rules, questions, evidence policies, and completion gates** by a qualified professional in that field (a licensed clinician, an attorney, a licensed financial advisor) -- not just a software engineer's best effort at encoding the domain, however careful.
- **An explicit, enforced disclaimer surface**: every deliverable this pack's rules apply to would need a mechanically-checked disclaimer (not just documentation prose) that the output is not a diagnosis, legal opinion, or investment recommendation, and that it does not create a professional relationship.
- **A higher evidentiary bar for claim_ledger entries** in this domain than `PRIMARY_SOURCE_VERIFIED`/`SECONDARY_SOURCE_SUPPORTED` currently require -- likely requiring a named, checkable credential or citation to an authoritative regulatory body (FDA/EMA-equivalent, a bar association, a financial regulator) specific to the claim's jurisdiction, which the current schema's `authority_level` enum does not yet distinguish finely enough for.
- **A completion-gate design that can never reach `PASS`** (only, at best, `PASS_WITH_CAVEATS` with a mandatory named human-expert-review step) for any deliverable that would be acted on directly by an end user without an intermediary professional -- unlike `product-management`/`data-science-ml`, where a disclosed limitation can responsibly reach a caveated pass.
- **A legal/liability review of Groundspec itself** as a project, given that shipping structured guidance in these domains carries materially different risk than shipping it for product PRDs or ML evaluation plans.

The `domain_pack.v0_1_0.schema.json` manifest already reserves a `risk_classification` field (`standard` / `requires_expert_review`) precisely so a future pack in one of these domains has somewhere to declare this -- but the CLI does not yet gate on that value beyond surfacing it via `pack list`/`pack inspect`, and no such pack ships in this release. This is a disclosed gap, not a hidden one: see `docs/threat-model.md`'s Domain Pack extensibility section.
