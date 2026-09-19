"""Deterministic content hashing for Domain Packs.

Hashes are always computed from the files actually on disk at
resolve/inspect/lock time -- never pre-declared by the pack author in
pack.toml -- so they can never go stale relative to the content they claim
to describe (see docs/architecture.md's Domain Pack SDK section).
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def hash_pack_directory(pack_dir: Path) -> str:
    """A single hash over every file in the pack directory, computed in a
    sorted, path-relative, platform-independent way so the same pack
    content always hashes identically regardless of OS or traversal order.
    """
    hasher = hashlib.sha256()
    for path in sorted(pack_dir.rglob("*"), key=lambda p: p.relative_to(pack_dir).as_posix()):
        if path.is_dir():
            continue
        rel = path.relative_to(pack_dir).as_posix()
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(path.read_bytes())
        hasher.update(b"\x00")
    return f"sha256:{hasher.hexdigest()}"
