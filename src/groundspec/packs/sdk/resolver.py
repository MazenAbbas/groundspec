"""Deterministic resolution of an explicitly-requested Domain Pack
selection: discovery, dependency closure, version compatibility, conflict
detection and classification, and effective precedence.

The CLI never infers which packs a natural-language request needs -- that
is the Meta-Skill's (model-dependent) job. This module only ever operates
on an explicit list of ``pack_id`` strings the caller supplies, exactly as
the product spec requires: "The AI may recommend and explain pack
selection. The deterministic CLI must validate the selected packs and
their composition."
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from groundspec.__about__ import PACK_PLATFORM_VERSION
from groundspec.packs.sdk import semver
from groundspec.packs.sdk.discovery import (
    ORIGIN_OFFICIAL,
    ORIGIN_PROJECT,
    ORIGIN_USER,
    PackLocation,
    discover_all,
)
from groundspec.packs.sdk.errors import (
    PackCompositionAmbiguousError,
    PackCompositionInvalidError,
    PackDependencyCycleError,
    PackNotFoundError,
    PackVersionRangeError,
)
from groundspec.packs.sdk.manifest import DomainPack, load_pack
from groundspec.rules.pack_loader import LoadedPack

_ORIGIN_SHADOW_PRECEDENCE = {ORIGIN_PROJECT: 0, ORIGIN_USER: 1, ORIGIN_OFFICIAL: 2}
MAX_DEPENDENCY_DEPTH = 8
"""Mirrors the existing single-file rule-pack loader's import-depth
ceiling (groundspec.rules.pack_loader.DEFAULT_MAX_IMPORT_DEPTH) applied to
Domain Pack dependencies -- defense in depth against denial-of-service via
an extremely deep (but acyclic, so cycle detection alone wouldn't catch
it) dependency chain. See docs/threat-model.md."""


@dataclass(frozen=True)
class ConflictReport:
    kind: str
    classification: str  # "resolvable_by_precedence" | "requires_user_decision" | "invalid_composition"
    message: str
    involved_pack_ids: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedEntry:
    pack: DomainPack
    requested: bool


@dataclass(frozen=True)
class ResolutionResult:
    requested_ids: tuple[str, ...]
    selected: tuple[ResolvedEntry, ...]
    conflicts: tuple[ConflictReport, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not any(c.classification != "resolvable_by_precedence" for c in self.conflicts)

    @property
    def rule_packs(self) -> list[LoadedPack]:
        return [entry.pack.rules for entry in self.selected if entry.pack.rules is not None]


def _load_all_candidates(*, project_root: Path | None) -> dict[str, list[tuple[PackLocation, DomainPack]]]:
    """pack_id -> every (location, loaded pack) declaring that id, across
    all origins -- loaded once so shadow detection sees every candidate."""
    by_id: dict[str, list[tuple[PackLocation, DomainPack]]] = {}
    for location in discover_all(project_root=project_root):
        pack = load_pack(location.pack_dir, origin=location.origin)
        by_id.setdefault(pack.pack_id, []).append((location, pack))
    return by_id


def _pick_shadow_winner(candidates: list[tuple[PackLocation, DomainPack]]) -> tuple[PackLocation, DomainPack]:
    return min(candidates, key=lambda pair: _ORIGIN_SHADOW_PRECEDENCE[pair[0].origin])


def resolve(
    requested_ids: list[str],
    *,
    project_root: Path | None = None,
    allow_shadow: frozenset[str] = frozenset(),
) -> ResolutionResult:
    by_id = _load_all_candidates(project_root=project_root)
    conflicts: list[ConflictReport] = []
    selected: dict[str, ResolvedEntry] = {}

    def _resolve_one(pack_id: str, *, requested: bool, stack: tuple[str, ...]) -> None:
        if pack_id in stack:
            cycle = " -> ".join((*stack, pack_id))
            raise PackDependencyCycleError(f"cyclic pack dependency: {cycle}")
        if len(stack) > MAX_DEPENDENCY_DEPTH:
            raise PackDependencyCycleError(
                f"dependency depth exceeded {MAX_DEPENDENCY_DEPTH} while resolving {pack_id!r} "
                f"(chain: {' -> '.join(stack)})"
            )
        if pack_id in selected:
            return
        candidates = by_id.get(pack_id)
        if not candidates:
            raise PackNotFoundError(
                f"no pack named {pack_id!r} found in official, project (.groundspec/packs), "
                "or user (~/.groundspec/packs) locations"
            )
        if len(candidates) > 1:
            origins = tuple(sorted({loc.origin for loc, _ in candidates}))
            if pack_id not in allow_shadow:
                raise PackCompositionInvalidError(
                    f"pack id {pack_id!r} is declared by more than one origin ({', '.join(origins)}); "
                    f"an unofficial pack may never silently shadow another -- pass --allow-shadow {pack_id} "
                    "to explicitly choose one, per the documented precedence (project > user > official)"
                )
            _, pack = _pick_shadow_winner(candidates)
            conflicts.append(
                ConflictReport(
                    kind="shadow",
                    classification="resolvable_by_precedence",
                    message=(
                        f"pack id {pack_id!r} is declared by {', '.join(origins)}; "
                        f"explicitly allowed to shadow -- using the {pack.origin} copy "
                        f"(v{pack.version}, {pack.content_hash})"
                    ),
                    involved_pack_ids=(pack_id,),
                )
            )
        else:
            _, pack = candidates[0]

        if not semver.in_range(
            PACK_PLATFORM_VERSION,
            min_version=pack.manifest.min_platform_version,
            max_version=pack.manifest.max_platform_version,
        ):
            max_pv = pack.manifest.max_platform_version or "unbounded"
            raise PackCompositionInvalidError(
                f"pack {pack_id!r} v{pack.version} requires platform version "
                f"[{pack.manifest.min_platform_version}, {max_pv}], "
                f"this build is platform version {PACK_PLATFORM_VERSION}"
            )

        selected[pack_id] = ResolvedEntry(pack=pack, requested=requested)

        for dep in pack.manifest.dependencies:
            if not semver.range_is_possible(min_version=dep.min_version, max_version=dep.max_version):
                raise PackVersionRangeError(
                    f"pack {pack_id!r} declares an impossible dependency range for {dep.pack_id!r}: "
                    f"min_version {dep.min_version} > max_version {dep.max_version}"
                )
            _resolve_one(dep.pack_id, requested=False, stack=(*stack, pack_id))
            dep_pack = selected[dep.pack_id].pack
            dep_ok = semver.in_range(
                dep_pack.version, min_version=dep.min_version, max_version=dep.max_version
            )
            if not dep_ok:
                raise PackVersionRangeError(
                    f"pack {pack_id!r} requires {dep.pack_id!r} in "
                    f"[{dep.min_version}, {dep.max_version or 'unbounded'}], found v{dep_pack.version}"
                )

    for requested_id in requested_ids:
        _resolve_one(requested_id, requested=True, stack=())

    _check_explicit_conflicts(selected, conflicts)
    _check_cross_pack_rule_id_collisions(selected)
    _check_completion_gate_collisions(selected, conflicts)

    ordered = sorted(selected.values(), key=lambda e: (-e.pack.manifest.priority, e.pack.pack_id))
    return ResolutionResult(
        requested_ids=tuple(requested_ids), selected=tuple(ordered), conflicts=tuple(conflicts)
    )


def _check_explicit_conflicts(selected: dict[str, ResolvedEntry], conflicts: list[ConflictReport]) -> None:
    ids = set(selected)
    for pack_id, entry in selected.items():
        for c in entry.pack.manifest.conflicts:
            if c.pack_id not in ids:
                continue
            other_version = selected[c.pack_id].pack.version
            in_conflict_range = semver.in_range(
                other_version, min_version=c.min_version or "0.0.0", max_version=c.max_version
            )
            if in_conflict_range:
                raise PackCompositionInvalidError(
                    f"pack {pack_id!r} declares an explicit conflict with {c.pack_id!r} ({c.reason}); "
                    "both cannot be selected in the same composition"
                )


def _check_cross_pack_rule_id_collisions(selected: dict[str, ResolvedEntry]) -> None:
    owner_of: dict[str, str] = {}
    for entry in selected.values():
        loaded = entry.pack.rules
        if loaded is None:
            continue
        for rule in loaded.rules:
            rule_id = rule["id"]
            assert isinstance(rule_id, str)
            prior = owner_of.get(rule_id)
            if prior is not None and prior != loaded.pack_id:
                raise PackCompositionInvalidError(
                    f"rule id {rule_id!r} is declared by both {prior!r} and {loaded.pack_id!r} -- "
                    "rule IDs must be unique across an entire composition, not just within one pack"
                )
            owner_of[rule_id] = loaded.pack_id


def _gate_signature(condition: object, on_violation: str) -> str:
    """A hashable, order-independent fingerprint of a gate's behavior, so
    two gates can be compared for equality even though ``condition`` is an
    arbitrarily-nested dict (unhashable, and dict equality already ignores
    key order, which is exactly the comparison we want)."""
    return json.dumps({"condition": condition, "on_violation": on_violation}, sort_keys=True)


def _check_completion_gate_collisions(
    selected: dict[str, ResolvedEntry], conflicts: list[ConflictReport]
) -> None:
    by_gate_id: dict[str, list[tuple[str, int, str]]] = {}
    for entry in selected.values():
        for gate in entry.pack.completion_gates:
            by_gate_id.setdefault(gate.id, []).append(
                (
                    entry.pack.pack_id,
                    entry.pack.manifest.priority,
                    _gate_signature(gate.condition, gate.on_violation),
                )
            )
    for gate_id, contributors in by_gate_id.items():
        distinct = {c[2] for c in contributors}
        if len(distinct) <= 1:
            continue
        ranked = sorted(contributors, key=lambda c: (-c[1], c[0]))
        top_priority = ranked[0][1]
        tied_at_top = [c for c in ranked if c[1] == top_priority]
        if len(tied_at_top) > 1 and len({c[2] for c in tied_at_top}) > 1:
            raise PackCompositionAmbiguousError(
                f"completion gate {gate_id!r} is declared differently by "
                f"{', '.join(c[0] for c in tied_at_top)} with no priority to break the tie -- "
                "give one pack a higher `priority` in pack.toml, or drop the gate from one of them"
            )
        conflicts.append(
            ConflictReport(
                kind="completion_gate_collision",
                classification="resolvable_by_precedence",
                message=(
                    f"completion gate {gate_id!r}: {len(contributors)} pack(s) disagree; "
                    f"{ranked[0][0]!r} wins by priority ({top_priority})"
                ),
                involved_pack_ids=tuple(sorted({c[0] for c in contributors})),
            )
        )
