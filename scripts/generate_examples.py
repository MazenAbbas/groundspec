"""One-off generator for the repo's examples/ directory (PRD Phase 16).

Run with: .venv/Scripts/python.exe scripts/generate_examples.py

This is a development-time script, not part of the shipped package. It is
re-run manually whenever an example needs to be regenerated after a schema
change; its output is committed to git and then only ever read (and
validated by tests/integration/test_examples.py), never regenerated as a
side effect of running the test suite.
"""

from __future__ import annotations

import json
from pathlib import Path

from groundspec.contract.factory import new_contract
from groundspec.contract.serialization import dump_document

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def _sec(contract: dict, key: str) -> dict:
    return contract[key]  # type: ignore[return-value]


def example_01_food_delivery_mvp() -> dict:
    c = new_contract(
        task_id="food-delivery-mvp",
        raw_user_brief="I want a food delivery app",
        normalized_problem_statement=(
            "No MVP scope, target user, or acceptance criteria exist yet for the requested app; "
            "'food delivery app' alone does not specify what 'done' looks like."
        ),
        goal="Ship a walking-skeleton MVP: one city, one restaurant, one order flow, working end to end.",
        target_users=["a pilot cohort of customers in one city", "the one partner restaurant"],
        expected_deliverables=[
            {"name": "mvp_repo", "description": "A running MVP repository implementing the order flow"},
            {"name": "demo_script", "description": "Steps to demo the order flow locally"},
        ],
        risk_overlays=["informational", "filesystem_mutation"],
        risk_level="medium",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "software", "version": "0.1.0"}]
    _sec(c, "scope")["non_goals"] = [
        "Multi-city support",
        "Real payment processing (a sandboxed/mocked flow is enough)",
        "A driver-facing app",
        "Restaurant onboarding self-service",
    ]
    _sec(c, "scope")["assumptions"] = [
        {
            "statement": "One pilot city and one partner restaurant is an acceptable MVP scope.",
            "confidence": "medium",
            "safe_default": True,
        }
    ]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "order-flow-works",
            "description": "A user can browse the one restaurant's menu and place one order end to end",
            "priority": "must",
            "verification_method": "reproducible_command",
            "evidence_required": "an automated test exercising the order flow, and its output",
        },
        {
            "id": "demo-reproducible",
            "description": "Another developer can follow demo_script and reproduce the demo",
            "priority": "should",
            "verification_method": "manual_inspection",
            "evidence_required": "a second person confirms the script works from a clean checkout",
        },
    ]
    return c


def example_02_market_research() -> dict:
    c = new_contract(
        task_id="market-research-viability",
        raw_user_brief="research whether this market is promising",
        normalized_problem_statement="No evidence exists yet on whether this market is viable to enter.",
        goal=(
            "Produce a go/no-go recommendation, with sources, on whether to enter the market for "
            "AI-assisted grocery list apps in the US in 2026."
        ),
        target_users=["the founder deciding whether to build this"],
        expected_deliverables=[
            {"name": "market_report", "description": "A sourced market analysis with a recommendation"}
        ],
        risk_overlays=["informational"],
        risk_level="low",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "research", "version": "0.1.0"}]
    _sec(c, "scope")["constraints"] = [
        "US market only",
        "Use sources no older than 3 years unless citing a foundational/structural fact",
    ]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "sourced-recommendation",
            "description": "Recommendation is backed by at least 3 primary sources",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "citations present next to each claim, with access dates",
        },
        {
            "id": "contradictions-surfaced",
            "description": "Any disagreement between sources on market size/growth is reported, not hidden",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "the report names the disagreement and which side it favors, and why",
        },
    ]
    return c


