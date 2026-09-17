"""Generates three of the four Meta-Skill example scenarios (PRD Phase 5).

The fourth (03-software-csv-export) is deliberately not generated here: it
is the output of a real, live, isolated-session dry run of the exported
Meta-Skill (see examples/metaskill/03-software-csv-export/dry-run-report.md),
not a constructed artifact. These three ARE constructed -- authored during
feature development to demonstrate the target contract shape, exactly like
scripts/generate_examples.py does for the v0.1 examples/ directory. They are
labeled as such in each scenario's session-notes.md; none of their content
claims to be verified real-world research (see each contract's
scope.assumptions and status.remaining_uncertainty).
"""

from __future__ import annotations

from pathlib import Path

from groundspec.contract.factory import new_contract
from groundspec.contract.serialization import dump_document

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "examples" / "metaskill"


def _sec(contract: dict, key: str) -> dict:
    return contract[key]  # type: ignore[return-value]


def example_01_food_delivery_prd() -> tuple[dict, str]:
    c = new_contract(
        task_id="food-delivery-ksa-university-prd",
        raw_user_brief=(
            "Use Groundspec in Guided mode to study a food-delivery application for university "
            "students in Saudi Arabia. Produce a PRD and identify the highest-risk assumptions."
        ),
        normalized_problem_statement=(
            "No PRD exists yet for a campus-focused food-delivery product, and the riskiest "
            "assumptions behind it (payment mix, campus access, delivery logistics) haven't been "
            "surfaced or ranked."
        ),
        goal=(
            "Produce a PRD-shaped planning document for a food-delivery app targeting university "
            "students in Saudi Arabia, with the highest-risk assumptions explicitly identified and "
            "ranked."
        ),
        target_users=[
            "university students in Saudi Arabia (end users of the eventual app)",
            "the founding/product team reading this PRD to decide whether to build it",
        ],
        expected_deliverables=[
            {
                "name": "prd_outline",
                "description": (
                    "A PRD-structured planning document: problem, target users, MVP scope, "
                    "non-goals, and a ranked list of the highest-risk assumptions"
                ),
            }
        ],
        risk_overlays=["informational"],
        risk_level="low",
    )
    _sec(c, "routing")["domain_packs"] = [
        {"pack_id": "software", "version": "0.1.0"},
        {"pack_id": "research", "version": "0.1.0"},
    ]
    _sec(c, "scope")["non_goals"] = [
        "Actually building or shipping the app",
        "Nationwide launch scope -- this PRD is for a single-city pilot",
        "Verified real-world market sizing (this is a planning contract, not a completed research report)",
    ]
    _sec(c, "scope")["assumptions"] = [
        {
            "statement": "A single-city pilot (one or two campuses in Riyadh or Jeddah) is the right "
            "starting scope, not all of Saudi Arabia at once.",
            "confidence": "medium",
            "safe_default": True,
        },
        {
            "statement": "Campus-adjacent restaurants are logistically simpler for a pilot than "
            "delivering from across the city.",
            "confidence": "medium",
            "safe_default": True,
        },
    ]
    _sec(c, "scope")["open_questions"] = [
        {
            "question": "What's the actual payment mix among target students (card/mada, STC Pay-style "
            "wallets, or cash on delivery)? This changes checkout design and unit economics.",
            "classification": "high_value",
            "resolution_status": "open",
        },
        {
            "question": "Is there an existing university partnership for campus access, or must one be "
            "assumed/negotiated?",
            "classification": "high_value",
            "resolution_status": "open",
        },
    ]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "prd-covers-core-elements",
            "description": "PRD names target users, the core order-to-delivery journey, and MVP scope boundaries",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "reviewer confirms all three elements are present and specific, not generic",
        },
        {
            "id": "highest-risk-assumptions-ranked",
            "description": "At least 3 highest-risk assumptions are explicitly identified and ranked by potential impact",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "the PRD's risk section lists and orders them, not just mentions them in passing",
        },
        {
            "id": "no-fabricated-market-data",
            "description": "No specific Saudi market statistic (market size, payment-mix percentage, etc.) is stated as fact without a cited source",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "every quantitative market claim traces to status.verified_facts or is explicitly framed as an assumption/open question",
        },
    ]
    budget = _sec(c, "budget")
    budget["time_budget_minutes"] = 90
    budget["research_depth"] = "standard"
    session_notes = (
        "# Session notes: 01-food-delivery-ksa-university-prd\n\n"
        "**Mode:** Guided. **Intent:** contract-only.\n\n"
        "**How this example was produced:** constructed during Meta-Skill development to "
        "demonstrate the target contract shape for a Guided-mode planning request -- it was not "
        "captured from a live model run (unlike "
        "`examples/metaskill/03-software-csv-export`, which was). No claim is made that the "
        "assumptions/questions above are the objectively correct ones for a real Saudi food-delivery "
        "venture; they illustrate the *shape* of high-value-question selection and risk-ranking this "
        "Skill is meant to produce. A real invocation would need actual current research to fill in "
        "`status.verified_facts` before the PRD's market claims could be trusted.\n"
    )
    return c, session_notes


