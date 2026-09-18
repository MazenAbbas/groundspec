"""Deterministic Domain Pack discovery across the three supported origins.

1. **official** -- shipped inside the ``groundspec`` package itself
   (``src/groundspec/packs/<pack-id>/pack.toml``). Discovered by scanning
   for any immediate subdirectory of the packs root that contains a
   ``pack.toml`` -- adding a new official pack never requires touching this
   module.
2. **project** -- ``<project>/.groundspec/packs/<pack-id>/pack.toml``,
   matching the existing ``.groundspec/`` convention ``cmd_init`` already
   creates (see ``groundspec.cli.commands``).
3. **user** -- ``~/.groundspec/packs/<pack-id>/pack.toml``, checked only if
   that directory exists. Never auto-created, never auto-downloaded.

No remote marketplace, no network access, no scanning of arbitrary parent
directories -- see docs/threat-model.md's pack-extensibility section and
the product spec this module implements.

Shadowing: if more than one origin declares the same ``pack_id``, that is
never silently resolved by picking one -- see
:mod:`groundspec.packs.sdk.resolver`, which is the only place a shadow is
actually accepted (via an explicit ``--allow-shadow`` override) or
rejected. This module just reports what it found, from every origin.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from groundspec.packs.sdk.manifest import MANIFEST_FILENAME

ORIGIN_OFFICIAL = "official"
ORIGIN_PROJECT = "project"
ORIGIN_USER = "user"


@dataclass(frozen=True)
class PackLocation:
    pack_id_hint: str
    """The directory name, used only as a discovery hint -- the pack's real
    ``pack_id`` comes from parsing its manifest, and the two need not match
    on disk if a project pack's directory is named differently."""
    pack_dir: Path
    origin: str


def official_packs_root() -> Path:
    return Path(str(resources.files("groundspec.packs")))


def _scan_for_manifests(root: Path, *, origin: str) -> list[PackLocation]:
    if not root.is_dir():
        return []
    found = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if child.is_dir() and (child / MANIFEST_FILENAME).is_file():
            found.append(PackLocation(pack_id_hint=child.name, pack_dir=child, origin=origin))
    return found


def discover_official() -> list[PackLocation]:
    return _scan_for_manifests(official_packs_root(), origin=ORIGIN_OFFICIAL)


def discover_project(project_root: Path) -> list[PackLocation]:
    return _scan_for_manifests(project_root / ".groundspec" / "packs", origin=ORIGIN_PROJECT)


def discover_user(*, home: Path | None = None) -> list[PackLocation]:
    base = (home or Path.home()) / ".groundspec" / "packs"
    return _scan_for_manifests(base, origin=ORIGIN_USER)


def discover_all(*, project_root: Path | None = None) -> list[PackLocation]:
    """All discovered pack locations, official first, then project, then
    user -- the same order :mod:`groundspec.packs.sdk.resolver` treats as
    ascending shadow-precedence (a later origin may shadow an earlier one,
    but only with an explicit override)."""
    locations = list(discover_official())
    locations.extend(discover_project(project_root or Path.cwd()))
    locations.extend(discover_user())
    return locations
