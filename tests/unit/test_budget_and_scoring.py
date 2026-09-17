import pytest

from groundspec.budget.model import (
    Usage,
    any_dimension_exhausted,
    check_budget,
    forbid_silent_skip_on_expiry,
    verification_reserve_intact,
    verification_reserve_minutes,
)
from groundspec.scoring.rubric import DuplicateDimension, score

BUDGET = {
    "time_budget_minutes": 100,
    "max_clarification_questions": 3,
    "max_planning_iterations": 5,
    "max_execution_iterations": 10,
    "tool_call_budget": 50,
    "research_depth": "standard",
    "reserved_verification_fraction": 0.2,
}


def test_check_budget_reports_remaining_and_exceeded():
    usage = Usage(time_minutes_used=90, tool_calls_used=51)
    statuses = check_budget(BUDGET, usage)
    by_dim = {s.dimension: s for s in statuses}
    assert by_dim["time_minutes"].remaining == 10
    assert by_dim["tool_calls"].exceeded is True
    assert by_dim["planning_iterations"].exceeded is False
    assert any_dimension_exhausted(statuses) is True


def test_zero_budget_is_immediately_exhausted():
    zero_budget = {**BUDGET, "time_budget_minutes": 0}
    statuses = check_budget(zero_budget, Usage(time_minutes_used=0))
    time_status = next(s for s in statuses if s.dimension == "time_minutes")
    assert time_status.remaining == 0
    assert time_status.exceeded is False  # 0 used > 0 limit is False; exhausted, not overrun


def test_verification_reserve():
    assert verification_reserve_minutes(BUDGET) == 20
    assert verification_reserve_intact(BUDGET, Usage(time_minutes_used=79)) is True
    assert verification_reserve_intact(BUDGET, Usage(time_minutes_used=81)) is False


def test_forbid_silent_skip_on_expiry():
    ok_status = {"budget_expired": True, "completion_status": "partial"}
    bad_status = {"budget_expired": True, "completion_status": "complete"}
    assert forbid_silent_skip_on_expiry(ok_status) == []
    assert len(forbid_silent_skip_on_expiry(bad_status)) == 1


SOFT_OBJECTIVES = [
    {"dimension": "correctness", "weight": 0.6},
    {"dimension": "clarity", "weight": 0.4},
]


def test_hard_constraint_failure_beats_any_soft_score():
    result = score(
        soft_objectives=SOFT_OBJECTIVES,
        hard_constraint_results={"hc1": False},
        dimension_scores={"correctness": 1.0, "clarity": 1.0},
    )
    assert result.verdict == "fail_hard_constraint"
    assert result.weighted_total is None


def test_weighted_score_when_all_dimensions_scored():
    result = score(
        soft_objectives=SOFT_OBJECTIVES,
        hard_constraint_results={"hc1": True},
        dimension_scores={"correctness": 1.0, "clarity": 0.5},
    )
    assert result.verdict == "scored"
    assert result.weighted_total == pytest.approx(0.6 * 1.0 + 0.4 * 0.5)


def test_insufficient_evidence_dimension_excluded_from_denominator():
    result = score(
        soft_objectives=SOFT_OBJECTIVES,
        hard_constraint_results={},
        dimension_scores={"correctness": 0.8, "clarity": None},
    )
    assert result.insufficient_dimensions == ["clarity"]
    assert result.weighted_total == pytest.approx(0.8)


def test_all_dimensions_insufficient_yields_no_score():
    result = score(
        soft_objectives=SOFT_OBJECTIVES,
        hard_constraint_results={},
        dimension_scores={},
    )
    assert result.verdict == "insufficient_evidence"
    assert result.weighted_total is None
    assert set(result.insufficient_dimensions) == {"correctness", "clarity"}


def test_duplicate_dimension_rejected():
    with pytest.raises(DuplicateDimension):
        score(
            soft_objectives=[
                {"dimension": "correctness", "weight": 0.5},
                {"dimension": "correctness", "weight": 0.5},
            ],
            hard_constraint_results={},
            dimension_scores={"correctness": 1.0},
        )


def test_subjective_labeling():
    result = score(
        soft_objectives=SOFT_OBJECTIVES,
        hard_constraint_results={},
        dimension_scores={"correctness": 1.0, "clarity": 1.0},
    )
    by_dim = {d.dimension: d for d in result.dimension_scores}
    assert by_dim["correctness"].subjective is False
    assert by_dim["clarity"].subjective is True