def example_03_linkedin_launch_post() -> dict:
    c = new_contract(
        task_id="linkedin-launch-post",
        raw_user_brief="write a linkedin post announcing our launch",
        normalized_problem_statement="No announcement content exists yet for the product launch.",
        goal="Produce one LinkedIn post announcing the launch, ready to publish pending approval.",
        target_users=["prospective customers following the company page"],
        expected_deliverables=[{"name": "post_draft", "description": "Final LinkedIn post text"}],
        risk_overlays=["informational", "external_communication"],
        risk_level="low",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "content", "version": "0.1.0"}]
    _sec(c, "scope")["constraints"] = ["Under 200 words", "Match existing brand voice: direct, no hype"]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "under-word-limit",
            "description": "Post is at or under 200 words",
            "priority": "must",
            "verification_method": "automated_test",
            "evidence_required": "word count reported alongside the draft",
        },
        {
            "id": "no-fabricated-claims",
            "description": "No invented statistics or testimonials appear in the post",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "reviewer confirms every claim traces to a verified fact",
        },
    ]
    _sec(_sec(c, "routing"), "authorization")["requires_confirmation_for"] = [
        "publishing the post to the real company LinkedIn page"
    ]
    return c


def example_04_five_minute_task() -> dict:
    c = new_contract(
        task_id="rename-config-key",
        raw_user_brief="rename the FOO_BAR config key to FEATURE_FLAG_FOO_BAR everywhere",
        normalized_problem_statement="The config key name no longer matches the naming convention.",
        goal="Every reference to FOO_BAR in config and code uses FEATURE_FLAG_FOO_BAR instead.",
        target_users=["the developer maintaining this config"],
        expected_deliverables=[{"name": "renamed_refs", "description": "All references renamed consistently"}],
        risk_overlays=["informational", "filesystem_mutation"],
        risk_level="low",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "software", "version": "0.1.0"}]
    budget = _sec(c, "budget")
    budget["time_budget_minutes"] = 5
    budget["max_planning_iterations"] = 1
    budget["max_execution_iterations"] = 3
    budget["tool_call_budget"] = 10
    budget["research_depth"] = "none"
    budget["reserved_verification_fraction"] = 0.3
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "no-old-name-remains",
            "description": "A search for FOO_BAR finds zero remaining occurrences",
            "priority": "must",
            "verification_method": "reproducible_command",
            "evidence_required": "grep output showing zero matches for the old name",
        }
    ]
    return c


def example_05_high_risk_medical_escalation() -> dict:
    c = new_contract(
        task_id="medication-dosage-question",
        raw_user_brief="what dosage of this medication should I take for my condition",
        normalized_problem_statement=(
            "The user is asking for a specific medical dosage decision, which is a clinical "
            "judgment this framework cannot make."
        ),
        goal=(
            "Provide general, sourced information about the medication and clearly route the user "
            "to a qualified prescriber for the actual dosage decision."
        ),
        target_users=["the person asking, who is not a medical professional"],
        expected_deliverables=[
            {"name": "info_summary", "description": "General medication information with sources"}
        ],
        risk_overlays=["informational", "high_stakes_regulated"],
        risk_level="critical",
    )
    _sec(c, "scope")["non_goals"] = ["Recommending a specific dosage or making a prescribing decision"]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "no-dosage-recommendation",
            "description": "No specific dosage number is recommended for this user's situation",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "reviewer confirms the response contains no personalized dosage figure",
        }
    ]
    _sec(c, "control")["escalation_conditions"] = [
        {
            "id": "route-to-prescriber",
            "trigger": "the user asks for a specific dosage or personalized medical decision",
            "action": "state plainly that this requires a licensed prescriber and stop short of deciding",
        }
    ]
    return c


def example_06_contradictory_requirements() -> dict:
    c = new_contract(
        task_id="contradictory-brief-summary",
        raw_user_brief=(
            "write a one-paragraph summary of the report, but make sure to cover all 12 findings "
            "in full detail"
        ),
        normalized_problem_statement=(
            "The brief asks for both a one-paragraph summary and full detail on 12 findings, which "
            "cannot both be satisfied literally."
        ),
        goal="Produce a summary that resolves the length-vs-completeness contradiction explicitly.",
        target_users=["the report's original requester"],
        expected_deliverables=[{"name": "summary", "description": "The resolved summary document"}],
        risk_overlays=["informational"],
        risk_level="low",
    )
    _sec(c, "scope")["open_questions"] = [
        {
            "question": (
                "Should the one-paragraph length constraint or the 'all 12 findings in full "
                "detail' constraint take priority, since both cannot hold at once?"
            ),
            "classification": "blocking",
            "resolution_status": "answered",
            "answer": (
                "Length wins: produce a one-paragraph executive summary, plus a separate appendix "
                "listing all 12 findings in full detail, so both intents are honored in different sections."
            ),
        }
    ]
    _sec(c, "scope")["assumptions"] = [
        {
            "statement": "A two-part deliverable (short summary + detailed appendix) satisfies both stated needs.",
            "confidence": "medium",
            "safe_default": True,
        }
    ]
    _sec(c, "status")["remaining_uncertainty"] = [
        "The requester has not confirmed the two-part resolution; if they truly need a single "
        "paragraph with no appendix, some findings will be compressed to the point of losing detail."
    ]
    return c


