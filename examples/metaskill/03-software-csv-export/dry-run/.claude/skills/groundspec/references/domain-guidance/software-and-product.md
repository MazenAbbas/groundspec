# Domain guidance: software and product

Select `--domain software`. Read the pack's actual rules with `groundspec pack validate` if you need the exact requirement text; in short, it expects: a stated problem distinct from the solution, non-empty acceptance criteria scaled to `routing.risk_level` (not maximal by default), architecture decisions recorded when they'd surprise a future maintainer, backward-compatibility called out explicitly for interface changes, and any "tests pass" claim in evidence backed by an actual command run, not review alone.

Practical tips specific to this Skill's workflow:

- Scale ceremony to size: a five-minute config rename needs a tiny budget and one acceptance criterion (see `examples/04-five-minute-constrained-task` in the repository), not a full PRD.
- If the request touches an existing public interface, schema, or CLI, add `filesystem_mutation` to `routing.risk_overlays` and state backward-compatibility impact in `scope.constraints` or the acceptance criteria.
- If the request involves code handling external input, add `security_sensitive` so the injection/XSS/path-traversal hard constraint applies.
- Acceptance criteria for code should default to `reproducible_command` or `automated_test` verification, not `manual_inspection`, whenever a test can actually be run.
- For a new product/feature (not a small change), Guided mode's contract preview should surface: goal, target users, deliverables, and explicit non-goals -- scope creep is easier to prevent before execution than to walk back after.
