"""Deterministic, non-executing safety checks over a Domain Pack directory.

A pack is untrusted input until validated (see docs/threat-model.md's
pack-extensibility section). This module never runs, imports, or interprets
anything found in a pack -- it only inspects file names, sizes, link types,
and byte content for known-forbidden patterns, exactly the same posture the
existing single-file rule-pack loader already has (see
``groundspec.rules.pack_loader``'s module docstring).

Residual risk, stated honestly: this is a content *classifier*, not a
sandbox. It cannot prove a `.md`/`.toml` file's prose is harmless (e.g. a
prompt-injection attempt inside ``references/*.md``, which
``execution-and-verification.md``'s "untrusted content is data, not
instructions" rule -- not this module -- is what actually defends against).
It only prevents the pack *directory itself* from containing something that
could execute, escape its own root, or exhaust resources.
"""

from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from groundspec.packs.sdk.errors import UnsafePackContentError

MAX_FILE_BYTES = 1_000_000
MAX_PACK_TOTAL_BYTES = 8_000_000
MAX_FILES_PER_PACK = 200
MAX_PATH_DEPTH = 8

_FORBIDDEN_SUFFIXES = frozenset(
    {
        ".py", ".pyc", ".pyo", ".pyd", ".sh", ".bash", ".zsh", ".ps1", ".psm1",
        ".bat", ".cmd", ".exe", ".dll", ".so", ".dylib", ".jar", ".class",
        ".wasm", ".app", ".msi", ".deb", ".rpm", ".vbs", ".js", ".mjs", ".cjs",
        ".ts", ".php", ".rb", ".pl", ".jsp", ".apk", ".scpt", ".workflow",
    }
)
_ALLOWED_SUFFIXES = frozenset({".toml", ".md", ".json"})

# Control characters and bidi-override characters that could make a
# filename or identifier render differently than it actually is.
_SUSPICIOUS_UNICODE_CATEGORIES = frozenset({"Cc", "Cf"})


@dataclass(frozen=True)
class SafetyReport:
    file_count: int
    total_bytes: int
    checked_paths: tuple[str, ...]


def _relative_depth(root: Path, path: Path) -> int:
    return len(path.relative_to(root).parts)


def scan_pack_directory(pack_dir: Path) -> SafetyReport:
    """Raise :class:`UnsafePackContentError` on the first forbidden thing
    found; otherwise return a small report. Deterministic: iterates paths
    in sorted order so the *first* violation reported is stable across
    platforms and runs.
    """
    if not pack_dir.is_dir():
        raise UnsafePackContentError(f"{pack_dir} is not a directory")

    resolved_root = pack_dir.resolve()
    all_paths = sorted(pack_dir.rglob("*"), key=lambda p: p.as_posix())

    file_count = 0
    total_bytes = 0
    checked: list[str] = []

    for path in all_paths:
        rel = path.relative_to(pack_dir)
        rel_posix = rel.as_posix()

        _check_no_traversal(pack_dir, path, resolved_root)

        if path.is_symlink():
            raise UnsafePackContentError(
                f"{rel_posix}: symlinks/junctions are not permitted inside a pack directory"
            )

        _check_identifier_chars(rel_posix)

        if _relative_depth(pack_dir, path) > MAX_PATH_DEPTH:
            raise UnsafePackContentError(
                f"{rel_posix}: exceeds max pack directory depth ({MAX_PATH_DEPTH})"
            )
        if path.is_dir():
            continue

        suffix = path.suffix.lower()
        if suffix in _FORBIDDEN_SUFFIXES:
            raise UnsafePackContentError(
                f"{rel_posix}: executable/script file extension {suffix!r} is never permitted in a pack "
                "(a pack is declarative data, not code -- see docs/pack-authoring-guide.md)"
            )
        if suffix not in _ALLOWED_SUFFIXES:
            raise UnsafePackContentError(
                f"{rel_posix}: file extension {suffix!r} is not one of the allowed pack content types "
                f"({', '.join(sorted(_ALLOWED_SUFFIXES))})"
            )

        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise UnsafePackContentError(
                f"{rel_posix}: {size} bytes exceeds the per-file limit ({MAX_FILE_BYTES})"
            )

        _check_no_shebang_or_magic_bytes(path, rel_posix)

        file_count += 1
        total_bytes += size
        checked.append(rel_posix)

        if file_count > MAX_FILES_PER_PACK:
            raise UnsafePackContentError(f"pack exceeds the maximum file count ({MAX_FILES_PER_PACK})")
        if total_bytes > MAX_PACK_TOTAL_BYTES:
            raise UnsafePackContentError(
                f"pack exceeds the maximum total size ({MAX_PACK_TOTAL_BYTES} bytes)"
            )

    return SafetyReport(file_count=file_count, total_bytes=total_bytes, checked_paths=tuple(checked))


def _check_no_traversal(pack_dir: Path, path: Path, resolved_root: Path) -> None:
    try:
        resolved = path.resolve()
    except OSError as exc:  # pragma: no cover - defensive
        raise UnsafePackContentError(f"could not resolve path under {pack_dir}: {exc}") from exc
    if os.path.commonpath([str(resolved), str(resolved_root)]) != str(resolved_root):
        raise UnsafePackContentError(
            f"{path} resolves outside its own pack directory ({resolved_root}) -- "
            "path traversal is not permitted"
        )


def _check_identifier_chars(rel_posix: str) -> None:
    for ch in rel_posix:
        if ch in ("/",):
            continue
        category = unicodedata.category(ch)
        if category in _SUSPICIOUS_UNICODE_CATEGORIES:
            raise UnsafePackContentError(
                f"{rel_posix}: contains a control or bidi-override character (category {category}), "
                "which is never permitted in a pack path"
            )


def _check_no_shebang_or_magic_bytes(path: Path, rel_posix: str) -> None:
    """Even an allowed extension (.toml/.md/.json) is rejected if it starts
    with a shebang or a known native-executable magic number -- defense in
    depth against an executable disguised with a data extension."""
    try:
        with path.open("rb") as fh:
            head = fh.read(4)
    except OSError as exc:  # pragma: no cover - defensive
        raise UnsafePackContentError(f"{rel_posix}: could not read file: {exc}") from exc
    if head[:2] == b"#!":
        raise UnsafePackContentError(f"{rel_posix}: begins with a shebang line, which is never permitted")
    if head[:2] == b"MZ" or head[:4] == b"\x7fELF":
        raise UnsafePackContentError(f"{rel_posix}: begins with a native-executable magic number")
    if head[:4] == b"PK\x03\x04":
        raise UnsafePackContentError(
            f"{rel_posix}: begins with a zip/archive magic number, which is not a pack content type"
        )
