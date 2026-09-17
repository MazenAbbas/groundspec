# Contributing

Groundspec is pre-release. The repository is public at [github.com/MazenAbbas/groundspec](https://github.com/MazenAbbas/groundspec); issues and pull requests are welcome.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate   # or: source .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
```

Requires Python 3.11+ (the deterministic TOML reader uses the standard library's `tomllib`, which is 3.11+ only -- see `docs/architecture.md`).

## Before opening a PR

```bash
ruff check src tests eval scripts
mypy src
pytest
python -m build
twine check dist/*
```

All four must pass. CI (`.github/workflows/ci.yml`) runs the same checks across Windows/Ubuntu/macOS and Python 3.11-3.13.

## Code style

- No comments explaining *what* code does (names should do that); a comment is only for a non-obvious *why* -- a hidden constraint, a workaround, a subtle invariant.
- No dependency without a stated justification (see `docs/architecture.md` for the two existing ones: `jsonschema` and, in dev-only, `hatchling`/`pytest`/`ruff`/`mypy`/`build`/`twine`).
- Prefer the standard library. The deterministic core must keep working with no network access and no API key.

## Adding a rule to a built-in pack

1. Edit the relevant file under `src/groundspec/packs/`.
2. Run `pytest tests/integration/test_builtin_packs.py` -- it re-validates every built-in pack and re-checks the whole set for unexpected precedence conflicts.
3. If the new rule changes what an existing example demonstrates, update the relevant file under `examples/` and re-run `pytest tests/integration/test_examples.py`.
4. Add a rationale in `source_or_rationale` that traces back to a real requirement (a PRD line, a past incident, a standard) -- not just "seems right."

## Adding a domain pack

Domain packs are a deliberately small, curated set (`software`, `research`, `content` in v0.1) -- see the README's "Product boundaries." A new domain pack is a product decision, not just an engineering one; open an issue describing the target audience and why a project-layer pack (which anyone can already author locally, see `docs/rule-pack-authoring.md`) isn't sufficient before writing one.

## Schema changes

`contract_schema_version` and `rule_pack_schema_version` are `const` fields. A breaking schema change means adding a new versioned file (e.g. `task_contract.v0_2_0.schema.json`) alongside the old one, plus an explicit, tested migration function -- never editing `v0_1_0` in place once it's released. See `docs/architecture.md#schema-versioning-and-migration-strategy`.

## Commit style

One coherent subsystem per commit; no "misc fixes" grab-bags. No AI-attribution trailers or generated-by messages in commit text (see the project's own attribution policy).
