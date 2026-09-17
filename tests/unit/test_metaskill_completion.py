import pytest

from groundspec.metaskill.completion import (
    derive_completion_state,
    evaluate_acceptance_criteria,
)

CRITERIA = [
    {"id": "c1", "priority": "must"},
    {"id": "c2", "priority": "must"},
    {"id": "c3", "priority": "should"},
]


def test_acceptance_all_must_met():
    result = evaluate_acceptance_criteria(CRITERIA, {"c1": True, "c2": True})
    assert result.must_criteria_met is True
    assert result.unmet_must_ids == []
    assert result.missing_evidence_ids == []


def test_acceptance_should_criteria_do_not_affect_must_result():
    result = evaluate_acceptance_criteria(CRITERIA, {"c1": True, "c2": True, "c3": False})
    assert result.must_criteria_met is True


def test_acceptance_missing_evidence_for_a_must_criterion():
    result = evaluate_acceptance_criteria(CRITERIA, {"c1": True})
    assert result.must_criteria_met is None
    assert result.missing_evidence_ids == ["c2"]


def test_acceptance_unmet_must_criterion():
    result = evaluate_acceptance_criteria(CRITERIA, {"c1": True, "c2": False})
    assert result.must_criteria_met is False
    assert result.unmet_must_ids == ["c2"]


def test_acceptance_no_must_criteria_is_vacuously_met():
    result = evaluate_acceptance_criteria([{"id": "c3", "priority": "should"}], {})
    assert result.must_criteria_met is True


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {
                "hard_constraints_passed": True,
                "has_unresolved_blocking_questions": True,
                "budget_expired": False,
                "acceptance_criteria_met": True,
            },
            "BLOCKED",
        ),
        (
            {
                "hard_constraints_passed": False,
                "has_unresolved_blocking_questions": False,
                "budget_expired": False,
                "acceptance_criteria_met": True,
            },
            "FAIL",
        ),
        (
            {
                "hard_constraints_passed": True,
                "has_unresolved_blocking_questions": False,
                "budget_expired": False,
                "acceptance_criteria_met": None,
            },
            "INCOMPLETE",
        ),
        (
            {
                "hard_constraints_passed": True,
                "has_unresolved_blocking_questions": False,
                "budget_expired": False,
                "acceptance_criteria_met": False,
            },
            "FAIL",
        ),
        (
            {
                "hard_constraints_passed": True,
                "has_unresolved_blocking_questions": False,
                "budget_expired": False,
                "acceptance_criteria_met": True,
            },
            "PASS",
        ),
        (
            {
                "hard_constraints_passed": True,
                "has_unresolved_blocking_questions": False,
                "budget_expired": True,
                "acceptance_criteria_met": True,
            },
            "PASS_WITH_CAVEATS",
        ),
    ],
)
def test_derive_completion_state(kwargs: dict[str, object], expected: str):
    assert derive_completion_state(**kwargs) == expected  # type: ignore[arg-type]


def test_blocking_question_beats_everything_else():
    # Even a failed hard constraint and an unmet criterion don't matter if
    # there's still a blocking question -- you can't have verified
    # anything meaningful yet.
    state = derive_completion_state(
        hard_constraints_passed=False,
        has_unresolved_blocking_questions=True,
        budget_expired=True,
        acceptance_criteria_met=False,
    )
    assert state == "BLOCKED"


def test_hard_constraint_failure_beats_met_acceptance_criteria():
    state = derive_completion_state(
        hard_constraints_passed=False,
        has_unresolved_blocking_questions=False,
        budget_expired=False,
        acceptance_criteria_met=True,
    )
    assert state == "FAIL"


def test_text_alone_cannot_produce_pass():
    # There is no code path that returns PASS without acceptance_criteria_met
    # being the literal boolean True, backed by evaluate_acceptance_criteria's
    # requirement that every 'must' criterion have a recorded result.
    state = derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=False,
        budget_expired=False,
        acceptance_criteria_met=None,
    )
    assert state != "PASS"
    assert state == "INCOMPLETE"
