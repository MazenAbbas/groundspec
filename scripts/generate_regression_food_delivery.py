"""Generates the food-delivery regression fixtures under
tests/regression/food_delivery_v0_2_0rc1/ (PRD-style user test that
exposed real v0.2.0rc1 defects -- see that directory's README.md).

Not part of the installed package; a dev-only, re-runnable generator,
exactly like scripts/generate_examples.py and
scripts/generate_metaskill_examples.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from groundspec.contract.factory import new_contract
from groundspec.contract.serialization import dump_document

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "regression" / "food_delivery_v0_2_0rc1"


def _sec(contract: dict, key: str) -> dict:
    return contract[key]  # type: ignore[return-value]


def build_defective_contract_0_2_0() -> dict:
    """Reproduces, under the OLD (0.2.0) schema, the exact pattern the live
    test exhibited: a 'must' criterion's evidence is the executor's own
    self-review, recorded as a *verified* fact -- valid under 0.2.0,
    rejected by 0.3.0 (see the paired test)."""
    c = new_contract(
        task_id="ksa-food-delivery-defective-run",
        raw_user_brief=(
            "Use Groundspec in Guided mode to create a PRD for a Saudi university-student "
            "food-delivery application. Clearly separate verified facts, assumptions, and items "
            "requiring external research. Do not publish anything or perform any external action."
        ),
        normalized_problem_statement="No PRD exists yet for this concept.",
        goal="Produce a PRD for a Saudi university-student food-delivery concept.",
        target_users=["Saudi university students", "the founder deciding whether to pursue this"],
        expected_deliverables=[{"name": "prd", "description": "The PRD document"}],
        risk_overlays=["informational"],
        risk_level="low",
    )
    c["contract_schema_version"] = "0.2.0"
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "bnpl-section-accurate",
            "description": "The buy-now-pay-later (BNPL) market section accurately reflects the cited paper",
            "priority": "must",
            "verification_method": "automated_test",
            "evidence_required": "the cited source was actually read and matches the claim",
        }
    ]
    # This is exactly the defect: a self-review, recorded as VERIFIED, for a
    # criterion whose own verification_method demanded real evidence -- and
    # the paper was admittedly not read in full.
    _sec(c, "status")["verified_facts"] = [
        {
            "statement": "The BNPL section is accurate.",
            "evidence_label": "MODEL-EVALUATED",
            "source": "Self-assessment; the underlying paper was not read in full.",
        }
    ]
    return c


def build_corrected_contract_0_3_0() -> dict:
    c = new_contract(
        task_id="ksa-food-delivery-corrected-run",
        raw_user_brief=(
            "Use Groundspec in Guided mode to create a PRD for a Saudi university-student "
            "food-delivery application. Clearly separate verified facts, assumptions, and items "
            "requiring external research. Do not publish anything or perform any external action."
        ),
        normalized_problem_statement=(
            "No PRD exists yet for this concept, and several materially outcome-changing product "
            "decisions (scope, business model, research authorization) are unresolved."
        ),
        goal=(
            "Produce a first-draft PRD for a Saudi university-student food-delivery concept, with "
            "verified facts, assumptions, and external-research gaps kept explicitly distinct, and "
            "no external/network action taken."
        ),
        target_users=["Saudi university students", "the founder deciding whether to pursue this"],
        expected_deliverables=[{"name": "prd", "description": "The PRD document"}],
        risk_overlays=["informational"],
        risk_level="medium",
    )
    _sec(c, "routing")["domain_packs"] = [
        {"pack_id": "software", "version": "0.1.0"},
        {"pack_id": "research", "version": "0.1.0"},
    ]
    auth = _sec(_sec(c, "routing"), "authorization")
    auth["boundaries"] = [
        "No external action of any kind for this task: no network access, no web search or fetch, "
        "no publishing, no messages -- verbatim from the user's own request, recorded here unedited."
    ]
    auth["requires_confirmation_for"] = ["any network access", "any publishing action"]

    _sec(c, "scope")["non_goals"] = [
        "Performing any network research this session (explicitly prohibited by the user)",
        "A finished, launch-ready PRD -- this is a first draft with explicit open questions",
    ]
    _sec(c, "scope")["open_questions"] = [
        {
            "question": (
                "Before scoping the PRD: (a) is this a research-only concept exploration or a "
                "specific launch plan; (b) single-campus vs. city-wide vs. national scope; "
                "(c) standalone marketplace vs. university/merchant partnership; (d) is external "
                "web research authorized for this session? (one compact question covering the "
                "most material choices, per the Skill's clarification policy)"
            ),
            "classification": "blocking",
            "resolution_status": "answered",
            "answer": (
                "(a) a specific, if early-stage, launch-oriented PRD, not pure exploration; "
                "(b) single-campus pilot; (c) standalone marketplace for this draft's scope, with "
                "partnership noted as an alternative worth researching later; (d) no external "
                "research authorized -- work entirely from locally available reasoning."
            ),
        },
        {
            "question": "Target persona/segment within the student population?",
            "classification": "high_value",
            "resolution_status": "defaulted",
            "default_applied": (
                "Assumed the general undergraduate population rather than a narrower subsegment "
                "(e.g. dorm-only residents) -- deferred under the clarification-question budget, "
                "recorded here rather than silently folded into an assumption."
            ),
        },
        {
            "question": "Payment methods to support at launch?",
            "classification": "high_value",
            "resolution_status": "defaulted",
            "default_applied": (
                "Assumed card + a local digital wallet as the primary methods, with cash-on-delivery "
                "flagged as needing validation before commit -- deferred under budget, not asked."
            ),
        },
        {
            "question": "Primary language/localization for the product?",
            "classification": "high_value",
            "resolution_status": "defaulted",
            "default_applied": "Assumed Arabic-first with English support, deferred under budget.",
        },
        {
            "question": "Monetization model (commission, subscription, delivery fee, or a mix)?",
            "classification": "high_value",
            "resolution_status": "open",
        },
    ]
    _sec(c, "acceptance")["criteria"] = [
        {
            "id": "pilot-scope-explicit",
            "description": "The PRD states an explicit, non-ambiguous pilot geographic scope",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "the scope section names a specific campus/city, not a vague range",
        },
        {
            "id": "highest-risk-assumptions-ranked",
            "description": "At least 3 highest-risk assumptions are explicitly identified and ranked",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "the PRD's risk section lists and orders them",
        },
        {
            "id": "no-unauthorized-network-access",
            "description": "No network-capable tool call was made during this session",
            "priority": "must",
            "verification_method": "automated_test",
            "evidence_required": "the session's own tool-call log shows zero network-capable calls",
        },
        {
            "id": "evidence-correctly-labeled",
            "description": "Every claim uses the correct evidence label (no self-review recorded as verified)",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "status.verified_facts contains only genuinely-verified entries; "
            "anything else is in status.unverified_claims with an honest evidence_label",
        },
    ]
    budget = _sec(c, "budget")
    budget["max_clarification_questions"] = 3
    budget["research_depth"] = "none"

    status = _sec(c, "status")
    status["completion_status"] = "partial"
    status["verified_facts"] = [
        {
            "statement": "The request text and no other materials were available; no external source "
            "was consulted, per the user's explicit prohibition.",
            "evidence_label": "VERIFIED",
            "source": "Direct inspection of the conversation and this session's own tool-call log.",
        }
    ]
    status["unverified_claims"] = [
        {
            "statement": "Whether Saudi university students predominantly prefer card/wallet payment "
            "over cash-on-delivery for food delivery.",
            "reason": "External research was not authorized for this session, so this remains an open "
            "question pending a future, explicitly-authorized research pass.",
            "evidence_label": "RESEARCH_NEEDED",
        },
        {
            "statement": "Single-campus pilot scope, undergraduate-general persona, and the payment/"
            "language/monetization defaults above.",
            "reason": "Recorded as assumptions/deferred open questions; restated here for the report.",
            "evidence_label": "ASSUMPTION",
        },
    ]
    status["residual_risks"] = [
        {
            "risk": "The payment-method assumption (card/wallet over cash-on-delivery) is unverified; "
            "if wrong, the checkout section of this PRD would need significant rework.",
            "severity": "critical",
            "mitigation": "Explicitly flagged as the top research priority before this PRD is used "
            "for a build decision.",
            "affects_deliverable_validity": False,
        }
    ]
    status["remaining_uncertainty"] = [
        "Business model (standalone vs. partnership), monetization model, and three deferred "
        "high-value questions remain open -- see scope.open_questions.",
    ]
    return c


DEFECTIVE_EVIDENCE = {
    "hard_constraint_results": {},
    "dimension_scores": {},
    "acceptance_criteria_results": {
        "pilot-scope-explicit": {"met": True, "evidence_label": "VERIFIED"},
        "highest-risk-assumptions-ranked": {"met": True, "evidence_label": "VERIFIED"},
        "no-unauthorized-network-access": {"met": True, "evidence_label": "MODEL-EVALUATED"},
        "evidence-correctly-labeled": {"met": True, "evidence_label": "MODEL-EVALUATED"},
    },
    "authorization_violations": [
        "Performed 10 web searches during this session despite the user's explicit instruction "
        "'do not perform any external action.'"
    ],
}

CORRECTED_EVIDENCE = {
    "hard_constraint_results": {},
    "dimension_scores": {},
    "acceptance_criteria_results": {
        "pilot-scope-explicit": {"met": True, "evidence_label": "VERIFIED"},
        "highest-risk-assumptions-ranked": {"met": True, "evidence_label": "VERIFIED"},
        "no-unauthorized-network-access": {"met": True, "evidence_label": "MEASURED"},
        "evidence-correctly-labeled": {"met": True, "evidence_label": "VERIFIED"},
    },
    "authorization_violations": [],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dump_document(build_defective_contract_0_2_0(), OUT / "contract_defective.toml")
    dump_document(build_corrected_contract_0_3_0(), OUT / "contract_corrected.toml")
    (OUT / "evidence_defective.json").write_text(
        json.dumps(DEFECTIVE_EVIDENCE, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT / "evidence_corrected.json").write_text(
        json.dumps(CORRECTED_EVIDENCE, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote fixtures to {OUT}")


if __name__ == "__main__":
    main()