def example_07_insufficient_evidence() -> dict:
    c = new_contract(
        task_id="competitor-pricing-lookup",
        raw_user_brief="find out exactly what our top 3 competitors charge for the enterprise tier",
        normalized_problem_statement="Competitor enterprise pricing is not publicly listed for at least one competitor.",
        goal="Report each competitor's enterprise pricing, or state clearly that it could not be found.",
        target_users=["the pricing team"],
        expected_deliverables=[{"name": "pricing_table", "description": "Per-competitor pricing or 'unknown'"}],
        risk_overlays=["informational"],
        risk_level="low",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "research", "version": "0.1.0"}]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "pricing-or-honest-gap",
            "description": "Each competitor has either a sourced price or an explicit 'not publicly disclosed'",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "no cell in the pricing table is a guess presented as fact",
        }
    ]
    return c


EVIDENCE_07 = {
    "hard_constraint_results": {},
    "dimension_scores": {"correctness": 0.9, "evidence_quality": None},
}


def example_08_partial_completion_is_correct() -> dict:
    c = new_contract(
        task_id="migrate-legacy-reports",
        raw_user_brief="migrate all 40 legacy reports to the new dashboard format",
        normalized_problem_statement="40 legacy reports use a format the new dashboard cannot read.",
        goal="Migrate as many of the 40 legacy reports as the time budget allows, without breaking any.",
        target_users=["analysts who rely on these reports"],
        expected_deliverables=[{"name": "migrated_reports", "description": "Reports converted to the new format"}],
        risk_overlays=["informational", "filesystem_mutation"],
        risk_level="medium",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "software", "version": "0.1.0"}]
    budget = _sec(c, "budget")
    budget["time_budget_minutes"] = 30
    budget["reserved_verification_fraction"] = 0.2
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "migrated-reports-render",
            "description": "Every migrated report renders correctly in the new dashboard",
            "priority": "must",
            "verification_method": "reproducible_command",
            "evidence_required": "a rendering check run against each migrated report",
        }
    ]
    status = _sec(c, "status")
    status["completion_status"] = "partial"
    status["budget_expired"] = True
    status["verified_facts"] = [
        {
            "statement": "23 of 40 reports were migrated and pass the rendering check.",
            "evidence_label": "VERIFIED",
            "source": "rendering check output, run 2026-09-17",
        }
    ]
    status["omitted_work"] = ["The remaining 17 reports were not migrated before the time budget ran out."]
    status["remaining_uncertainty"] = [
        "The 17 unmigrated reports have not been checked for format quirks that might make them harder."
    ]
    status["residual_risks"] = [
        {
            "risk": "Analysts relying on the 17 unmigrated reports will not see them in the new dashboard yet.",
            "severity": "medium",
            "mitigation": "Keep the legacy dashboard available read-only until migration finishes.",
        }
    ]
    return c


def example_09_domain_rule_vs_style_preference() -> dict:
    c = new_contract(
        task_id="promo-post-no-length-limit",
        raw_user_brief="write our promo post and don't worry about length, just make it thorough",
        normalized_problem_statement=(
            "The task preference asks to ignore length limits, but the platform format constraint "
            "in the content domain pack requires respecting stated length limits."
        ),
        goal="Produce a promotional post for the target platform.",
        target_users=["the platform's audience"],
        expected_deliverables=[{"name": "promo_post", "description": "The promotional post text"}],
        risk_overlays=["informational", "external_communication"],
        risk_level="low",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "content", "version": "0.1.0"}]
    _sec(c, "scope")["constraints"] = ["Platform character limit is 280 characters"]
    return c


