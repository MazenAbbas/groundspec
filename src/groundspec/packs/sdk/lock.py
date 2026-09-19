"""Deterministic ``groundspec.lock`` file: exact pack IDs, versions, content
hashes, and origins for a resolved composition.

Repeated resolution of the same inputs must produce byte-identical lock
content -- this reuses the exact canonical-JSON writer
(``groundspec.contract.serialization.canonical_json_dumps``) that already
guarantees this for Task Contracts, for the same reason: sorted keys, no
timestamps, no absolute host paths (a project/user pack's path is recorded
relative to the project root it was discovered under; an official pack's
"path" is just its symbolic package-relative name -- never a real
filesystem path that would leak local directory structure).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from groundspec.__about__ import DOMAIN_PACK_SCHEMA_VERSION, PACK_PLATFORM_VERSION
from groundspec.contract.serialization import canonical_json_dumps
from groundspec.packs.sdk.discovery import ORIGIN_OFFICIAL
from groundspec.packs.sdk.resolver import ResolutionResult

LOCK_SCHEMA_VERSION = "0.1.0"


def _symbolic_path(pack_dir: Path, *, origin: str, project_root: Path | None) -> str:
    if origin == ORIGIN_OFFICIAL:
        return f"official:{pack_dir.name}"
    root = project_root or Path.cwd()
    try:
        return pack_dir.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        # Outside the project root (e.g. a user pack under the home dir) --
        # record only a symbolic marker, never the real absolute path.
        return f"{origin}:{pack_dir.name}"


def build_lock_document(
    result: ResolutionResult, *, project_root: Path | None = None
) -> dict[str, Any]:
    if not result.ok:
        raise ValueError("cannot lock a resolution with unresolved conflicts")
    return {
        "lock_schema_version": LOCK_SCHEMA_VERSION,
        "domain_pack_schema_version": DOMAIN_PACK_SCHEMA_VERSION,
        "platform_version": PACK_PLATFORM_VERSION,
        "requested": list(result.requested_ids),
        "packs": [
            {
                "pack_id": entry.pack.pack_id,
                "version": entry.pack.version,
                "origin": entry.pack.origin,
                "requested": entry.requested,
                "content_hash": entry.pack.content_hash,
                "source": _symbolic_path(
                    entry.pack.pack_dir, origin=entry.pack.origin, project_root=project_root
                ),
            }
            for entry in result.selected
        ],
    }


def write_lock(result: ResolutionResult, path: Path, *, project_root: Path | None = None) -> str:
    document = build_lock_document(result, project_root=project_root)
    text = canonical_json_dumps(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return text


def read_lock(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data
