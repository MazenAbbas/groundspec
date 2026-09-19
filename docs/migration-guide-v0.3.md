# Migration guide: v0.2.0rc3 -> v0.3.0rc1 (Domain Pack SDK)

**Short version: nothing breaks.** No action is required to keep an existing project, contract, or Skill export working exactly as it did under `v0.2.0rc3`. This guide explains what changed under the hood and how to adopt the new Domain Pack SDK if and when you want to.

## What actually changed

`v0.3.0rc1` adds a Domain Pack SDK (`groundspec.packs.sdk`) and a new `groundspec pack {list,inspect,init,validate,resolve,test,lock}` command surface on top of the existing rule-pack engine (`groundspec.rules.*`), which is **byte-for-byte unchanged**. The three existing official domain packs -- `software`, `research`, `content` -- now additionally ship a `pack.toml` manifest that wraps their existing rule file:

```toml
# src/groundspec/packs/software/pack.toml (illustrative excerpt)
[provides]
rules = "domain-software.json"   # the exact, unmodified file that has always been there
```

`domain-software.json`, `domain-research.json`, and `domain-content.json` themselves were not touched -- same content, same file, same SHA. The `pack.toml` files are purely additive: a new artifact the SDK's discovery/resolution/inspection layer reads, sitting next to files that already existed.

## What stays true, unchanged

- **Existing contracts remain valid.** A contract referencing `routing.domain_packs[].pack_id = "software"` (or `research`/`content`) resolves through the exact same code path (`groundspec.packs.registry.select_packs_for_contract` -> `groundspec.rules.pack_loader`) it always did. This SDK release did not touch that module's logic for those three packs.
- **Current pack IDs remain supported.** `software`, `research`, `content` mean exactly what they meant before.
- **Existing rule IDs remain stable.** Every rule ID in `domain-software.json`/`domain-research.json`/`domain-content.json` is unchanged.
- **Old serialized reports continue to load.** Nothing about `evidence.json`'s shape, contract schema versions (`0.1.0`-`0.4.0`), or `groundspec evaluate`'s exit codes changed for a contract that doesn't reference a Domain-Pack-SDK-only pack (`product-management`/`data-science-ml`).
- **`v0.2.0rc3` workflows remain reproducible.** `groundspec create --domain software`, `groundspec compile`, `groundspec audit`, `groundspec evaluate` all behave identically for pre-existing contracts.
- **Task-specific Skill generation (`groundspec compile --target {generic,claude-code,codex}`) is untouched** -- it never depended on the Domain Pack SDK.
- Regression tests proving all of the above: `tests/integration/test_builtin_packs.py` (unchanged, still passing against the same fixtures), `tests/integration/test_pack_sdk_official_packs.py` (new, proves the SDK's view of `software`/`research`/`content` agrees with the pre-SDK view).

## What's new, and how to adopt it (optional)

- **`groundspec pack list`/`inspect`** now show all five official packs (including the two new ones, `product-management` and `data-science-ml`) with richer metadata (capabilities, dependencies, conflicts, completion gates) than the old bare `groundspec pack validate <file>` ever exposed.
- **`groundspec pack resolve`/`lock`** give you a deterministic, reproducible multi-pack composition check and a lock file -- useful once a project starts depending on more than one domain pack, or a project-local pack. Nothing requires you to start using these; `groundspec create --domain <id> --domain <id>` still works exactly as before, with the deterministic rule-engine composition happening the same way it always did at `compile`/`audit`/`evaluate` time.
- **`groundspec evaluate` now additionally checks any completion gates the selected pack(s) declare.** For the three pre-existing packs, this is a no-op -- `software`/`research`/`content` declare no `completion-gates.toml`, so nothing new is evaluated for a contract that only uses them. It only takes effect if you select `product-management` and/or `data-science-ml`, or a project-local pack that declares its own gates.
- **`groundspec pack validate`** is now "smart": pointed at a directory or a `pack.toml`, it validates a full Domain Pack; pointed at a bare single-file rule pack (the pre-SDK format, still exactly as valid as it always was for a project-level `.groundspec/packs/*.toml` file with no manifest), it falls back to the original single-file validation, unchanged. Existing `groundspec pack validate <file>.toml` invocations for a bare project rule pack keep working with the exact same output shape.

## If you want to migrate a project-local rule pack onto the new manifest format

You don't have to -- a bare rule-pack file under `.groundspec/packs/` continues to work indefinitely. If you do want the richer discovery/inspection/composition/locking the SDK provides, wrap it the same way the built-in packs were wrapped: create `.groundspec/packs/<pack-id>/pack.toml` with `provides.rules` pointing at your existing file (moved alongside it, or referenced by relative path within the new directory), fill in the required manifest fields, and validate with `groundspec pack validate .groundspec/packs/<pack-id>`. See `docs/pack-authoring-guide.md` for the full field reference.
