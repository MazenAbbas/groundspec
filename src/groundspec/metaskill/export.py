"""Safe, atomic, deterministic multi-file export to a destination directory.

Used by ``groundspec skill export`` to write a rendered Meta-Skill (or, in
principle, any other in-memory file set) to disk without ever silently
overwriting a user's existing files, writing through a symlink to an
unintended location, or leaving a half-written directory behind if
interrupted partway through.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class ExportError(ValueError):
    pass


class DestinationExists(ExportError):
    pass


class UnsafeDestination(ExportError):
    pass


class UnsafeRelativePath(ExportError):
    pass


@dataclass(frozen=True)
class ManifestEntry:
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class ExportResult:
    destination: Path
    files: tuple[ManifestEntry, ...]


def _validate_relative_path(rel: str) -> None:
    """Defense in depth: reject anything that could escape the destination,
    even though every caller in this codebase supplies these paths from its
    own authored content, never from untrusted input."""
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts or not rel or rel != rel.strip():
        raise UnsafeRelativePath(f"unsafe relative path in file set: {rel!r}")
    for part in pure.parts:
        if part in ("", ".", ".."):
            raise UnsafeRelativePath(f"unsafe path segment in {rel!r}")


def _refuse_if_symlink(path: Path) -> None:
    """Refuse to write through a symlink or (on Windows) a junction /
    reparse point at the destination itself or its immediate parent. This
    does not walk the full ancestor chain -- see docs/threat-model.md for
    the documented scope of this check."""
    for candidate in (path, path.parent):
        try:
            if candidate.is_symlink():
                raise UnsafeDestination(
                    f"refusing to write through a symlink/reparse point at {candidate}"
                )
        except OSError:
            # Path does not exist yet (or a parent doesn't) -- nothing to
            # refuse; created fresh below.
            continue


def export_file_set(
    files: dict[str, str],
    destination: Path,
    *,
    force: bool = False,
) -> ExportResult:
    """Write ``files`` (relative POSIX path -> text content) into
    ``destination`` as a single atomic operation.

    Raises :class:`DestinationExists` if ``destination`` already exists and
    ``force`` is false. Raises :class:`UnsafeDestination` if writing would
    go through a symlink. Never partially writes ``destination`` on the
    caller's happy path: files are staged in a temporary sibling directory
    on the same filesystem, then moved into place with a single rename.
    """
    for rel in files:
        _validate_relative_path(rel)

    # Deliberately not .resolve()'d: resolving would follow a symlink and
    # then check the *target's* symlink-ness (always false), defeating the
    # whole point of the check below.
    destination = destination.absolute()
    _refuse_if_symlink(destination)

    if destination.exists() and not force:
        raise DestinationExists(f"{destination} already exists; pass force=True (--force) to overwrite")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent))
    try:
        manifest = []
        for rel, content in sorted(files.items()):
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            data = content.encode("utf-8")
            target.write_bytes(data)
            manifest.append(
                ManifestEntry(relative_path=rel, sha256=hashlib.sha256(data).hexdigest(), size=len(data))
            )

        if destination.exists():
            if not force:
                raise DestinationExists(f"{destination} already exists; pass --force to overwrite")
            backup = staging.parent / f".{destination.name}.replaced-{os.getpid()}"
            os.replace(destination, backup)
            try:
                os.replace(staging, destination)
            except OSError:
                os.replace(backup, destination)
                raise
            else:
                shutil.rmtree(backup, ignore_errors=True)
        else:
            os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return ExportResult(destination=destination, files=tuple(manifest))
