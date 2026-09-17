# Domain guidance: content and marketing

Select `--domain content`, and add `external_communication` to `routing.risk_overlays` whenever the output is meant to be published or sent, not just drafted. The pack expects audience/objective/channel defined up front, every substantive claim traceable to a verified fact, no fabricated urgency/scarcity/testimonials/statistics under any framing, brand-voice and platform-format constraints respected, and a named review/approval step plus an outcome measurement.

Practical tips specific to this Skill's workflow:

- Publishing itself always requires per-instance confirmation regardless of mode -- see `execution-and-verification.md`'s authorization gates. Drafting does not; don't over-block on this.
- If the request is to *audit* existing content (Audit mode), check each measurable claim against `status.verified_facts` and flag any claim with no matching entry as an `unverified_claim` rather than assuming it's fine because it reads persuasively.
- Length/format constraints from the platform (character limits, etc.) belong in `scope.constraints` and are enforced as a `soft_objective` by the domain pack; a task-specific preference to ignore them is a legitimate project-layer rule pack, and if it conflicts, the domain rule wins by precedence (see `routing-and-risk.md` and the repository's `examples/09-domain-rule-vs-style-preference`) -- that's expected, not a bug to work around.
- Do not fabricate a testimonial, statistic, or urgency claim to make content more persuasive even if explicitly asked to "make it punchier" -- that instruction does not override the hard constraint, and the right response is to say so and offer a substantiated alternative instead.
