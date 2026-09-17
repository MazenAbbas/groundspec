"""Deterministic completion-state derivation for the Meta-Skill's final report.

The whole point of this module is that a task can never be reported as
``PASS`` just because an AI produced confident-sounding text. ``PASS``
requires actual structured evidence: every 'must' acceptance criterion has
a recorded true/false result, every applicable hard constraint passed, and
no blocking question is still open. This mirrors, and is used alongside,
the existing hard-constraint-beats-soft-score discipline in
:mod:`groundspec.scoring.rubric` -- soft-objective scores never gate this
state either, for the same reason: they are improvable quality signals,
not completion gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CompletionState = Literal["PASS", "PASS_WITH_CAVEATS", "FAIL", "INCOMPLETE", "BLOCKED"]

_VALID_STATES: frozenset[str] = frozenset({"PASS", "PASS_WITH_CAVEATS", "FAIL", "INCOMPLETE", "BLOCKED"})


@dataclass(frozen=True)
class AcceptanceEvaluation:
    must_criteria_met: bool | None
    """None means at least one 'must' criterion has no recorded result --
    there is not enough evidence to call this either met or unmet."""
    unmet_must_ids: list[str]
    missing_evidence_ids: list[str]


def evaluate_acceptance_criteria(
    criteria: list[dict[str, object]],
    results: dict[str, bool],
) -> AcceptanceEvaluation:
    """``criteria`` is a contract's ``acceptance.criteria`` list. ``results``
    maps criterion id -> whether it was actually verified met, supplied by
    whoever collected the evidence (human or AI Skill) -- never inferred
    here."""
    must_ids = [
        str(c["id"]) for c in criteria if c.get("priority", "must") == "must"
    ]
    missing = [cid for cid in must_ids if cid not in results]
    if missing:
        return AcceptanceEvaluation(must_criteria_met=None, unmet_must_ids=[], missing_evidence_ids=missing)
    unmet = [cid for cid in must_ids if not results[cid]]
    return AcceptanceEvaluation(
        must_criteria_met=(len(unmet) == 0), unmet_must_ids=unmet, missing_evidence_ids=[]
    )


def derive_completion_state(
    *,
    hard_constraints_passed: bool,
    has_unresolved_blocking_questions: bool,
    budget_expired: bool,
    acceptance_criteria_met: bool | None,
) -> CompletionState:
    """Pure function: identical inputs always produce the identical state.

    Priority order, highest first:
      1. An unresolved blocking question means no useful verification can
         have happened yet -- BLOCKED, regardless of everything else.
      2. A failed hard constraint is disqualifying -- FAIL, regardless of
         acceptance criteria or budget.
      3. No recorded result for some 'must' criterion -- INCOMPLETE: this
         is a *missing-evidence* state, deliberately distinct from FAIL.
      4. An unmet 'must' criterion -- FAIL.
      5. Every 'must' criterion met: PASS, or PASS_WITH_CAVEATS if the
         budget ran out along the way (see module docstring: budget
         pressure always downgrades a PASS, even if the criteria that
         were actually checked all passed, because time pressure is a
         standing reason to distrust unexplored edge cases).
    """
    if has_unresolved_blocking_questions:
        return "BLOCKED"
    if not hard_constraints_passed:
        return "FAIL"
    if acceptance_criteria_met is None:
        return "INCOMPLETE"
    if acceptance_criteria_met is False:
        return "FAIL"
    return "PASS_WITH_CAVEATS" if budget_expired else "PASS"
