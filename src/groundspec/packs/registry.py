"""Locates and resolves groundspec's built-in rule packs, and assembles the
full precedence-ordered stack (core -> risk overlays -> domain -> project)
for a given contract.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from groundspec.rules.pack_loader import LoadedPack, flatten, resolve_pack

CORE_PACK_ID = "core-invariants"

RISK_OVERLAY_PACK_IDS: dict[str, str] = {
    "informational": "risk-overlay-informational",
    "external_communication": "risk-overlay-external-communication",
    "filesystem_mutation": "risk-overlay-filesystem-mutation",
    "destructive_irreversible": "risk-overlay-destructive-irreversible",
    "security_sensitive": "risk-overlay-security-sensitive",
    "high_stakes_regulated": "risk-overlay-high-stakes-regulated",
    "personal_data": "risk-overlay-personal-data",
}

DOMAIN_PACK_IDS: dict[str, str] = {
    "software": "domain-software",
    "research": "domain-research",
    "content": "domain-content",
}


class BuiltinPackNotFound(ValueError):
    pass


def _builtin_search_dirs() -> list[Path]:
    # groundspec.packs is always installed as real files on disk (wheel and
    # editable installs alike are never zipped), so files() already returns
    # a usable Path without needing the as_file() extraction path.
    base = Path(str(resources.files("groundspec.packs")))
    return [base, base / "risk_overlays", base / "software", base / "research", base / "content"]


def load_builtin(pack_id: str, *, extra_search_dirs: list[Path] | None = None) -> LoadedPack:
    search_dirs = _builtin_search_dirs() + (extra_search_dirs or [])
    for directory in search_dirs:
        for suffix in (".json", ".toml"):
            candidate = directory / f"{pack_id}{suffix}"
            if candidate.is_file():
                return resolve_pack(candidate, search_dirs=search_dirs)
    raise BuiltinPackNotFound(f"no built-in pack named {pack_id!r}")


def select_packs_for_contract(
    contract: dict[str, object],
    *,
    project_pack_paths: list[Path] | None = None,
    extra_search_dirs: list[Path] | None = None,
) -> list[LoadedPack]:
    """Return every applicable pack, already flattened, in descending
    precedence order (core, risk overlays, domain, project)."""
    routing = contract["routing"]
    assert isinstance(routing, dict)

    packs: list[LoadedPack] = [load_builtin(CORE_PACK_ID, extra_search_dirs=extra_search_dirs)]

    overlays = routing["risk_overlays"]
    assert isinstance(overlays, list)
    for overlay in overlays:
        pack_id = RISK_OVERLAY_PACK_IDS.get(overlay)
        if pack_id is not None:
            packs.append(load_builtin(pack_id, extra_search_dirs=extra_search_dirs))

    domain_packs = routing["domain_packs"]
    assert isinstance(domain_packs, list)
    for ref in domain_packs:
        assert isinstance(ref, dict)
        pack_id = ref["pack_id"]
        assert isinstance(pack_id, str)
        builtin_id = DOMAIN_PACK_IDS.get(pack_id, pack_id)
        packs.append(load_builtin(builtin_id, extra_search_dirs=extra_search_dirs))

    for path in project_pack_paths or []:
        packs.append(resolve_pack(path, search_dirs=[path.parent, *_builtin_search_dirs()]))

    all_loaded: list[LoadedPack] = []
    for pack in packs:
        all_loaded.extend(flatten(pack))
    return all_loaded
