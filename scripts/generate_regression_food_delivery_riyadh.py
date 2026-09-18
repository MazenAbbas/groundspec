"""Generates the second food-delivery regression fixtures under
tests/regression/food_delivery_riyadh_v0_2_0rc2/ (a live PRD run that
returned PASS despite unsupported material claims, a silently-promoted
city, a generalized ZATCA VAT rule, and a secondary source treated as
official -- see that directory's README.md).

Not part of the installed package; a dev-only, re-runnable generator,
exactly like scripts/generate_regression_food_delivery.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from groundspec.contract.factory import new_contract
from groundspec.contract.serialization import dump_document

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "regression" / "food_delivery_riyadh_v0_2_0rc2"

ZATCA_URL = "https://example-tax-advisory.example/zatca-emarketplace-vat-guidance"
ZATCA_TITLE = "ZATCA e-marketplace VAT deemed-supplier guidance -- explainer"
RIDER_URL = "https://example-news.example/ksa-gig-economy-rider-classification"
RIDER_TITLE = "Coverage of gig-economy delivery rider classification trends in KSA"


def _sec(contract: dict, key: str) -> dict:
    return contract[key]  # type: ignore[return-value]


def build_defective_contract_0_3_0() -> dict:
    """Reproduces, under the OLD (0.3.0, pre-claim-ledger) schema, the exact
    pattern the second live test exhibited: material claims (student
    budget/schedule, competitor gap) exist only as PRD prose with no
    evidence record of any kind; a conditional regulatory rule (ZATCA VAT
    deemed-supplier treatment) is recorded as a flatly VERIFIED fact with
    no real source and no preserved conditions; and the specific pilot
    city/campus (Riyadh / King Saud University) appears in the brief with
    no corresponding open_question at all -- silently promoted from
    illustrative anchor to confirmed scope."""
    c = new_contract(
        task_id="ksa-food-delivery-riyadh-defective-run",
        raw_user_brief=(
            "Create a PRD for a university-student food-delivery application in Riyadh, "
            "piloting near King Saud University."
        ),
        normalized_problem_statement=(
            "University students in Riyadh have narrower discretionary budgets and more rigid "
            "daily schedules than the general population, and major food-delivery platforms do "
            "not specifically optimize for these needs."
        ),
        goal="Produce a PRD for a Riyadh university-student food-delivery pilot near King Saud University.",
        target_users=["Riyadh university students", "the founder deciding whether to pursue this"],
        expected_deliverables=[{"name": "prd", "description": "The PRD document"}],
        risk_overlays=["informational"],
        risk_level="low",
    )
    c["contract_schema_version"] = "0.3.0"
    # Riyadh / King Saud University appear directly in brief.raw_user_brief and
    # brief.goal above with NO corresponding scope.open_questions entry --
    # the exact "silently promoted from illustrative anchor to confirmed
    # scope" defect. scope.open_questions is left empty, on purpose.
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "zatca-section-accurate",
            "description": "The VAT/regulatory section accurately reflects official ZATCA guidance",
            "priority": "must",
            "verification_method": "external_reference_check",
            "evidence_required": "the cited ZATCA rule was actually read and matches the claim as stated",
        }
    ]
    # The defect: a conditional rule (deemed-supplier treatment is
    # conditional on supplier residency/VAT-registration status, among
    # other things) generalized into an unconditional one, and recorded as
    # VERIFIED with no actual source -- "general knowledge" is not a source.
    _sec(c, "status")["verified_facts"] = [
        {
            "statement": "All food-delivery marketplaces operating in Saudi Arabia are deemed "
            "suppliers under ZATCA rules and must issue every invoice themselves.",
            "evidence_label": "VERIFIED",
            "source": "General knowledge of GCC e-commerce VAT trends; no specific document opened.",
        }
    ]
    # The student-budget/schedule claim and the competitor-capability claim
    # (both directly in normalized_problem_statement above) have no
    # evidence record anywhere in this contract -- 0.3.0 has no
    # status.claim_ledger field to hold one even if someone tried.
    return c


def build_corrected_contract_0_4_0() -> dict:
    c = new_contract(
        task_id="ksa-food-delivery-riyadh-corrected-run",
        raw_user_brief=(
            "Create a PRD for a university-student food-delivery application in one city near "
            "one university."
        ),
        normalized_problem_statement=(
            "A first-draft PRD is needed for a single-city, single-campus-adjacent university-"
            "student food-delivery pilot. The specific city/campus was not named in the request "
            "and required clarification. Several claims about student budgets, competitor "
            "behavior, and regulatory treatment are directional and require disclosed evidence "
            "labels rather than being asserted as settled fact."
        ),
        goal=(
            "Produce a first-draft PRD for a university-student food-delivery pilot, with every "
            "material factual claim mapped to a claim-ledger entry at an honestly-labeled "
            "evidence strength, and the pilot city/campus confirmed rather than silently assumed."
        ),
        target_users=["university students in the confirmed pilot city", "the founder"],
        expected_deliverables=[{"name": "prd", "description": "The PRD document"}],
        risk_overlays=["informational"],
        risk_level="medium",
    )
    _sec(c, "routing")["domain_packs"] = [
        {"pack_id": "software", "version": "0.1.0"},
        {"pack_id": "research", "version": "0.1.0"},
    ]
    _sec(c, "scope")["open_questions"] = [
        {
            "question": "Which specific city and campus should the pilot target? A single city "
            "near one university was requested, but no specific city/campus was named.",
            "classification": "high_value",
            "resolution_status": "answered",
            "answer": "Riyadh, piloting near King Saud University -- confirmed by the user, not "
            "assumed by the Skill.",
        },
        {
            "question": "Standalone marketplace vs. university/merchant partnership for this draft?",
            "classification": "high_value",
            "resolution_status": "defaulted",
            "default_applied": "Assumed standalone marketplace for this draft's scope, with "
            "partnership noted as an alternative worth researching later -- deferred under the "
            "clarification-question budget.",
        },
    ]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "pilot-city-confirmed-not-assumed",
            "description": "The pilot city/campus is either user-confirmed or an explicit "
            "placeholder, never silently promoted from an illustrative example",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "scope.open_questions records the city/campus decision with "
            "resolution_status 'answered' or an explicit placeholder default",
        },
        {
            "id": "material-claims-mapped-to-ledger",
            "description": "Every material factual claim in the PRD (problem statement, market "
            "size, regulatory feasibility, risk severity) has a status.claim_ledger entry",
            "priority": "must",
            "verification_method": "automated_test",
            "evidence_required": "evidence.json's unmapped_material_claims is empty",
        },
        {
            "id": "regulatory-claims-preserve-conditions",
            "description": "Conditional regulatory rules (e.g. ZATCA VAT deemed-supplier "
            "treatment) keep their actual conditions, never generalized to a universal rule",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "the relevant claim_ledger entry's scope_and_qualifiers states "
            "the source's actual conditions",
        },
        {
            "id": "no-secondary-source-presented-as-primary",
            "description": "No secondary source is recorded with primary/official authority",
            "priority": "must",
            "verification_method": "automated_test",
            "evidence_required": "no claim_ledger entry combines SECONDARY_SOURCE_SUPPORTED with "
            "authority_level primary_official (schema-enforced, re-verified here)",
        },
    ]
    budget = _sec(c, "budget")
    budget["max_clarification_questions"] = 3
    budget["research_depth"] = "shallow"

    status = _sec(c, "status")
    status["completion_status"] = "partial"
    status["verified_facts"] = [
        {
            "statement": "The pilot city and campus were explicitly confirmed by the user in this "
            "conversation.",
            "evidence_label": "USER_CONFIRMED",
            "source": "Direct user confirmation in this conversation.",
        }
    ]
    status["unverified_claims"] = [
        {
            "statement": "Whether the standalone-marketplace business model outperforms a "
            "university/merchant partnership for this specific pilot.",
            "reason": "Deferred under the clarification-question budget; restated here for the "
            "report.",
            "evidence_label": "ASSUMPTION",
        }
    ]
    status["residual_risks"] = [
        {
            "risk": "The ZATCA VAT deemed-supplier treatment and the rider-classification claim "
            "both rest on secondary sources only; if official guidance turns out to impose "
            "additional obligations, the compliance section of this PRD would need rework before "
            "a build/launch decision.",
            "severity": "critical",
            "mitigation": "Both claims are explicitly flagged in status.claim_ledger as requiring "
            "primary/official confirmation before this PRD is used for a build decision -- this "
            "is a disclosed limitation of a first-draft PRD, not a defect in the analysis "
            "performed.",
            "affects_deliverable_validity": False,
        }
    ]
    status["remaining_uncertainty"] = [
        "Business model (standalone vs. partnership) remains an open, deferred question.",
        "Official/primary confirmation for the ZATCA VAT and rider-classification claims has not "
        "been obtained -- see status.claim_ledger.",
    ]
    status["claim_ledger"] = [
        {
            "claim_id": "student-budget-schedule",
            "claim": "Target university students have narrower discretionary budgets and more "
            "rigid daily schedules than the general urban population in the pilot city",
            "evidence_label": "RESEARCH_NEEDED",
            "evaluator_type": "ai_model",
            "scope_and_qualifiers": "Directional claim only; no specific figures asserted; not "
            "verified against local survey or spending data for this specific market.",
            "affects": ["problem_definition"],
        },
        {
            "claim_id": "competitor-gap",
            "claim": "Major food-delivery platforms operating in the pilot city do not "
            "specifically optimize pricing or scheduling for university-student budgets/schedules",
            "evidence_label": "RESEARCH_NEEDED",
            "evaluator_type": "ai_model",
            "scope_and_qualifiers": "No competitor app audit was performed this session; based on "
            "general familiarity only, not a systematic review.",
            "affects": ["market_size", "problem_definition"],
        },
        {
            "claim_id": "zatca-deemed-supplier",
            "claim": "Saudi ZATCA e-marketplace VAT deemed-supplier treatment may apply to this "
            "marketplace model",
            "evidence_label": "SECONDARY_SOURCE_SUPPORTED",
            "source_type": "professional_advisory",
            "authority_level": "secondary_professional",
            "source_url": ZATCA_URL,
            "source_title": ZATCA_TITLE,
            "publisher": "Example Tax Advisory",
            "access_date": "2026-09-17",
            "excerpt_or_locator": "Section 3: deemed-supplier treatment applies to an electronic "
            "marketplace when the underlying supplier is a resident not registered for VAT, "
            "among other conditions.",
            "scope_and_qualifiers": "Conditional: applies only to specific supplier categories "
            "(e.g. resident, non-VAT-registered suppliers) and other stated conditions -- does "
            "not apply to every marketplace or every supplier arrangement universally.",
            "evaluator_type": "ai_model",
            "limitations": "No primary ZATCA regulation or official guidance document was "
            "inspected; official/professional confirmation for this exact operating model is "
            "still required before a build/launch decision.",
            "affects": ["legal_or_regulatory_feasibility", "risk_severity"],
        },
        {
            "claim_id": "rider-employment-status",
            "claim": "Delivery riders under this model may face regulatory scrutiny over worker "
            "classification, per secondary reporting on gig-economy trends in Saudi Arabia",
            "evidence_label": "SECONDARY_SOURCE_SUPPORTED",
            "source_type": "news_report",
            "authority_level": "secondary_general",
            "source_url": RIDER_URL,
            "source_title": RIDER_TITLE,
            "publisher": "Example News",
            "access_date": "2026-09-17",
            "excerpt_or_locator": "Paragraph 4: discusses general gig-economy worker "
            "classification debates in the region, not a specific ruling on this operating model.",
            "scope_and_qualifiers": "Based on secondary news reporting about general gig-economy "
            "classification trends, not a specific regulatory ruling on this exact operating "
            "model.",
            "evaluator_type": "ai_model",
            "limitations": "The corresponding official regulatory source was not inspected; "
            "treat as an unconfirmed, disclosed risk, not a settled legal conclusion.",
            "affects": ["legal_or_regulatory_feasibility", "risk_severity"],
        },
        {
            "claim_id": "conversion-target-threshold",
            "claim": "Suggested 15% trial-to-repeat conversion target for the pilot's first "
            "90 days",
            "evidence_label": "MODEL_EVALUATED",
            "evaluator_type": "ai_model",
            "scope_and_qualifiers": "none; a suggested internal target for this draft, not "
            "benchmarked against an external source.",
            "affects": ["acceptance_thresholds"],
        },
    ]
    return c


DEFECTIVE_EVIDENCE = {
    "hard_constraint_results": {},
    "dimension_scores": {},
    "acceptance_criteria_results": {
        "zatca-section-accurate": {"met": True, "evidence_label": "VERIFIED"},
    },
    "authorization_violations": [],
    "unmapped_material_claims": [
        "University students in Riyadh have narrower discretionary budgets and more rigid daily "
        "schedules than the general population (asserted in the problem statement with no "
        "evidence record of any kind).",
        "Major food-delivery platforms do not specifically optimize for university-student needs "
        "(asserted with no evidence record of any kind).",
    ],
}

CORRECTED_EVIDENCE = {
    "hard_constraint_results": {},
    "dimension_scores": {},
    "acceptance_criteria_results": {
        "pilot-city-confirmed-not-assumed": {"met": True, "evidence_label": "VERIFIED"},
        "material-claims-mapped-to-ledger": {"met": True, "evidence_label": "MEASURED"},
        "regulatory-claims-preserve-conditions": {"met": True, "evidence_label": "MODEL-EVALUATED"},
        "no-secondary-source-presented-as-primary": {"met": True, "evidence_label": "MEASURED"},
    },
    "authorization_violations": [],
    "unmapped_material_claims": [],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dump_document(build_defective_contract_0_3_0(), OUT / "contract_defective.toml")
    dump_document(build_corrected_contract_0_4_0(), OUT / "contract_corrected.toml")
    (OUT / "evidence_defective.json").write_text(
        json.dumps(DEFECTIVE_EVIDENCE, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT / "evidence_corrected.json").write_text(
        json.dumps(CORRECTED_EVIDENCE, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote fixtures to {OUT}")


if __name__ == "__main__":
    main()