PROJECT_PACK_09 = {
    "rule_pack_schema_version": "0.1.0",
    "pack_id": "project-style-preference-example",
    "version": "0.1.0",
    "layer": "project",
    "title": "Example project preference: ignore length limits",
    "description": "Demonstrates a project-layer preference that conflicts with, and loses to, a domain rule.",
    "rules": [
        {
            "id": "ignore-length-limits",
            "version": "0.1.0",
            "title": "Prefer thoroughness over the stated length limit",
            "purpose": "Reflects a one-off task preference expressed by the user.",
            "scope": "This task only.",
            "applies_when": True,
            "severity": "soft_objective",
            "requirement": "Ignore any stated length/character limit; prioritize covering everything thoroughly instead.",
            "verification_method": "manual_inspection",
            "evidence_requirement": "the draft is judged on completeness, not length.",
            "failure_behavior": "warn_only",
            "source_or_rationale": "PRD Phase 16 example 9: task preference vs domain rule conflict.",
            "conflict_key": "platform-format-constraint",
        }
    ],
}


def example_10_unauthorized_external_action() -> dict:
    c = new_contract(
        task_id="post-apology-to-support-forum",
        raw_user_brief="go post an apology on the public support forum for the outage, use my account",
        normalized_problem_statement=(
            "The user is asking for a public post to be made on their behalf without having "
            "reviewed or approved the specific content first."
        ),
        goal="Draft an apology post for the outage and get it explicitly approved before any posting.",
        target_users=["customers who saw the outage", "the requesting user, who must approve the text"],
        expected_deliverables=[{"name": "apology_draft", "description": "Draft apology text, unpublished"}],
        risk_overlays=["informational", "external_communication"],
        risk_level="medium",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "content", "version": "0.1.0"}]
    auth = _sec(_sec(c, "routing"), "authorization")
    auth["granted_permissions"] = ["drafting the apology text"]
    auth["boundaries"] = ["no post may be published without explicit per-post confirmation"]
    auth["requires_confirmation_for"] = ["publishing anything to the public support forum"]
    _sec(c, "control")["stop_conditions"] = [
        {
            "id": "stop-before-publish",
            "trigger": "the draft is ready to post",
            "action": "show the exact text and destination to the user and wait for explicit confirmation",
        }
    ]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "not-published-without-confirmation",
            "description": "The post is not published until the user explicitly confirms the exact text",
            "priority": "must",
            "verification_method": "user_confirmation",
            "evidence_required": "a confirmation record showing the exact approved text",
        }
    ]
    return c


def main() -> None:
    scenarios = [
        ("01-food-delivery-mvp", example_01_food_delivery_mvp(), None),
        ("02-market-research", example_02_market_research(), None),
        ("03-linkedin-launch-post", example_03_linkedin_launch_post(), None),
        ("04-five-minute-constrained-task", example_04_five_minute_task(), None),
        ("05-high-risk-medical-escalation", example_05_high_risk_medical_escalation(), None),
        ("06-contradictory-requirements", example_06_contradictory_requirements(), None),
        ("07-insufficient-evidence", example_07_insufficient_evidence(), EVIDENCE_07),
        ("08-partial-completion-correct", example_08_partial_completion_is_correct(), None),
        ("09-domain-rule-vs-style-preference", example_09_domain_rule_vs_style_preference(), None),
        ("10-unauthorized-external-action", example_10_unauthorized_external_action(), None),
    ]
    for slug, contract, evidence in scenarios:
        out_dir = EXAMPLES / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        dump_document(contract, out_dir / "contract.toml")
        if evidence is not None:
            result_dir = out_dir / "result"
            result_dir.mkdir(exist_ok=True)
            (result_dir / "evidence.json").write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        print(f"wrote {out_dir}")

    pack_dir = EXAMPLES / "09-domain-rule-vs-style-preference" / "project-packs"
    pack_dir.mkdir(exist_ok=True)
    (pack_dir / "project-style-preference-example.json").write_text(
        json.dumps(PROJECT_PACK_09, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {pack_dir}")


if __name__ == "__main__":
    main()
