"""Exception hierarchy for the Domain Pack SDK.

Kept separate from :mod:`groundspec.rules.errors` (the existing single-file
rule-pack loader's exceptions) even though the two overlap conceptually --
the SDK wraps and extends that loader rather than replacing it, and callers
that only ever used the old loader must keep seeing the old exception
types unchanged. See docs/architecture.md's Domain Pack SDK section.
"""

from __future__ import annotations


class PackSdkError(ValueError):
    """Base class for all Domain Pack SDK failures."""


class PackManifestError(PackSdkError):
    """The manifest (pack.toml) itself is invalid."""


class PackNotFoundError(PackSdkError):
    pass


class PackShadowConflictError(PackSdkError):
    """A local/user pack declares the same pack_id as an official pack (or
    another local/user pack) without an explicit override."""


class PackVersionRangeError(PackSdkError):
    """A dependency or conflict version range is impossible (min > max), or
    no available version of a dependency satisfies its declared range."""


class PackDependencyCycleError(PackSdkError):
    pass


class PackCompositionInvalidError(PackSdkError):
    """A requested pack composition can never be resolved (explicit
    conflict between two selected/depended packs, duplicate rule IDs
    across independently-authored packs, etc.)."""


class PackCompositionAmbiguousError(PackSdkError):
    """A requested pack composition has a conflict that deterministic
    precedence cannot resolve (e.g. two same-priority gates disagree) and
    genuinely requires a human decision."""


class PackContentError(PackSdkError):
    """A referenced content file (questions.toml, evidence-policy.toml,
    acceptance-templates.toml, completion-gates.toml, tests/scenarios.toml)
    is malformed."""


class UnsafePackContentError(PackSdkError):
    """A pack directory contains something the threat model forbids:
    an executable file disguised as data, a symlink/junction, a path that
    escapes the pack root, an oversized file, etc."""
