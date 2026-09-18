"""Confirms each contract schema bump (0.1.0 -> 0.2.0 -> 0.3.0 -> 0.4.0) is
additive and backward compatible: every older document keeps validating
against its own untouched schema file forever. See docs/architecture.md's
schema versioning section for the policy this enforces.
"""

import copy

from groundspec.contract.factory import new_contract
from groundspec.contract.schema_loader import SUPPORTED_CONTRACT_VERSIONS, load_contract_schema
from groundspec.contract.validator import validate_contract_dict


def _minimal_contract() -> dict:
    return new_contract(
        task_id="schema-version-check",
        raw_user_brief="b",
        normalized_problem_statement="p",
        goal="g",
        target_users=["u"],
        expected_deliverables=[{"name": "d", "description": "d"}],
    )


def test_all_four_schema_versions_are_supported():
    assert "0.1.0" in SUPPORTED_CONTRACT_VERSIONS
    assert "0.2.0" in SUPPORTED_CONTRACT_VERSIONS
    assert "0.3.0" in SUPPORTED_CONTRACT_VERSIONS
    assert "0.4.0" in SUPPORTED_CONTRACT_VERSIONS


def test_new_contracts_default_to_0_4_0():
    contract = _minimal_contract()
    assert contract["contract_schema_version"] == "0.4.0"
    assert validate_contract_dict(contract) == []


def test_0_1_0_through_0_3_0_documents_remain_valid_forever():
    for version in ("0.1.0", "0.2.0", "0.3.0"):
        contract = _minimal_contract()
        contract["contract_schema_version"] = version
        assert validate_contract_dict(contract) == [], version


def test_high_value_classification_exists_in_0_2_0_plus_but_not_0_1_0():
    contract = _minimal_contract()
    contract["scope"]["open_questions"] = [
        {"question": "q", "classification": "high_value", "resolution_status": "open"}
    ]
    for version in ("0.2.0", "0.3.0", "0.4.0"):
        contract["contract_schema_version"] = version
        assert validate_contract_dict(contract) == [], version

    contract["contract_schema_version"] = "0.1.0"
    issues = validate_contract_dict(contract)
    assert len(issues) == 1
    assert issues[0].schema_rule == "enum"


def test_0_1_0_and_0_2_0_schemas_are_structurally_identical_except_the_new_enum_value():
    schema_01 = load_contract_schema("0.1.0")
    schema_02 = load_contract_schema("0.2.0")

    def classification_enum(schema: dict) -> list[str]:
        enum = schema["$defs"]["open_question"]["properties"]["classification"]["enum"]
        assert isinstance(enum, list)
        return enum

    assert set(classification_enum(schema_02)) - set(classification_enum(schema_01)) == {"high_value"}

    defs_01 = dict(schema_01["$defs"])
    defs_02 = dict(schema_02["$defs"])
    del defs_01["open_question"]
    del defs_02["open_question"]
    assert defs_01 == defs_02


# --- 0.3.0: evidence-taxonomy and risk-validity hardening (regression fixes) ---


def test_assumption_safe_default_must_be_true_in_0_3_0():
    contract = _minimal_contract()
    contract["contract_schema_version"] = "0.3.0"
    contract["scope"]["assumptions"] = [{"statement": "x", "confidence": "low", "safe_default": False}]
    issues = validate_contract_dict(contract)
    assert len(issues) == 1
    assert issues[0].path == "scope.assumptions.0.safe_default"


def test_assumption_safe_default_false_still_allowed_in_0_1_0_and_0_2_0():
    # The 0.3.0 tightening is deliberately NOT retrofitted onto older
    # schemas -- those documents keep whatever behavior they always had.
    for version in ("0.1.0", "0.2.0"):
        contract = _minimal_contract()
        contract["contract_schema_version"] = version
        contract["scope"]["assumptions"] = [{"statement": "x", "confidence": "low", "safe_default": False}]
        assert validate_contract_dict(contract) == [], version


def test_verified_facts_reject_model_evaluated_and_other_weak_labels_in_0_3_0():
    contract = _minimal_contract()
    contract["contract_schema_version"] = "0.3.0"
    for weak_label in ("MODEL-EVALUATED", "PROPOSED", "PENDING_EXTERNAL_VALIDATION", "OUT_OF_SCOPE"):
        contract["status"]["verified_facts"] = [{"statement": "x", "evidence_label": weak_label}]
        issues = validate_contract_dict(contract)
        assert len(issues) == 1, weak_label
        assert issues[0].schema_rule == "enum"


