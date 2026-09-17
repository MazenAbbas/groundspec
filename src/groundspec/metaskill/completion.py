"""Deterministic completion-state derivation for the Meta-Skill's final report.

The whole point of this module is that a task can never be reported as
``PASS`` just because an AI produced confident-sounding text. ``PASS``
requires actual structured evidence: every 'must' acceptance criterion has
a recorded true/false result *backed by evidence adequate to that
criterion's own declared verification method*, every applicable hard
constraint passed, no explicit authorization boundary was violated, no
open, unresolved critical risk undermines the deliverable's validity, and
no blocking question is still open. This mirrors, and is used alongside,
the existing hard-constraint-beats-soft-score discipline in
:mod:`groundspec.scoring.rubric` -- soft-objective scores never gate this
state either, for the same reason: they are improvable quality signals,
not completion gates.

Hardened in schema/behavior revision 0.3.0 after a live user test of
v0.2.0rc1 found ``PASS`` reported despite an unresolved critical risk,
model-self-evaluated 'must' criteria, and an authorization-boundary
violation -- see docs/threat-model.md and CHANGELOG.md's [0.2.0rc2] entry
for the full account.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CompletionState = Literal["PASS", "PASS_WITH_CAVEATS", "FAIL", "INCOMPLETE", "BLOCKED"]

_VALID_STATES: frozenset[str] = frozenset({"PASS", "PASS_WITH_CAVEATS", "FAIL", "INCOMPLETE", "BLOCKED"})

# Evidence labels that do NOT constitute independent/deterministic
# verification. A 'must' criterion whose declared verification_method
# demands real evidence (automated_test, reproducible_command,
# static_analysis, external_reference_check) may not be satisfied by one
# of these alone.
_WEAK_EVIDENCE_LABELS: frozenset[str] = frozenset(
    {"MODEL-EVALUATED", "MODEL_EVALUATED", "PROPOSED", "ASSUMPTION", "RESEARCH_NEEDED"}
)
_METHODS_REQUIRING_STRONG_EVIDENCE: frozenset[str] = frozenset(
    {"automated_test", "reproducible_command", "static_analysis", "external_reference_check"}
)


@dataclass(frozen=True)
class AcceptanceEvaluation:
    must_criteria_met: bool | None
    """None means at least one 'must' criterion has no recorded result, or
    at least one has only weak/inadequate evidence where its own
    verification_method demanded strong evidence -- either way, there is
    not enough evidence to call this either met or unmet."""
    unmet_must_ids: list[str]
    missing_evidence_ids: list[str]
    inadequate_evidence_ids: list[str] = field(default_factory=list)


def evaluate_acceptance_criteria(
    criteria: list[dict[str, object]],
    results: dict[str, object],
) -> AcceptanceEvaluation:
    """``criteria`` is a contract's ``acceptance.criteria`` list. ``results``
    maps criterion id to either:

    - a plain ``bool`` (legacy shape, unchanged since v0.1.0rc1: whether it
      was verified met, with no evidence-strength information); or
    - ``{"met": bool, "evidence_label": str}`` (new: also states what kind
      of evidence backs the result, so a criterion whose verification_method
      demands real evidence cannot be satisfied by a bare self-review).

    Never inferred here -- both shapes are supplied by whoever collected
    the evidence (human or AI Skill).
    """
    criteria_by_id = {str(c["id"]): c for c in criteria}
    must_ids = [cid for cid, c in criteria_by_id.items() if c.get("priority", "must") == "must"]

    missing = [cid for cid in must_ids if cid not in results]
    if missing:
        return AcceptanceEvaluation(
            must_criteria_met=None, unmet_must_ids=[], missing_evidence_ids=missing
        )

    unmet: list[str] = []
    inadequate: list[str] = []
    for cid in must_ids:
        entry = results[cid]
        if isinstance(entry, bool):
            met, label = entry, None
        else:
            assert isinstance(entry, dict)
            met, label = bool(entry.get("met", False)), entry.get("evidence_label")

        if not met:
            unmet.append(cid)
            continue

        verification_method = criteria_by_id[cid].get("verification_method")
        if (
            label is not None
            and verification_method in _METHODS_REQUIRING_STRONG_EVIDENCE
            and label in _WEAK_EVIDENCE_LABELS
        ):
            inadequate.append(cid)

    if inadequate:
        return AcceptanceEvaluation(
            must_criteria_met=None,
            unmet_must_ids=unmet,
            missing_evidence_ids=[],
            inadequate_evidence_ids=inadequate,
        )
    return AcceptanceEvaluation(
        must_criteria_met=(len(unmet) == 0), unmet_must_ids=unmet, missing_evidence_ids=[]
    )


def residual_risk_blocks_completion(residual_risks: list[dict[str, object]]) -> bool:
    """True if any residual risk is both severity 'critical' and marked (or,
    absent the field, defaulted -- see the 0.3.0 schema's
    residual_risk.affects_deliverable_validity, default True) as affecting
    the deliverable's own validity, as opposed to being a legitimate
    finding the requested exploration was asked to produce."""
    return any(
        risk.get("severity") == "critical" and bool(risk.get("affects_deliverable_validity", True))
        for risk in residual_risks
    )


def has_deferred_high_value_open_questions(open_questions: list[dict[str, object]]) -> bool:
    """True if any open question is classified 'high_value' and was not
    actually answered by the user -- whether it was given a disclosed
    default (resolution_status 'defaulted') or left fully open with no
    default attempted at all ('open'; note a 'high_value' item left
    'open' does not reach BLOCKED, since only 'blocking' does -- this is
    what keeps it from being silently dropped instead).

    A disclosed default under budget pressure is the *documented*,
    correct behavior (see clarification-policy.md) -- but it still means
    the deliverable rests on an unconfirmed, materially outcome-changing
    judgment call, which is exactly what downgrades an otherwise-clean
    result to PASS_WITH_CAVEATS instead of a plain PASS."""
    return any(
        q.get("classification") == "high_value" and q.get("resolution_status") != "answered"
        for q in open_questions
    )


def derive_completion_state(
    *,
    hard_constraints_passed: bool,
    has_unresolved_blocking_questions: bool,
    budget_expired: bool,
    acceptance_criteria_met: bool | None,
    authorization_boundary_violated: bool = False,
    unresolved_critical_risk_to_validity: bool = False,
    has_deferred_high_value_items: bool = False,
) -> CompletionState:
    """Pure function: identical inputs always produce the identical state.

    Priority order, highest first:
      1. An unresolved blocking question means no useful verification can
         have happened yet -- BLOCKED, regardless of everything else.
      2. An explicit authorization boundary was violated -- FAIL. This is
         disqualifying on its own regardless of how good the rest of the
         work is: doing something the user explicitly prohibited is a
         defect in the run, not a quality issue to caveat around.
      3. A failed hard constraint is disqualifying -- FAIL.
      4. No recorded result for some 'must' criterion, or a 'must'
         criterion's only evidence was inadequate for its own declared
         verification method (see evaluate_acceptance_criteria) --
         INCOMPLETE: a *missing/inadequate-evidence* state, deliberately
         distinct from FAIL (not proven wrong, just not proven).
      5. An unmet 'must' criterion -- FAIL.
      6. An unresolved critical risk that affects the deliverable's own
         validity -- FAIL (see residual_risk_blocks_completion). A critical
         risk that is itself a legitimate finding the exploration was asked
         to produce does NOT reach this function as True -- see that
         helper's docstring; this deliberately does not auto-fail every
         critical finding, only ones marked as undermining validity.
      7. Every 'must' criterion met, no violation, no blocking risk: PASS,
         or PASS_WITH_CAVEATS if the budget ran out along the way (budget
         pressure always downgrades a PASS, because time pressure is a
         standing reason to distrust unexplored edge cases) *or* if any
         high-value clarification item was deferred/defaulted rather than
         actually confirmed by the user (see has_deferred_high_value_items):
         a disclosed, responsible default is not a defect, but a deliverable
         resting on several unconfirmed material judgment calls is not a
         plain, unqualified PASS either -- two independent live runs of
         this exact policy reached PASS with six such defaults apiece
         before this gate existed, which is the reason it does now.
    """
    if has_unresolved_blocking_questions:
        return "BLOCKED"
    if authorization_boundary_violated:
        return "FAIL"
    if not hard_constraints_passed:
        return "FAIL"
    if acceptance_criteria_met is None:
        return "INCOMPLETE"
    if acceptance_criteria_met is False:
        return "FAIL"
    if unresolved_critical_risk_to_validity:
        return "FAIL"
    if budget_expired or has_deferred_high_value_items:
        return "PASS_WITH_CAVEATS"
    return "PASS"
