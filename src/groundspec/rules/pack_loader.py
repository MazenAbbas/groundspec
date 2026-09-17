"""Loads a single rule-pack file and resolves its ``imports``.

Security posture (see docs/threat-model.md):

* A rule pack is exactly one JSON or TOML file -- never a directory or
  archive -- so there is no zip-slip or archive-extraction surface in v0.1.
* ``pack_id`` is constrained by the schema to ``[a-z0-9][a-z0-9_.-]*`` with
  no path separators, so it can never be used to escape the search
  directories it is looked up in; there is no user-controlled path
  concatenation anywhere in this module.
* Imports are resolved by ``pack_id``/``version`` against an explicit,
  caller-supplied list of search directories -- never by a path embedded in
  the (untrusted) pack content itself.
* Cycle detection, a fixed import-depth ceiling, and duplicate-id detection
  all raise rather than silently drop or silently pick a winner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from groundspec.contract.serialization import UnknownFileFormat, load_document
from groundspec.contract.validator import validate_rule_pack_dict
from groundspec.rules.errors import (
    CyclicImport,
    DuplicateRuleId,
    ImportDepthExceeded,
    PackNotFound,
    PackVersionMismatch,
    RulePackError,
)

DEFAULT_MAX_IMPORT_DEPTH = 4


@dataclass(frozen=True)
class LoadedPack:
    pack_id: str
    version: str
    layer: str
    title: str
    rules: list[dict[str, object]]
    imported: list[LoadedPack] = field(default_factory=list)


def _find_pack_file(pack_id: str, search_dirs: list[Path]) -> Path:
    for directory in search_dirs:
        for suffix in (".json", ".toml"):
            candidate = directory / f"{pack_id}{suffix}"
            if candidate.is_file():
                return candidate
    raise PackNotFound(
        f"rule pack {pack_id!r} not found in any of: {', '.join(str(d) for d in search_dirs)}"
    )


def load_pack_file(path: Path) -> dict[str, object]:
    try:
        data = load_document(path)
    except UnknownFileFormat as exc:
        raise RulePackError(str(exc)) from exc
    issues = validate_rule_pack_dict(data)
    if issues:
        from groundspec.contract.validator import SchemaValidationError

        raise SchemaValidationError(issues)
    _check_duplicate_rule_ids(data)
    return data


def _check_duplicate_rule_ids(pack: dict[str, object]) -> None:
    seen: set[str] = set()
    rules = pack.get("rules", [])
    assert isinstance(rules, list)
    for rule in rules:
        assert isinstance(rule, dict)
        rule_id = rule["id"]
        assert isinstance(rule_id, str)
        if rule_id in seen:
            raise DuplicateRuleId(f"pack {pack['pack_id']!r} declares rule id {rule_id!r} twice")
        seen.add(rule_id)


def resolve_pack(
    entry_path: Path,
    *,
    search_dirs: list[Path] | None = None,
    max_import_depth: int = DEFAULT_MAX_IMPORT_DEPTH,
) -> LoadedPack:
    """Load ``entry_path`` and recursively resolve its declared imports."""
    search_dirs = search_dirs or [entry_path.parent]
    return _resolve(entry_path, search_dirs=search_dirs, max_depth=max_import_depth, depth=0, stack=())


def _resolve(
    path: Path,
    *,
    search_dirs: list[Path],
    max_depth: int,
    depth: int,
    stack: tuple[str, ...],
) -> LoadedPack:
    data = load_pack_file(path)
    pack_id = data["pack_id"]
    version = data["version"]
    assert isinstance(pack_id, str) and isinstance(version, str)

    if pack_id in stack:
        cycle = " -> ".join((*stack, pack_id))
        raise CyclicImport(f"cyclic rule-pack import detected: {cycle}")
    if depth > max_depth:
        raise ImportDepthExceeded(
            f"import depth exceeded {max_depth} while loading {pack_id!r} "
            f"(chain: {' -> '.join(stack)})"
        )

    imports = data.get("imports", [])
    assert isinstance(imports, list)
    imported: list[LoadedPack] = []
    for ref in imports:
        assert isinstance(ref, dict)
        ref_id = ref["pack_id"]
        ref_version = ref["version"]
        assert isinstance(ref_id, str) and isinstance(ref_version, str)
        import_path = _find_pack_file(ref_id, search_dirs)
        child = _resolve(
            import_path,
            search_dirs=search_dirs,
            max_depth=max_depth,
            depth=depth + 1,
            stack=(*stack, pack_id),
        )
        if child.version != ref_version:
            raise PackVersionMismatch(
                f"{pack_id!r} imports {ref_id!r}=={ref_version!r} but found {child.version!r}"
            )
        imported.append(child)

    layer = data["layer"]
    title = data["title"]
    rules = data["rules"]
    assert isinstance(layer, str) and isinstance(title, str) and isinstance(rules, list)
    return LoadedPack(
        pack_id=pack_id,
        version=version,
        layer=layer,
        title=title,
        rules=rules,
        imported=imported,
    )


def flatten(pack: LoadedPack) -> list[LoadedPack]:
    """All packs in a resolved import tree, entry pack first, no duplicates."""
    seen: dict[str, LoadedPack] = {}

    def _walk(p: LoadedPack) -> None:
        if p.pack_id not in seen:
            seen[p.pack_id] = p
        for child in p.imported:
            _walk(child)

    _walk(pack)
    return list(seen.values())
