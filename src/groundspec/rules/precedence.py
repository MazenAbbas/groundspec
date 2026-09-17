"""Deterministic precedence resolution and conflict detection across rule
packs.

Layer precedence (index 0 = highest, never overridden by a lower layer):

    0 core         -- universal invariants, built into this project
    1 risk_overlay -- built-in, selected by the contract's risk overlays
    2 domain       -- software / research / content, etc.
    3 project       -- supplied by a repository, company, or user

("Platform and system safety restrictions" and "explicit authorization
boundaries" sit above all of this and are enforced by the host AI platform
and the contract's own ``routing.authorization`` block, not by rule packs --
see docs/architecture.md.)

Two rules only ever conflict if they share a non-empty ``conflict_key`` and
disagree on ``requirement``. Conflicts are never resolved silently: the
higher-precedence rule wins, but the loser and the reason are both kept on
the returned :class:`RuleSet` for reporting.
"""

from __future__ import annotations

from dataclasses import dataclass

from groundspec.rules.errors import DuplicatePackId
from groundspec.rules.pack_loader import LoadedPack

LAYER_PRECEDENCE: dict[str, int] = {"core": 0, "risk_overlay": 1, "domain": 2, "project": 3}


@dataclass(frozen=True)
class QualifiedRule:
    pack_id: str
    pack_layer: str
    rule: dict[str, object]

    @property
    def rule_id(self) -> str:
        rule_id = self.rule["id"]
        assert isinstance(rule_id, str)
        return rule_id

    @property
    def fq_id(self) -> str:
        return f"{self.pack_id}:{self.rule_id}"


@dataclass(frozen=True)
class PrecedenceConflict:
    conflict_key: str
    winner: QualifiedRule
    losers: list[QualifiedRule]
    explanation: str


@dataclass(frozen=True)
class RuleSet:
    active_rules: list[QualifiedRule]
    conflicts: list[PrecedenceConflict]


def _dedupe_packs(packs: list[LoadedPack]) -> list[LoadedPack]:
    seen: dict[str, LoadedPack] = {}
    for pack in packs:
        prior = seen.get(pack.pack_id)
        if prior is None:
            seen[pack.pack_id] = pack
        elif prior.version != pack.version or prior.rules != pack.rules:
            raise DuplicatePackId(
                f"pack id {pack.pack_id!r} is declared more than once with different content "
                f"(versions {prior.version!r} and {pack.version!r}); rename one of them"
            )
    return list(seen.values())


def build_rule_set(packs: list[LoadedPack]) -> RuleSet:
    """``packs`` should already be given in descending precedence order
    (core packs first, then risk overlays, then domain, then project) --
    that order is what breaks same-layer ties deterministically.
    """
    deduped = _dedupe_packs(packs)

    all_rules: list[QualifiedRule] = []
    for pack in deduped:
        for rule in pack.rules:
            if rule.get("status") == "deprecated":
                continue
            all_rules.append(QualifiedRule(pack_id=pack.pack_id, pack_layer=pack.layer, rule=rule))

    groups: dict[str, list[QualifiedRule]] = {}
    ungrouped: list[QualifiedRule] = []
    for qr in all_rules:
        raw_key = qr.rule.get("conflict_key") or ""
        assert isinstance(raw_key, str)
        key = raw_key
        if key:
            groups.setdefault(key, []).append(qr)
        else:
            ungrouped.append(qr)

    active = list(ungrouped)
    conflicts: list[PrecedenceConflict] = []

    for key, candidates in groups.items():
        requirements = {c.rule["requirement"] for c in candidates}
        if len(requirements) == 1:
            active.extend(candidates)
            continue

        ranked = sorted(
            candidates,
            key=lambda c: (LAYER_PRECEDENCE[c.pack_layer], c.pack_id, c.rule_id),
        )
        winner, *losers = ranked
        active.append(winner)
        same_layer = losers and losers[0].pack_layer == winner.pack_layer
        explanation = (
            f"conflict_key {key!r}: {len(candidates)} rule(s) disagree on 'requirement'. "
            f"{winner.fq_id} (layer={winner.pack_layer}) wins by layer precedence"
            + (
                f"; tie-broken alphabetically among same-layer candidates "
                f"({', '.join(c.fq_id for c in losers if c.pack_layer == winner.pack_layer)})"
                if same_layer
                else ""
            )
            + "."
        )
        conflicts.append(
            PrecedenceConflict(conflict_key=key, winner=winner, losers=losers, explanation=explanation)
        )

    return RuleSet(active_rules=active, conflicts=conflicts)
