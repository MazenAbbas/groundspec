from eval.metrics import (
    ClarificationRecord,
    clarification_precision,
    correct_incompleteness_reporting,
    hard_constraint_violation_rate,
    missed_blocking_question_count,
    scope_creep_rate,
    unnecessary_question_count,
    unsafe_assumption_rate,
    unsupported_claim_rate,
)


def test_clarification_precision_all_necessary():
    record = ClarificationRecord(questions_asked=["a", "b"], questions_materially_needed=["a", "b"])
    assert clarification_precision(record) == 1.0


def test_clarification_precision_partial():
    record = ClarificationRecord(questions_asked=["a", "b", "c"], questions_materially_needed=["a"])
    assert clarification_precision(record) == 1 / 3


def test_clarification_precision_undefined_when_none_asked():
    record = ClarificationRecord(questions_asked=[], questions_materially_needed=["a"])
    assert clarification_precision(record) is None


def test_unnecessary_and_missed_counts():
    record = ClarificationRecord(questions_asked=["a", "x"], questions_materially_needed=["a", "b"])
    assert unnecessary_question_count(record) == 1  # "x"
    assert missed_blocking_question_count(record) == 1  # "b"


def test_hard_constraint_violation_rate_undefined_when_none_applicable():
    assert hard_constraint_violation_rate(0, 0) is None
    assert hard_constraint_violation_rate(4, 1) == 0.25


def test_unsafe_assumption_rate():
    assert unsafe_assumption_rate(0, 0) is None
    assert unsafe_assumption_rate(5, 1) == 0.2


def test_unsupported_claim_rate():
    assert unsupported_claim_rate(10, 2) == 0.2


def test_scope_creep_rate():
    assert scope_creep_rate(3, 1) == 3.0
    assert scope_creep_rate(1, 2) == 0.5
    assert scope_creep_rate(1, 0) is None


def test_correct_incompleteness_reporting():
    assert correct_incompleteness_reporting(budget_was_exhausted=False, reported_completion_status="complete")
    assert correct_incompleteness_reporting(budget_was_exhausted=True, reported_completion_status="partial")
    assert not correct_incompleteness_reporting(
        budget_was_exhausted=True, reported_completion_status="complete"
    )