def example_02_research_image_dataset() -> tuple[dict, str]:
    c = new_contract(
        task_id="image-dataset-validation-approaches",
        raw_user_brief=(
            "Use Groundspec to compare three local-first image-dataset validation approaches under "
            "a four-hour research budget. Separate verified evidence from inference."
        ),
        normalized_problem_statement=(
            "No comparison exists yet between candidate local-first (offline, no cloud upload) "
            "approaches for validating an image dataset, and there's no time-boxed plan for producing one."
        ),
        goal=(
            "Produce a comparison of three local-first image-dataset validation approaches -- "
            "coverage, cost/compute, and failure modes -- completed within a 4-hour research budget, "
            "with verified findings kept explicitly separate from inference."
        ),
        target_users=["the engineer deciding which validation approach to adopt"],
        expected_deliverables=[
            {
                "name": "comparison_report",
                "description": "A structured comparison of the three approaches with sourced findings and labeled inference",
            }
        ],
        risk_overlays=["informational"],
        risk_level="low",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "research", "version": "0.1.0"}]
    _sec(c, "scope")["constraints"] = [
        "Local-first / offline-capable approaches only -- no cloud-hosted-only tools",
        "Hard 4-hour research time budget",
    ]
    _sec(c, "scope")["open_questions"] = [
        {
            "question": "Which three specific approaches/tools should be compared, or should the "
            "research select three representative ones itself?",
            "classification": "blocking",
            "resolution_status": "answered",
            "answer": (
                "No specific tools were named in the brief, so the research selects three "
                "representative local-first approaches itself (e.g. a rule-based checker, a "
                "statistical/embedding-based outlier detector, and a lightweight model-assisted "
                "checker) and states the selection rationale up front."
            ),
        }
    ]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "three-approaches-compared",
            "description": "Exactly three local-first approaches are compared on the same criteria",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "the report's comparison table has three rows and consistent columns",
        },
        {
            "id": "evidence-vs-inference-separated",
            "description": "Every claim is labeled as either sourced evidence or the researcher's own inference",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "status.verified_facts vs status.unverified_claims/remaining_uncertainty are both populated and distinct",
        },
        {
            "id": "within-time-budget",
            "description": "The research is completed, or honestly reported as partial, within the 4-hour budget",
            "priority": "must",
            "verification_method": "automated_test",
            "evidence_required": "status.budget_expired and status.completion_status are consistent with groundspec.budget.model.forbid_silent_skip_on_expiry",
        },
    ]
    budget = _sec(c, "budget")
    budget["time_budget_minutes"] = 240
    budget["research_depth"] = "standard"
    budget["reserved_verification_fraction"] = 0.2
    session_notes = (
        "# Session notes: 02-image-dataset-validation-approaches\n\n"
        "**Mode:** Guided. **Intent:** contract-only (research deliverable).\n\n"
        "**How this example was produced:** constructed during Meta-Skill development, not captured "
        "from a live model run. The 'blocking question, answered by picking three representative "
        "approaches' pattern demonstrates how the clarification policy handles a genuinely blocking "
        "gap (which tools to compare) when no user is available to ask -- the Skill states its own "
        "reasonable choice and its rationale rather than stalling. A real invocation would still "
        "need to actually run the comparison and populate status.verified_facts with real findings; "
        "this contract does not claim that work has happened.\n"
    )
    return c, session_notes


