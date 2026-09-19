"""Builds a minimal, schema-valid Task Contract from the few fields a user
actually has to supply. Everything else is an explicit, documented default
-- never a guess about the user's actual intent.
"""

from __future__ import annotations

from groundspec.__about__ import CONTRACT_SCHEMA_VERSION


def new_contract(
    *,
    task_id: str,
    raw_user_brief: str,
    normalized_problem_statement: str,
    goal: str,
    target_users: list[str],
    expected_deliverables: list[dict[str, str]],
    risk_overlays: list[str] | None = None,
    risk_level: str = "low",
    tool_call_budget: int = 50,
    time_budget_minutes: int = 60,
) -> dict[str, object]:
    return {
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "task_id": task_id,
        "brief": {
            "raw_user_brief": raw_user_brief,
            "normalized_problem_statement": normalized_problem_statement,
            "goal": goal,
            "target_users": target_users,
            "context": "",
            "inputs": [],
            "expected_deliverables": expected_deliverables,
        },
        "scope": {
            "constraints": [],
            "non_goals": [],
            "assumptions": [],
            "open_questions": [],
        },
        "routing": {
            "domain_packs": [],
            "risk_overlays": risk_overlays or ["informational"],
            "risk_level": risk_level,
            "authorization": {
                "granted_permissions": [],
                "boundaries": [],
                "requires_confirmation_for": [],
            },
        },
        "quality": {
            "hard_constraints": [],
            "soft_objectives": [],
        },
        "acceptance": {"criteria": []},
        "budget": {
            "time_budget_minutes": time_budget_minutes,
            "max_clarification_questions": 3,
            "max_planning_iterations": 3,
            "max_execution_iterations": 20,
            "tool_call_budget": tool_call_budget,
            "research_depth": "shallow",
            "cost_budget": None,
            "reserved_verification_fraction": 0.15,
        },
        "control": {
            "stop_conditions": [],
            "escalation_conditions": [],
        },
        "status": {
            "completion_status": "not_started",
            "verified_facts": [],
            "unverified_claims": [],
            "remaining_uncertainty": [],
            "residual_risks": [],
            "omitted_work": [],
            "budget_expired": False,
        },
    }