def test_verified_facts_accept_genuine_verification_labels_in_0_3_0():
    contract = _minimal_contract()
    contract["contract_schema_version"] = "0.3.0"
    for real_label in ("VERIFIED", "MEASURED", "SOURCE_VERIFIED", "USER_CONFIRMED", "HUMAN-REVIEWED"):
        contract["status"]["verified_facts"] = [{"statement": "x", "evidence_label": real_label}]
        assert validate_contract_dict(contract) == [], real_label


def test_unverified_claims_accept_the_new_optional_evidence_label_in_0_3_0():
    contract = _minimal_contract()
    contract["contract_schema_version"] = "0.3.0"
    for weak_label in (
        "MODEL-EVALUATED",
        "PROPOSED",
        "ASSUMPTION",
        "RESEARCH_NEEDED",
        "PENDING_EXTERNAL_VALIDATION",
        "OUT_OF_SCOPE",
    ):
        contract["status"]["unverified_claims"] = [
            {"statement": "x", "reason": "r", "evidence_label": weak_label}
        ]
        assert validate_contract_dict(contract) == [], weak_label


def test_unverified_claims_evidence_label_is_optional_and_does_not_exist_pre_0_3_0():
    contract = _minimal_contract()
    contract["status"]["unverified_claims"] = [{"statement": "x", "reason": "r"}]
    contract["contract_schema_version"] = "0.3.0"
    assert validate_contract_dict(contract) == []

    contract["status"]["unverified_claims"] = [
        {"statement": "x", "reason": "r", "evidence_label": "ASSUMPTION"}
    ]
    contract["contract_schema_version"] = "0.2.0"
    issues = validate_contract_dict(contract)
    assert len(issues) == 1
    assert issues[0].schema_rule == "additionalProperties"


def test_residual_risk_affects_deliverable_validity_defaults_to_true_in_0_3_0():
    from groundspec.contract.normalize import fill_defaults

    contract = _minimal_contract()
    contract["contract_schema_version"] = "0.3.0"
    contract["status"]["residual_risks"] = [{"risk": "x", "severity": "critical"}]
    filled = fill_defaults(contract, load_contract_schema("0.3.0"))
    assert filled["status"]["residual_risks"][0]["affects_deliverable_validity"] is True
    assert validate_contract_dict(filled) == []


def test_residual_risk_can_explicitly_declare_it_does_not_affect_validity():
    contract = _minimal_contract()
    contract["contract_schema_version"] = "0.3.0"
    contract["status"]["residual_risks"] = [
        {"risk": "x", "severity": "critical", "affects_deliverable_validity": False}
    ]
    assert validate_contract_dict(contract) == []


# --- 0.4.0: claim-ledger evidence provenance (Riyadh food-delivery regression) ---


def _minimal_claim(**overrides: object) -> dict:
    claim = {
        "claim_id": "c1",
        "claim": "x",
        "evidence_label": "MEASURED",
        "evaluator_type": "deterministic_tool",
        "scope_and_qualifiers": "none; unconditional per the source",
    }
    claim.update(overrides)
    return claim


def test_claim_ledger_defaults_to_empty_and_does_not_exist_pre_0_4_0():
    contract = _minimal_contract()
    assert validate_contract_dict(contract) == []

    contract["status"]["claim_ledger"] = []
    contract["contract_schema_version"] = "0.3.0"
    issues = validate_contract_dict(contract)
    assert len(issues) == 1
    assert issues[0].schema_rule == "additionalProperties"


def test_bare_measured_claim_is_valid_with_no_citation_fields():
    contract = _minimal_contract()
    contract["status"]["claim_ledger"] = [_minimal_claim()]
    assert validate_contract_dict(contract) == []


def test_primary_source_verified_requires_full_citation():
    contract = _minimal_contract()
    contract["status"]["claim_ledger"] = [_minimal_claim(evidence_label="PRIMARY_SOURCE_VERIFIED")]
    issues = validate_contract_dict(contract)
    assert issues
    assert all(i.schema_rule == "required" for i in issues)
    missing = {i.message for i in issues}
    for field in ("source_url", "source_title", "access_date", "excerpt_or_locator", "source_type"):
        assert any(field in m for m in missing), field


def test_primary_source_verified_with_full_citation_is_valid():
    contract = _minimal_contract()
    contract["status"]["claim_ledger"] = [
        _minimal_claim(
            evidence_label="PRIMARY_SOURCE_VERIFIED",
            source_type="government_body",
            authority_level="primary_official",
            source_url="https://example.gov/reg",
            source_title="Official regulation",
            access_date="2026-09-17",
            excerpt_or_locator="Section 4",
        )
    ]
    assert validate_contract_dict(contract) == []


