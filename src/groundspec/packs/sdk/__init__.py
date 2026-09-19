"""The Domain Pack SDK: manifest schema, discovery, resolution, locking,
scaffolding, and testing for Domain Packs. See docs/architecture.md's
Domain Pack SDK section and docs/pack-authoring-guide.md.
"""

from __future__ import annotations

from groundspec.packs.sdk.discovery import discover_all, discover_official, discover_project, discover_user
from groundspec.packs.sdk.manifest import DomainPack, PackManifest, load_pack
from groundspec.packs.sdk.resolver import ConflictReport, ResolutionResult, resolve

__all__ = [
    "DomainPack",
    "PackManifest",
    "load_pack",
    "discover_all",
    "discover_official",
    "discover_project",
    "discover_user",
    "ConflictReport",
    "ResolutionResult",
    "resolve",
]