def example_04_audit_linkedin_post() -> tuple[dict, str]:
    audited_post = (
        "🚀 Thrilled to announce our launch! We've already helped over 50,000 companies save "
        "millions of dollars, and industry analysts agree we're the #1 solution on the market. "
        "This is a once-in-a-lifetime opportunity -- offer ends in 24 hours, so sign up now before "
        "it's gone forever!"
    )
    c = new_contract(
        task_id="audit-linkedin-launch-post",
        raw_user_brief=(
            "Audit this LinkedIn launch post. Verify every measurable claim and remove claims that "
            "are not supported by evidence."
        ),
        normalized_problem_statement=(
            "An existing draft LinkedIn post makes several specific, checkable claims (a user count, "
            "a savings figure, an analyst ranking, a countdown) with no evidence on file for any of them."
        ),
        goal=(
            "Audit the draft post: identify every measurable/factual claim, check it against "
            "available evidence, and produce a remediation report -- do not rewrite the post unless "
            "asked to."
        ),
        target_users=["whoever owns the post and decides whether to publish it"],
        expected_deliverables=[
            {
                "name": "audit_report",
                "description": "A remediation report listing each claim, its evidence status, and the recommended fix",
            }
        ],
        risk_overlays=["informational", "external_communication"],
        risk_level="low",
    )
    _sec(c, "routing")["domain_packs"] = [{"pack_id": "content", "version": "0.1.0"}]
    _sec(c, "scope")["non_goals"] = [
        "Rewriting or publishing the post (Audit mode: report findings, don't modify unless asked)"
    ]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "every-claim-identified",
            "description": "Every measurable/factual claim in the post is listed individually",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "the audit report enumerates each claim (user count, savings figure, analyst ranking, urgency deadline) separately",
        },
        {
            "id": "unsupported-claims-flagged",
            "description": "Each claim with no on-file evidence is flagged as unsupported, not silently accepted",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "status.unverified_claims lists each one with a reason",
        },
        {
            "id": "fabricated-urgency-flagged",
            "description": "The '24 hours / gone forever' urgency claim is flagged as a fabricated-urgency risk per the content domain pack, independent of whether it happens to be true",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "the audit report cites the no-fabricated-claims hard constraint explicitly",
        },
    ]
    session_notes = (
        "# Session notes: 04-audit-linkedin-launch-post\n\n"
        "**Mode:** Audit. **Intent:** audit-existing.\n\n"
        "**How this example was produced:** constructed during Meta-Skill development, not captured "
        "from a live model run. The audited post text below is a fabricated example written "
        "specifically to contain checkable problems (an unsourced user count, an unsourced savings "
        "figure, an unattributed 'industry analysts agree' claim, and a manufactured countdown) so "
        "that Audit mode's expected findings are unambiguous. It is not a real post from any real "
        "company.\n\n"
        "## The post being audited\n\n"
        f"> {audited_post}\n\n"
        "## Expected audit findings (what a correct audit should surface)\n\n"
        "1. \"50,000 companies\" -- unsourced quantitative claim; flag as unverified.\n"
        "2. \"save millions of dollars\" -- unsourced, unquantified; flag as unverified.\n"
        "3. \"industry analysts agree we're the #1 solution\" -- unattributed; no analyst is named or cited; flag as unverified.\n"
        "4. \"offer ends in 24 hours... gone forever\" -- classic fabricated-urgency pattern; flag per the content pack's hard constraint regardless of whether a real deadline exists, unless a genuine, verifiable deadline is on file.\n"
    )
    return c, session_notes


def main() -> None:
    scenarios = [
        ("01-food-delivery-ksa-university-prd", *example_01_food_delivery_prd()),
        ("02-image-dataset-validation-approaches", *example_02_research_image_dataset()),
        ("04-audit-linkedin-launch-post", *example_04_audit_linkedin_post()),
    ]
    for slug, contract, notes in scenarios:
        out_dir = OUT / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        dump_document(contract, out_dir / "contract.toml")
        (out_dir / "session-notes.md").write_text(notes, encoding="utf-8")
        print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