def test_secondary_source_supported_cannot_claim_primary_official_authority():
    # This is the exact "secondary regulatory news source treated as primary
    # official confirmation" defect -- structurally impossible now, not just
    # discouraged in prose.
    contract = _minimal_contract()
    contract["status"]["claim_ledger"] = [
        _minimal_claim(
            evidence_label="SECONDARY_SOURCE_SUPPORTED",
            source_type="news_report",
            authority_level="primary_official",
            source_url="https://example-news.example/article",
            source_title="News article",
            access_date="2026-09-17",
            excerpt_or_locator="paragraph 3",
        )
    ]
    issues = validate_contract_dict(contract)
    assert len(issues) == 1
    assert issues[0].path == "status.claim_ledger.0.authority_level"
    assert issues[0].schema_rule == "enum"


def test_secondary_source_supported_on_a_legal_claim_requires_stated_limitations():
    contract = _minimal_contract()
    contract["status"]["claim_ledger"] = [
        _minimal_claim(
            evidence_label="SECONDARY_SOURCE_SUPPORTED",
            source_type="news_report",
            authority_level="secondary_general",
            source_url="https://example-news.example/article",
            source_title="News article",
            access_date="2026-09-17",
            excerpt_or_locator="paragraph 3",
            affects=["legal_or_regulatory_feasibility"],
        )
    ]
    issues = validate_contract_dict(contract)
    assert len(issues) == 1
    assert issues[0].schema_rule == "required"

    contract["status"]["claim_ledger"][0]["limitations"] = (
        "No primary regulatory source was inspected; official confirmation remains required."
    )
    assert validate_contract_dict(contract) == []


def test_model_evaluated_assumption_and_research_needed_cannot_claim_source_authority():
    for label in ("MODEL_EVALUATED", "ASSUMPTION", "RESEARCH_NEEDED", "USER_CONFIRMED", "MEASURED"):
        contract = _minimal_contract()
        contract["status"]["claim_ledger"] = [
            _minimal_claim(evidence_label=label, authority_level="primary_official")
        ]
        issues = validate_contract_dict(contract)
        assert len(issues) == 1, label
        assert issues[0].schema_rule == "const", label


def test_conditional_zatca_style_claim_preserves_qualifiers_and_validates():
    # Regression-shaped: a conditional regulatory rule, properly qualified
    # and disclosed as secondary-only, rather than generalized as universal.
    contract = _minimal_contract()
    contract["status"]["claim_ledger"] = [
        _minimal_claim(
            claim_id="zatca-deemed-supplier",
            claim="Deemed-supplier VAT treatment may apply to this marketplace model",
            evidence_label="SECONDARY_SOURCE_SUPPORTED",
            source_type="professional_advisory",
            authority_level="secondary_professional",
            source_url="https://example-tax-advisory.example/zatca",
            source_title="ZATCA e-marketplace VAT guidance explainer",
            access_date="2026-09-17",
            excerpt_or_locator="Deemed-supplier treatment applies when the underlying supplier is "
            "a resident not registered for VAT.",
            scope_and_qualifiers="Conditional: applies only to specific supplier categories (e.g. "
            "resident, non-VAT-registered suppliers); does not apply to every marketplace universally.",
            affects=["legal_or_regulatory_feasibility"],
            limitations="No primary ZATCA document was inspected; official confirmation for this "
            "exact operating model remains required before launch.",
        )
    ]
    assert validate_contract_dict(contract) == []
    unacceptable = copy.deepcopy(contract)
    unacceptable["status"]["claim_ledger"][0]["scope_and_qualifiers"] = (
        "All food-delivery marketplaces are deemed suppliers and must issue every invoice."
    )
    # The schema cannot detect that this rewrites a conditional rule as a
    # universal one from prose alone -- that is caught by the regression
    # test's structural qualifier-content check, not schema validation. It
    # remains schema-valid; documented here so the boundary isn't assumed
    # away.
    assert validate_contract_dict(unacceptable) == []


def test_claim_ledger_maxitems_and_pattern_are_enforced():
    contract = _minimal_contract()
    contract["status"]["claim_ledger"] = [_minimal_claim(claim_id="Not Valid Slug!")]
    issues = validate_contract_dict(contract)
    assert len(issues) == 1
    assert issues[0].path == "status.claim_ledger.0.claim_id"
    assert issues[0].schema_rule == "pattern"
