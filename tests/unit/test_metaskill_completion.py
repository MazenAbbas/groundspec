import pytest

from groundspec.metaskill.completion import (
    derive_completion_state,
    evaluate_acceptance_criteria,
    residual_risk_blocks_completion,
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


# --- Regression hardening: authorization violations and critical risk (v0.2.0rc2) ---


def test_authorization_violation_beats_everything_including_met_criteria():
    state = derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=False,
        budget_expired=False,
        acceptance_criteria_met=True,
        authorization_boundary_violated=True,
    )
    assert state == "FAIL"


def test_blocking_question_still_beats_authorization_violation():
    state = derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=True,
        budget_expired=False,
        acceptance_criteria_met=True,
        authorization_boundary_violated=True,
    )
    assert state == "BLOCKED"


def test_unresolved_critical_risk_to_validity_prevents_pass():
    state = derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=False,
        budget_expired=False,
        acceptance_criteria_met=True,
        unresolved_critical_risk_to_validity=True,
    )
    assert state == "FAIL"


def test_critical_risk_not_marked_as_affecting_validity_does_not_block_pass():
    state = derive_completion_state(
        hard_constraints_passed=True,
        has_unresolved_blocking_questions=False,
        budget_expired=False,
        acceptance_criteria_met=True,
        unresolved_critical_risk_to_validity=False,
    )
    assert state == "PASS"


def test_residual_risk_blocks_completion_true_for_unmarked_critical_risk():
    # Absence of affects_deliverable_validity defaults to True (conservative).
    assert residual_risk_blocks_completion([{"risk": "x", "severity": "critical"}]) is True


def test_residual_risk_blocks_completion_false_when_explicitly_not_validity_affecting():
    assert (
        residual_risk_blocks_completion(
            [{"risk": "x", "severity": "critical", "affects_deliverable_validity": False}]
        )
        is False
    )


def test_residual_risk_blocks_completion_false_for_non_critical_severity():
    assert residual_risk_blocks_completion([{"risk": "x", "severity": "high"}]) is False


def test_residual_risk_blocks_completion_false_when_no_risks():
    assert residual_risk_blocks_completion([]) is False


# --- Regression hardening: acceptance-criteria evidence adequacy (v0.2.0rc2) ---

CRITERIA_REQUIRING_STRONG_EVIDENCE = [
    {"id": "c1", "priority": "must", "verification_method": "automated_test"},
]


def test_model_evaluated_label_is_inadequate_for_automated_test_criterion():
    result = evaluate_acceptance_criteria(
        CRITERIA_REQUIRING_STRONG_EVIDENCE,
        {"c1": {"met": True, "evidence_label": "MODEL-EVALUATED"}},
    )
    assert result.must_criteria_met is None
    assert result.inadequate_evidence_ids == ["c1"]


def test_source_verified_label_is_adequate_for_automated_test_criterion():
    result = evaluate_acceptance_criteria(
        CRITERIA_REQUIRING_STRONG_EVIDENCE,
        {"c1": {"met": True, "evidence_label": "VERIFIED"}},
    )
    assert result.must_criteria_met is True
    assert result.inadequate_evidence_ids == []


def test_legacy_plain_bool_result_still_works_unchanged():
    result = evaluate_acceptance_criteria(CRITERIA_REQUIRING_STRONG_EVIDENCE, {"c1": True})
    assert result.must_criteria_met is True
    assert result.inadequate_evidence_ids == []


def test_manual_inspection_criterion_accepts_model_evaluated_label():
    criteria = [{"id": "c1", "priority": "must", "verification_method": "manual_inspection"}]
    entry = {"met": True, "evidence_label": "MODEL-EVALUATED"}
    result = evaluate_acceptance_criteria(criteria, {"c1": entry})
    assert result.must_criteria_met is True
    assert result.inadequate_evidence_ids == []


def test_unmet_criterion_with_weak_label_is_reported_as_unmet_not_inadequate():
    # Evidence-adequacy only matters for a claimed-met result; an honestly
    # reported failure is just a failure, regardless of what label rode
    # along with it.
    result = evaluate_acceptance_criteria(
        CRITERIA_REQUIRING_STRONG_EVIDENCE,
        {"c1": {"met": False, "evidence_label": "MODEL-EVALUATED"}},
    )
    assert result.must_criteria_met is False
    assert result.unmet_must_ids == ["c1"]
    assert result.inadequate_evidence_ids == []
