"""Budget arithmetic and graceful-degradation reporting (see PRD Phase 6).

This module only does arithmetic and produces structured reports. It has no
opinion on *what* work to cut when a budget is tight -- that is a planning
decision for the AI Skill, guided by the fixed priority order documented in
:data:`DEGRADATION_PRIORITY`. What this module guarantees is that the
bookkeeping is honest: you cannot ask it whether verification was skipped
without it telling you, and a completed-with-expired-budget contract can
never silently claim full completion (see
:func:`forbid_silent_skip_on_expiry`, enforced by the ``core`` rule pack and
the ``audit``/``evaluate`` CLI commands).
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEGRADATION_PRIORITY = (
    "protect_safety_and_hard_constraints",
    "preserve_core_deliverable",
    "reduce_optional_depth",
    "report_omitted_work_explicitly",
    "never_skip_required_verification_silently",
    "return_incomplete_rather_than_pretend_completion",
)


@dataclass(frozen=True)
class Usage:
    time_minutes_used: float = 0.0
    clarification_questions_used: int = 0
    planning_iterations_used: int = 0
    execution_iterations_used: int = 0
    tool_calls_used: int = 0


@dataclass(frozen=True)
class DimensionStatus:
    dimension: str
    limit: float
    used: float

    @property
    def remaining(self) -> float:
        return max(0.0, self.limit - self.used)

    @property
    def exceeded(self) -> bool:
        return self.used > self.limit


def check_budget(contract_budget: dict[str, object], usage: Usage) -> list[DimensionStatus]:
    pairs = (
        ("time_minutes", contract_budget["time_budget_minutes"], usage.time_minutes_used),
        (
            "clarification_questions",
            contract_budget["max_clarification_questions"],
            usage.clarification_questions_used,
        ),
        (
            "planning_iterations",
            contract_budget["max_planning_iterations"],
            usage.planning_iterations_used,
        ),
        (
            "execution_iterations",
            contract_budget["max_execution_iterations"],
            usage.execution_iterations_used,
        ),
        ("tool_calls", contract_budget["tool_call_budget"], usage.tool_calls_used),
    )
    statuses = []
    for name, limit, used in pairs:
        assert isinstance(limit, (int, float))
        statuses.append(DimensionStatus(dimension=name, limit=float(limit), used=float(used)))
    return statuses


def verification_reserve_minutes(contract_budget: dict[str, object]) -> float:
    total = contract_budget["time_budget_minutes"]
    fraction = contract_budget["reserved_verification_fraction"]
    assert isinstance(total, (int, float)) and isinstance(fraction, (int, float))
    return float(total) * float(fraction)


def verification_reserve_intact(contract_budget: dict[str, object], usage: Usage) -> bool:
    total = contract_budget["time_budget_minutes"]
    assert isinstance(total, (int, float))
    remaining = float(total) - usage.time_minutes_used
    return remaining >= verification_reserve_minutes(contract_budget)


def any_dimension_exhausted(statuses: list[DimensionStatus]) -> bool:
    return any(s.exceeded for s in statuses)


@dataclass(frozen=True)
class DegradationReport:
    work_completed: list[str] = field(default_factory=list)
    work_omitted: list[str] = field(default_factory=list)
    verification_performed: list[str] = field(default_factory=list)
    verification_skipped: list[str] = field(default_factory=list)
    risks_introduced: list[str] = field(default_factory=list)
    recommended_next_action: str = ""

    def is_honest_about_expiry(self) -> bool:
        """A degradation report is dishonest if it claims nothing was
        omitted/skipped while also recommending nothing further -- that
        combination means the caller forgot to fill it in, not that the
        task genuinely finished clean (use plain completion, not a
        degradation report, for that case)."""
        if not self.work_omitted and not self.verification_skipped:
            return bool(self.recommended_next_action) is False
        return True


def forbid_silent_skip_on_expiry(status: dict[str, object]) -> list[str]:
    """Hard-constraint check: budget expiry may never be paired with a
    claimed-complete status. Returns violation messages (empty = OK)."""
    violations = []
    if status.get("budget_expired") is True and status.get("completion_status") == "complete":
        violations.append(
            "status.budget_expired is true but status.completion_status is 'complete': "
            "a budget that ran out cannot silently claim full completion. "
            "Use 'partial' or 'blocked' and list the omission in status.omitted_work."
        )
    return violations
