"""Platform-independent compilation of a Task Contract into instruction text.

Every adapter (Claude Skill, Codex Skill, generic prompt) renders from the
exact same :func:`render_body` output. This is deliberate: Phase 10/25 both
require that "adapters must not change the contract's meaning," and the
only reliable way to guarantee that is to give them nothing to individually
reinterpret -- vendor-specific code only adds frontmatter and file
placement around one shared body.
"""

from __future__ import annotations

from groundspec.rules.evaluator import AppliedRule

LIMITATIONS_NOTE = (
    "This document is generated instructions, not enforcement. A model can be told to honor "
    "hard constraints and budgets, but nothing here can force it to -- there is no runtime "
    "checking the model's own output against this contract except what you run yourself with "
    "`groundspec audit` / `groundspec evaluate` afterward. Treat this as a strong brief, not a "
    "guarantee."
)


def _fmt_list(items: list[str], empty: str = "(none)") -> str:
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def render_body(
    contract: dict[str, object],
    applied_rules: list[AppliedRule],
) -> str:
    brief = contract["brief"]
    scope = contract["scope"]
    routing = contract["routing"]
    quality = contract["quality"]
    acceptance = contract["acceptance"]
    budget = contract["budget"]
    control = contract["control"]
    assert isinstance(brief, dict) and isinstance(scope, dict) and isinstance(routing, dict)
    assert isinstance(quality, dict) and isinstance(acceptance, dict) and isinstance(budget, dict)
    assert isinstance(control, dict)

    hard = [a for a in applied_rules if a.applies and a.severity == "hard_constraint"]
    soft_rule = [a for a in applied_rules if a.applies and a.severity == "soft_objective"]
    advisory = [a for a in applied_rules if a.applies and a.severity == "advisory"]

    sections: list[str] = []

    sections.append(f"# Task: {contract['task_id']}\n")
    sections.append(f"**Goal.** {brief['goal']}\n")
    sections.append(f"**Problem.** {brief['normalized_problem_statement']}\n")
    sections.append("**Who this is for.**\n" + _fmt_list(list(brief["target_users"])) + "\n")
    if brief.get("context"):
        sections.append(f"**Context.** {brief['context']}\n")

    deliverables = [f"{d['name']}: {d['description']}" for d in brief["expected_deliverables"]]
    sections.append("## Deliverables\n" + _fmt_list(deliverables) + "\n")

    sections.append("## Constraints and non-goals\n")
    sections.append("Constraints:\n" + _fmt_list(list(scope["constraints"])) + "\n")
    sections.append("Explicitly out of scope:\n" + _fmt_list(list(scope["non_goals"])) + "\n")

    assumptions = [f"{a['statement']} (confidence: {a['confidence']})" for a in scope["assumptions"]]
    sections.append("## Assumptions in force\n" + _fmt_list(assumptions) + "\n")

    open_qs = [
        f"[{q['classification']}] {q['question']}"
        for q in scope["open_questions"]
        if q["resolution_status"] == "open"
    ]
    if open_qs:
        sections.append(
            "## Open questions still blocking\n"
            + _fmt_list(open_qs)
            + "\nResolve 'blocking' questions before proceeding. For "
            "'important_defaultable' questions, apply the documented default and record it in "
            "scope.open_questions[].default_applied rather than stopping.\n"
        )

    auth = routing["authorization"]
    assert isinstance(auth, dict)
    sections.append(
        "## Authorization\n"
        f"Risk level: {routing['risk_level']} | Risk overlays: {', '.join(routing['risk_overlays'])}\n"
        "Granted permissions:\n" + _fmt_list(list(auth["granted_permissions"])) + "\n"
        "Boundaries:\n" + _fmt_list(list(auth["boundaries"])) + "\n"
        "Requires explicit confirmation before doing any of:\n"
        + _fmt_list(list(auth["requires_confirmation_for"]))
        + "\n"
    )

    hard_lines = [f"[{a.qualified.fq_id}] {a.qualified.rule['requirement']}" for a in hard]
    sections.append(
        "## Hard constraints (a single violation blocks completion; no soft score can outweigh this)\n"
        + _fmt_list(hard_lines)
        + "\n"
    )

    soft_lines = [f"{o['dimension']} (weight {o['weight']})" for o in quality["soft_objectives"]]
    soft_lines += [f"[{a.qualified.fq_id}] {a.qualified.rule['requirement']}" for a in soft_rule]
    sections.append("## Soft quality objectives (weighted, improvable, never overrides a hard constraint)\n"
                     + _fmt_list(soft_lines) + "\n")

    if advisory:
        advisory_lines = [f"[{a.qualified.fq_id}] {a.qualified.rule['requirement']}" for a in advisory]
        sections.append("## Advisory notes\n" + _fmt_list(advisory_lines) + "\n")

    criteria_lines = [
        f"[{c['priority']}] {c['id']}: {c['description']} "
        f"(verify via {c['verification_method']}; evidence: {c['evidence_required']})"
        for c in acceptance["criteria"]
    ]
    sections.append("## Acceptance criteria\n" + _fmt_list(criteria_lines) + "\n")

    sections.append(
        "## Budget\n"
        f"- Time: {budget['time_budget_minutes']} minutes "
        f"(reserve {budget['reserved_verification_fraction'] * 100:.0f}% for final verification, "
        "never spend it on anything else)\n"
        f"- Clarification questions: {budget['max_clarification_questions']}\n"
        f"- Planning iterations: {budget['max_planning_iterations']}\n"
        f"- Execution iterations: {budget['max_execution_iterations']}\n"
        f"- Tool calls: {budget['tool_call_budget']}\n"
        f"- Research depth: {budget['research_depth']}\n"
    )

    stop_lines = [f"{c['id']}: if {c['trigger']} then {c['action']}" for c in control["stop_conditions"]]
    esc_lines = [f"{c['id']}: if {c['trigger']} then {c['action']}" for c in control["escalation_conditions"]]
    sections.append("## Stop conditions\n" + _fmt_list(stop_lines) + "\n")
    sections.append("## Escalation conditions\n" + _fmt_list(esc_lines) + "\n")

    sections.append(
        "## When you finish (or run out of budget)\n"
        "Report using these evidence labels only: VERIFIED, MEASURED, MODEL-EVALUATED, "
        "HUMAN-REVIEWED, PROPOSED, PENDING_EXTERNAL_VALIDATION, OUT_OF_SCOPE. Never use a "
        "stronger label than the evidence you actually have. If the budget ran out, "
        "completion_status must be 'partial' or 'blocked' -- never 'complete' -- and you must "
        "list what was omitted and what verification was skipped. Prefer reporting incomplete "
        "work honestly over claiming a finish that didn't happen.\n"
    )

    sections.append(f"---\n{LIMITATIONS_NOTE}\n")

    return "\n".join(sections)
