# Pack discovery, inspection, and scaffolding

This file is about the Domain Pack SDK's own CLI surface, not about which pack fits a request (that's `routing-and-risk.md`).

## Discover what's actually available -- don't assume

Before proposing a pack the user hasn't heard of, or if you're unsure a project has a local override, run `groundspec pack list` (or `--json` for a stable machine-readable form). It reports every pack this installation can actually see, from all three supported origins:

1. **official** -- shipped with `groundspec` itself (`software`, `research`, `content`, `product-management`, `data-science-ml` as of this writing -- don't hard-code this list from memory, run `pack list`, since a project's own Groundspec version may ship more).
2. **project** -- `.groundspec/packs/<pack-id>/` in the current project, created via `groundspec pack init`.
3. **user** -- `~/.groundspec/packs/<pack-id>/`, if that directory exists. Never auto-created, never auto-downloaded -- there is no remote pack marketplace in this version of Groundspec, and you must never imply one exists.

## Inspecting a specific pack

`groundspec pack inspect <pack-id>` shows the full manifest: version, capabilities, supported intents, routing triggers/exclusions (advisory, not a matching algorithm), compatibility range, dependencies, conflicts, every rule/gate/question/evidence-policy/acceptance-template it provides, and its content hash. Use this instead of guessing at a pack's contents from memory -- packs can be versioned and a project may pin an older one.

## Scaffolding a new pack

If a user wants a domain Groundspec doesn't ship yet, `groundspec pack init <pack-id> --output .groundspec/packs` creates the smallest valid pack skeleton (a manifest, one example rule, one guidance note) that passes `groundspec pack validate` immediately. Fill in the actual rules/questions/evidence-policy/completion-gates yourself or guide the user through it -- never hand-author a pack.toml from scratch when `pack init` exists, for the same reason you never hand-author a Task Contract.

**A pack is declarative policy and guidance data, not code.** It cannot run commands, import Python modules, grant permissions, expand your authorization, contact the network, or modify Groundspec's own behavior outside its documented extension points (rules, questions, evidence policies, acceptance templates, completion gates). If asked to make a pack "smarter" by having it execute something, say plainly that this isn't how Domain Packs work and explain the extension points that do exist instead.

## Composing more than one pack

See `routing-and-risk.md`'s "Multi-pack composition" section for `groundspec pack resolve`/`lock` -- the deterministic step that validates whatever pack(s) you proposed, before a Task Contract is ever built from them.

## What this pack layer deliberately does not do (yet)

No remote marketplace, no automatic download, no scanning of arbitrary parent directories for packs, no medical/legal/investment-advice packs shipped as ordinary packs (those need additional expert-review process this version does not implement -- see the project's own `docs/domain-pack-backlog.md` if asked about them). Say so plainly rather than implying broader capability than exists.
