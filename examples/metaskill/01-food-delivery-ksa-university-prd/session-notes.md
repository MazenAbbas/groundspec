# Session notes: 01-food-delivery-ksa-university-prd

**Mode:** Guided. **Intent:** contract-only.

**How this example was produced:** constructed during Meta-Skill development to demonstrate the target contract shape for a Guided-mode planning request -- it was not captured from a live model run (unlike `examples/metaskill/03-software-csv-export`, which was). No claim is made that the assumptions/questions above are the objectively correct ones for a real Saudi food-delivery venture; they illustrate the *shape* of high-value-question selection and risk-ranking this Skill is meant to produce. A real invocation would need actual current research to fill in `status.verified_facts` before the PRD's market claims could be trusted.

**Corrected in v0.2.0rc2:** an independent forward test caught this example silently defaulting geographic/market scope as a plain assumption, contradicting the clarification policy's own checklist (which lists that dimension as near-universally material). It is now recorded as a deferred `high_value` open question instead -- see CHANGELOG.md's [0.2.0rc2] entry.
