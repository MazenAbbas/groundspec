"""Minimal, dependency-free semantic-version parsing and comparison.

Every version string this SDK ever accepts is already schema-constrained to
``^[0-9]+\\.[0-9]+\\.[0-9]+$`` (no pre-release/build metadata) -- see
``domain_pack.v0_1_0.schema.json``. That means comparison is just tuple
comparison of three integers; no third-party semver library is needed, the
same reasoning already applied to this project's TOML writer and schema
validator (see docs/architecture.md's "why there is no X dependency"
sections).
"""

from __future__ import annotations

Version = tuple[int, int, int]


class InvalidVersionError(ValueError):
    pass


def parse(version: str) -> Version:
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise InvalidVersionError(f"not a valid strict semver (X.Y.Z) version: {version!r}")
    major, minor, patch = (int(p) for p in parts)
    return (major, minor, patch)


def in_range(version: str, *, min_version: str, max_version: str | None) -> bool:
    v = parse(version)
    if v < parse(min_version):
        return False
    if max_version is None:
        return True
    return v <= parse(max_version)


def range_is_possible(*, min_version: str, max_version: str | None) -> bool:
    if max_version is None:
        return True
    return parse(min_version) <= parse(max_version)
