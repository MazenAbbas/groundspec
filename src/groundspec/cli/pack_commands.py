"""Implementations of `groundspec pack <subcommand>` for the Domain Pack SDK.

Kept separate from ``cli/commands.py`` (the pre-SDK contract/skill commands)
purely for file size; wired into the same argparse tree in ``cli/main.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from groundspec.contract.serialization import UnknownFileFormat
from groundspec.contract.validator import SchemaValidationError
from groundspec.packs.sdk import discovery
from groundspec.packs.sdk.discovery import ORIGIN_OFFICIAL
from groundspec.packs.sdk.errors import PackSdkError
from groundspec.packs.sdk.lock import build_lock_document, write_lock
from groundspec.packs.sdk.manifest import MANIFEST_FILENAME, load_pack
from groundspec.packs.sdk.resolver import resolve
from groundspec.packs.sdk.scaffold import init_pack
from groundspec.packs.sdk.testing import run_pack_tests
from groundspec.rules.errors import RulePackError
from groundspec.rules.pack_loader import load_pack_file, resolve_pack

OK = "[OK]"
FAIL = "[FAIL]"


def _all_locations() -> list[discovery.PackLocation]:
    return discovery.discover_all()


def _find_pack_dir_by_id(pack_id: str) -> discovery.PackLocation | None:
    for location in _all_locations():
        try:
            manifest_pack_id = _peek_pack_id(location.pack_dir)
        except PackSdkError:
            continue
        if manifest_pack_id == pack_id:
            return location
    return None


def _peek_pack_id(pack_dir: Path) -> str:
    from groundspec.packs.sdk.manifest import load_manifest_dict

    data = load_manifest_dict(pack_dir / MANIFEST_FILENAME)
    pack_id = data["pack_id"]
    assert isinstance(pack_id, str)
    return pack_id


def cmd_pack_list(args: object) -> int:
    as_json = bool(getattr(args, "json", False))
    rows = []
    for location in _all_locations():
        try:
            pack = load_pack(location.pack_dir, origin=location.origin)
        except PackSdkError as exc:
            print(f"{FAIL} {location.pack_dir}: {exc}", file=sys.stderr)
            continue
        rows.append(
            {
                "pack_id": pack.pack_id,
                "version": pack.version,
                "origin": pack.origin,
                "official": pack.origin == ORIGIN_OFFICIAL,
                "description": pack.manifest.description,
                "capabilities": list(pack.manifest.capabilities),
                "min_platform_version": pack.manifest.min_platform_version,
                "max_platform_version": pack.manifest.max_platform_version,
            }
        )
    if as_json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        print("No packs discovered.")
        return 0
    for row in rows:
        tag = "official" if row["official"] else str(row["origin"])
        row_capabilities = row["capabilities"]
        assert isinstance(row_capabilities, list)
        caps = ", ".join(row_capabilities) or "(none declared)"
        print(f"{row['pack_id']} v{row['version']} [{tag}] -- {row['description']}")
        print(f"    capabilities: {caps}")
    return 0


def cmd_pack_inspect(args: object) -> int:
    pack_id_or_path = getattr(args, "pack", None)
    as_json = bool(getattr(args, "json", False))
    pack_dir = _resolve_pack_arg_to_dir(pack_id_or_path)
    if pack_dir is None:
        print(f"{FAIL} no pack found for {pack_id_or_path!r}", file=sys.stderr)
        return 2
    try:
        pack = load_pack(pack_dir, origin=_origin_for(pack_dir))
    except PackSdkError as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        return 1

    report = {
        "pack_id": pack.pack_id,
        "version": pack.version,
        "display_name": pack.manifest.display_name,
        "description": pack.manifest.description,
        "origin": pack.origin,
        "content_hash": pack.content_hash,
        "capabilities": list(pack.manifest.capabilities),
        "supported_intents": list(pack.manifest.supported_intents),
        "routing": {
            "triggers": list(pack.manifest.routing_triggers),
            "exclusions": list(pack.manifest.routing_exclusions),
        },
        "compatibility": {
            "min_platform_version": pack.manifest.min_platform_version,
            "max_platform_version": pack.manifest.max_platform_version,
        },
        "dependencies": [
            {"pack_id": d.pack_id, "min_version": d.min_version, "max_version": d.max_version}
            for d in pack.manifest.dependencies
        ],
        "suggested": list(pack.manifest.suggested),
        "conflicts": [
            {
                "pack_id": c.pack_id,
                "reason": c.reason,
                "min_version": c.min_version,
                "max_version": c.max_version,
            }
            for c in pack.manifest.conflicts
        ],
        "priority": pack.manifest.priority,
        "risk_classification": pack.manifest.risk_classification,
        "provided_rule_ids": [r["id"] for r in pack.rules.rules] if pack.rules else [],
        "provided_rule_count": len(pack.rules.rules) if pack.rules else 0,
        "evidence_policy_ids": [p.id for p in pack.evidence_policies],
        "acceptance_template_ids": [t.id for t in pack.acceptance_templates],
        "completion_gate_ids": [g.id for g in pack.completion_gates],
        "question_ids": [q.id for q in pack.questions],
        "reference_paths": list(pack.reference_paths),
        "test_scenario_count": len(pack.scenarios),
    }
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print(f"{pack.pack_id} v{pack.version} ({pack.manifest.display_name}) [{pack.origin}]")
    print(f"  {pack.manifest.description}")
    print(f"  content hash: {pack.content_hash}")
    print(f"  capabilities: {', '.join(pack.manifest.capabilities) or '(none)'}")
    print(f"  supported intents: {', '.join(pack.manifest.supported_intents) or '(all)'}")
    print(f"  compatibility: >= {pack.manifest.min_platform_version}"
          f"{', <= ' + pack.manifest.max_platform_version if pack.manifest.max_platform_version else ''}")
    if pack.manifest.dependencies:
        print("  dependencies:")
        for d in pack.manifest.dependencies:
            upper = f", <= {d.max_version}" if d.max_version else ""
            print(f"    - {d.pack_id} >= {d.min_version}{upper}")
    if pack.manifest.conflicts:
        print("  conflicts:")
        for c in pack.manifest.conflicts:
            print(f"    - {c.pack_id} ({c.reason})")
    if pack.rules:
        rule_ids = ", ".join(str(r["id"]) for r in pack.rules.rules)
        print(f"  provides {len(pack.rules.rules)} rule(s): {rule_ids}")
    if pack.completion_gates:
        print(f"  provides {len(pack.completion_gates)} completion gate(s): "
              f"{', '.join(g.id for g in pack.completion_gates)}")
    if pack.questions:
        print(f"  provides {len(pack.questions)} clarification dimension(s)")
    if pack.evidence_policies:
        print(f"  provides {len(pack.evidence_policies)} evidence polic(y/ies)")
    if pack.acceptance_templates:
        print(f"  provides {len(pack.acceptance_templates)} acceptance template(s)")
    if pack.reference_paths:
        print(f"  references: {', '.join(pack.reference_paths)}")
    if pack.scenarios:
        print(f"  {len(pack.scenarios)} test scenario(s) (run with `groundspec pack test {pack.pack_id}`)")
    return 0


def cmd_pack_init(args: object) -> int:
    pack_id = args.pack_id  # type: ignore[attr-defined]
    output = Path(getattr(args, "output", None) or ".")
    force = bool(getattr(args, "force", False))
    try:
        pack_dir = init_pack(pack_id, output, force=force)
    except PackSdkError as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        return 1
    print(f"{OK} wrote {pack_dir}")
    print(f"  Run: groundspec pack validate {pack_dir}")
    return 0


def cmd_pack_validate(args: object) -> int:
    """Smart, backward-compatible validate: a bare single-file rule pack
    (the pre-SDK format, e.g. a project-level .groundspec/packs/*.toml
    rule pack with no manifest) validates exactly as it always has; a
    Domain Pack directory or pack.toml path, or a bare pack-id looked up
    in the registry, validates as a full Domain Pack."""
    target = args.path  # type: ignore[attr-defined]
    path = Path(target)

    if path.is_dir():
        return _validate_pack_dir(path)
    if path.is_file() and path.name == MANIFEST_FILENAME:
        return _validate_pack_dir(path.parent)
    if path.is_file():
        return _validate_bare_rule_pack_file(path)

    location = _find_pack_dir_by_id(target)
    if location is not None:
        return _validate_pack_dir(location.pack_dir)

    print(f"{FAIL} {target}: no such file/directory, and no pack with that id is registered", file=sys.stderr)
    return 2


def _validate_pack_dir(pack_dir: Path) -> int:
    try:
        pack = load_pack(pack_dir, origin=_origin_for(pack_dir))
    except PackSdkError as exc:
        print(f"{FAIL} {pack_dir}: {exc}", file=sys.stderr)
        return 1
    print(f"{OK} {pack_dir}: Domain Pack {pack.pack_id!r} v{pack.version} is valid ({pack.content_hash})")
    return 0


def _validate_bare_rule_pack_file(path: Path) -> int:
    try:
        data = load_pack_file(path)
        resolve_pack(path, search_dirs=[path.parent])
    except (RulePackError, SchemaValidationError, UnknownFileFormat, FileNotFoundError) as exc:
        print(f"{FAIL} {path}: {exc}", file=sys.stderr)
        return 1
    rules = data["rules"]
    assert isinstance(rules, list)
    print(f"{OK} {path}: pack {data['pack_id']!r} v{data['version']} ({len(rules)} rule(s)) is valid")
    return 0


def _origin_for(pack_dir: Path) -> str:
    for location in _all_locations():
        if location.pack_dir.resolve() == pack_dir.resolve():
            return location.origin
    return discovery.ORIGIN_PROJECT


def _resolve_pack_arg_to_dir(arg: str | None) -> Path | None:
    if not arg:
        return None
    path = Path(arg)
    if path.is_dir():
        return path
    if path.is_file() and path.name == MANIFEST_FILENAME:
        return path.parent
    location = _find_pack_dir_by_id(arg)
    return location.pack_dir if location else None


def cmd_pack_resolve(args: object) -> int:
    requested = list(getattr(args, "pack", None) or [])
    if not requested:
        print(f"{FAIL} pass at least one --pack <id>", file=sys.stderr)
        return 2
    allow_shadow = frozenset(getattr(args, "allow_shadow", None) or [])
    as_json = bool(getattr(args, "json", False))

    try:
        result = resolve(requested, allow_shadow=allow_shadow)
    except PackSdkError as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        return 1

    if as_json:
        report = {
            "ok": result.ok,
            "requested": list(result.requested_ids),
            "selected": [
                {
                    "pack_id": e.pack.pack_id,
                    "version": e.pack.version,
                    "origin": e.pack.origin,
                    "requested": e.requested,
                    "content_hash": e.pack.content_hash,
                    "rule_ids": [r["id"] for r in e.pack.rules.rules] if e.pack.rules else [],
                }
                for e in result.selected
            ],
            "conflicts": [
                {
                    "kind": c.kind,
                    "classification": c.classification,
                    "message": c.message,
                    "packs": list(c.involved_pack_ids),
                }
                for c in result.conflicts
            ],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if result.ok else 1

    print(f"Resolved {len(result.selected)} pack(s) for: {', '.join(result.requested_ids)}")
    for entry in result.selected:
        tag = "requested" if entry.requested else "dependency"
        print(f"  - {entry.pack.pack_id} v{entry.pack.version} [{entry.pack.origin}, {tag}]")
        if entry.pack.rules:
            print(f"      rules: {', '.join(str(r['id']) for r in entry.pack.rules.rules)}")
    if result.conflicts:
        print("Conflicts:")
        for c in result.conflicts:
            print(f"  [{c.classification}] {c.message}")
    status_word = "is valid" if result.ok else "has unresolved conflicts"
    print(f"\n{OK if result.ok else FAIL} composition {status_word}")
    return 0 if result.ok else 1


def cmd_pack_test(args: object) -> int:
    target = args.path  # type: ignore[attr-defined]
    pack_dir = _resolve_pack_arg_to_dir(target)
    if pack_dir is None:
        print(f"{FAIL} no pack found for {target!r}", file=sys.stderr)
        return 2
    try:
        pack = load_pack(pack_dir, origin=_origin_for(pack_dir))
    except PackSdkError as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        return 1

    if not pack.scenarios:
        print(f"{OK} {pack.pack_id}: no test scenarios declared")
        return 0

    results = run_pack_tests(pack)
    failed = [r for r in results if not r.passed]
    for r in results:
        tag = OK if r.passed else FAIL
        print(f"{tag} [{r.evaluation_kind}] {r.scenario_id}")
        for failure in r.failures:
            print(f"    {failure}")
    print(f"\n{len(results) - len(failed)}/{len(results)} scenario(s) passed")
    return 0 if not failed else 1


def cmd_pack_lock(args: object) -> int:
    requested = list(getattr(args, "pack", None) or [])
    if not requested:
        print(f"{FAIL} pass at least one --pack <id>", file=sys.stderr)
        return 2
    allow_shadow = frozenset(getattr(args, "allow_shadow", None) or [])
    out_path = Path(getattr(args, "out", None) or "groundspec.lock")

    try:
        result = resolve(requested, allow_shadow=allow_shadow)
    except PackSdkError as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        return 1

    if not result.ok:
        print(f"{FAIL} refusing to lock: unresolved conflicts", file=sys.stderr)
        for c in result.conflicts:
            if c.classification != "resolvable_by_precedence":
                print(f"  [{c.classification}] {c.message}", file=sys.stderr)
        return 1

    write_lock(result, out_path)
    doc = build_lock_document(result)
    print(f"{OK} wrote {out_path} ({len(doc['packs'])} pack(s) locked)")
    return 0
