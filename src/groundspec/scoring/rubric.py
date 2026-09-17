"""The soft loss function: a weighted, explicitly non-objective rubric that
can never outrank a hard-constraint failure (see PRD Phase 5).

This module does not invent scores. Per-dimension scores (0.0-1.0, or
``None`` for "cannot be scored with the evidence available") are supplied
by the caller -- a human reviewer or an AI Skill's self-assessment recorded
as evidence. What this module guarantees deterministically is: weights are
never silently renormalized without saying so, a dimension named twice is
an error rather than double-counted, a hard-constraint failure always wins
over any soft score, and every individual dimension result survives in the
output alongside the total.
"""

from __future__ import annotations

from dataclasses import dataclass

# Dimensions with a comparatively mechanical, measurable basis (tests pass,
# criteria present, budget arithmetic). The rest depend on reviewer
# judgment and are labeled as such in every result -- see PRD Phase 5's
# "label subjective judgments" requirement.
OBJECTIVE_DIMENSIONS = frozenset(
    {
        "correctness",
        "requirement_coverage",
        "acceptance_criteria_completeness",
        "resource_overrun",
    }
)

ALL_DIMENSIONS = frozenset(
    {
        "correctness",
        "requirement_coverage",
        "evidence_quality",
        "usability",
        "clarity",
        "maintainability",
        "efficiency",
        "uncertainty_handling",
        "scope_discipline",
        "unsupported_claims",
        "acceptance_criteria_completeness",
        "resource_overrun",
    }
)


class DuplicateDimension(ValueError):
    pass


@dataclass(frozen=True)
class DimensionScore:
    dimension: str
    weight: float
    score: float | None
    subjective: bool
    rationale: str = ""

    @property
    def insufficient_evidence(self) -> bool:
        return self.score is None


@dataclass(frozen=True)
class RubricResult:
    hard_constraints_passed: bool
    failed_hard_constraint_ids: list[str]
    dimension_scores: list[DimensionScore]
    weighted_total: float | None
    insufficient_dimensions: list[str]
    verdict: str  # "fail_hard_constraint" | "scored" | "insufficient_evidence"


def _validate_unique_dimensions(soft_objectives: list[dict[str, object]]) -> None:
    seen: set[str] = set()
    for obj in soft_objectives:
        dim = obj["dimension"]
        assert isinstance(dim, str)
        if dim in seen:
            raise DuplicateDimension(
                f"dimension {dim!r} appears more than once in quality.soft_objectives; "
                "a single weight per dimension prevents double-counting the same failure"
            )
        seen.add(dim)


def score(
    *,
    soft_objectives: list[dict[str, object]],
    hard_constraint_results: dict[str, bool],
    dimension_scores: dict[str, float | None],
) -> RubricResult:
    failed_hard = sorted(rule_id for rule_id, passed in hard_constraint_results.items() if not passed)
    hard_passed = len(failed_hard) == 0

    _validate_unique_dimensions(soft_objectives)

    results: list[DimensionScore] = []
    for obj in soft_objectives:
        dim = obj["dimension"]
        weight = obj["weight"]
        assert isinstance(dim, str) and isinstance(weight, (int, float))
        raw_score = dimension_scores.get(dim)
        results.append(
            DimensionScore(
                dimension=dim,
                weight=float(weight),
                score=raw_score,
                subjective=dim not in OBJECTIVE_DIMENSIONS,
            )
        )

    insufficient = [d.dimension for d in results if d.insufficient_evidence]
    scored = [d for d in results if not d.insufficient_evidence]
    weight_sum = sum(d.weight for d in scored)
    weighted_total: float | None
    if not hard_passed:
        weighted_total = None
        verdict = "fail_hard_constraint"
    elif not scored or weight_sum == 0:
        weighted_total = None
        verdict = "insufficient_evidence"
    else:
        weighted_total = sum((d.score or 0.0) * d.weight for d in scored) / weight_sum
        verdict = "scored"

    return RubricResult(
        hard_constraints_passed=hard_passed,
        failed_hard_constraint_ids=failed_hard,
        dimension_scores=results,
        weighted_total=weighted_total,
        insufficient_dimensions=insufficient,
        verdict=verdict,
    )
