# Live dry-run report: 03-software-csv-export

- **Scenario:** "Use Groundspec to add CSV export to an existing Python CLI without breaking its JSON contract."
- **Date:** 2026-09-17
- **Model:** Claude (same model family as the engineering session that built this feature, Sonnet 5); dispatched as a fresh, isolated subagent via the Agent tool with no memory of the engineering conversation, no `model` override passed, so it ran under whichever default the harness configures for that agent type. The exact underlying model build was not independently re-verified beyond that.
- **Evaluator:** the subagent's own report is model-generated; a human/deterministic pass reviewed it afterward (this file) against the actual files it left on disk -- the contract's schema validity, the code diff, and the test run were independently re-checked, not taken on the subagent's word alone (see "Independent verification" below).
- **What this is:** a genuine live run -- the subagent read the exported Skill at `dry-run/.claude/skills/groundspec/` and used the real, installed `groundspec` CLI (not a mock) to do the work. It is not a static template substitution.
- **Limitations / possible bias:** one scenario, one run, no repeated sampling, and the subagent is the same model family that wrote the Skill it was following -- a genuinely independent model (different vendor/version) might surface different gaps. This is not a statistically powered evaluation; it's one concrete, verifiable data point plus qualitative feedback on the Skill's instructions. The full 3-arm comparison and the other three example scenarios were not run live -- see `examples/metaskill/README.md`.

## What it produced

- `result/csv-export-inventory-cli.toml` -- a real Task Contract, built via `groundspec create` then hand-edited (never hand-authored from scratch).
- `fixture/inventory.py` / `fixture/test_inventory.py` -- real code changes: an additive `--format {json,csv}` flag on the `report` command, defaulting to `json` (unchanged default behavior), plus three new tests alongside the original.
- `result/evidence.json` -- the evidence file it fed to `groundspec evaluate`.

## Independent verification (re-checked after the subagent finished, not just trusted)

```
$ .venv/Scripts/python.exe -m pytest examples/metaskill/03-software-csv-export/fixture/test_inventory.py -v
```
All 4 tests pass, including the original `test_report_json_contract_unchanged` (confirms the JSON contract claim independently of the subagent's own report).

```
$ .venv/Scripts/groundspec.exe validate examples/metaskill/03-software-csv-export/result/csv-export-inventory-cli.toml
$ .venv/Scripts/groundspec.exe audit examples/metaskill/03-software-csv-export/result/csv-export-inventory-cli.toml
$ .venv/Scripts/groundspec.exe evaluate examples/metaskill/03-software-csv-export/result/csv-export-inventory-cli.toml examples/metaskill/03-software-csv-export/result/
```
All three re-run cleanly against the actual file on disk with the same result the subagent reported: valid contract, static audit passed with no precedence conflicts, `Verdict: insufficient_evidence` (non-gating -- no soft objectives were declared) alongside `Completion state: PASS`.

The contract predates this feature's schema bump to `0.2.0` (the subagent ran against the `0.1.0` default that was current at dispatch time) -- it still validates, since `0.1.0` remains fully supported; it was deliberately left as-is rather than bumped after the fact, to keep this as an honest, unedited record of what the live run actually produced.

## Real findings from this run, and what was fixed as a result

The subagent's report flagged four concrete problems with the Skill's own instructions. All four were fixed in the canonical Meta-Skill content as a direct result of this dry run (see the diff in the commit that added this file):

1. **`groundspec evaluate`'s `Verdict: insufficient_evidence` line was undocumented and easy to misread as a failure.** It's actually about `quality.soft_objectives` scoring specifically, independent of the gating `Completion state` line. Fixed: `execution-and-verification.md` now says this explicitly.
2. **The workflow doc's "what to hand-edit" list omitted the `status` section**, even though several hard constraints require it to be populated before an honest `PASS` is possible. Fixed: `task-contract-workflow.md` step 3 now lists `status` too.
3. **A real TOML-authoring footgun**: writing `[[status.verified_facts]]` before other scalar/array keys in the same table causes those later keys to silently attach to the wrong table (a TOML scoping rule, not a groundspec bug, but the Skill sends people into hand-editing TOML without warning them). Fixed: added an explicit tip in `task-contract-workflow.md`.
4. **Quick-vs-Guided mode selection was ambiguous** for a request that's both "professional engineering work" and "a fast, well-scoped ask." Fixed: `SKILL.md`'s mode table now notes that risk overlays drive the contract-preview requirement independently of mode, so the mode choice mostly only affects the question budget, not safety-relevant behavior.

This is exactly the kind of gap a live run finds that a purely constructed example (like the other three in `examples/metaskill/`) cannot -- see `examples/metaskill/README.md` for why those three are labeled differently.
