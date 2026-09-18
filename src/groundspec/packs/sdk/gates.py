"""Evaluates Domain-Pack-provided completion gates and composes their
result with the core completion state.

This is the one documented extension point through which a Domain Pack
can actually influence ``PASS``/``PASS_WITH_CAVEATS``/``INCOMPLETE``/``FAIL``
without any code of its own running: a gate is a condition (the same safe,
non-executable DSL rules already use, see ``groundspec.rules.condition``)
evaluated against ``{"contract": <task contract>, "evidence": <evidence.json>}``,
plus a fixed, enumerated action. ``derive_completion_state`` itself
(``groundspec.metaskill.completion``) is never modified or monkey-patched --
this module only ever *downgrades* its output, mirroring the same
"a lower layer can narrow but never broaden" rule that governs pack rules
generally (see docs/architecture.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from groundspec.metaskill.completion import CompletionState
from groundspec.packs.sdk.content import CompletionGate
from groundspec.rules.condition import evaluate as evaluate_condition

_SEVERITY_RANK: dict[str, int] = {
    "PASS": 0,
    "PASS_WITH_CAVEATS": 1,
    "INCOMPLETE": 2,
    "FAIL": 2,
    "BLOCKED": 3,
}
_ACTION_TO_STATE: dict[str, CompletionState] = {
    "downgrade_to_caveats": "PASS_WITH_CAVEATS",
    "downgrade_to_incomplete": "INCOMPLETE",
    "downgrade_to_fail": "FAIL",
}


@dataclass(frozen=True)
class TriggeredGate:
    pack_id: str
    gate_id: str
    description: str
    on_violation: str
    rationale: str


def evaluate_gates(
    gates: list[tuple[str, CompletionGate]],
    *,
    contract: dict[str, object],
    evidence: dict[str, object],
) -> list[TriggeredGate]:
    view = {"contract": contract, "evidence": evidence}
    triggered = []
    for pack_id, gate in gates:
        if evaluate_condition(gate.condition, view):
            triggered.append(
                TriggeredGate(
                    pack_id=pack_id,
                    gate_id=gate.id,
                    description=gate.description,
                    on_violation=gate.on_violation,
                    rationale=gate.rationale,
                )
            )
    return triggered


def apply_pack_gates(base_state: CompletionState, triggered: list[TriggeredGate]) -> CompletionState:
    """Never returns a state *less* severe than ``base_state`` -- a pack
    gate can only push completion further from PASS, exactly like every
    other pack-provided rule in this project (see the module docstring)."""
    if base_state == "BLOCKED":
        return base_state  # nothing outranks an unresolved blocking question
    worst: CompletionState = base_state
    for gate in triggered:
        candidate = _ACTION_TO_STATE[gate.on_violation]
        if _SEVERITY_RANK[candidate] > _SEVERITY_RANK[worst]:
            worst = candidate
    return worst
