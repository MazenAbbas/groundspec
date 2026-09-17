"""Confirms each contract schema bump (0.1.0 -> 0.2.0 -> 0.3.0) is additive
and backward compatible: every older document keeps validating against its
own untouched schema file forever. See docs/architecture.md's schema
versioning section for the policy this enforces.
"""

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


def test_all_three_schema_versions_are_supported():
    assert "0.1.0" in SUPPORTED_CONTRACT_VERSIONS
    assert "0.2.0" in SUPPORTED_CONTRACT_VERSIONS
    assert "0.3.0" in SUPPORTED_CONTRACT_VERSIONS


def test_new_contracts_default_to_0_3_0():
    contract = _minimal_contract()
    assert contract["contract_schema_version"] == "0.3.0"
    assert validate_contract_dict(contract) == []


def test_0_1_0_and_0_2_0_documents_remain_valid_forever():
    for version in ("0.1.0", "0.2.0"):
        contract = _minimal_contract()
        contract["contract_schema_version"] = version
        assert validate_contract_dict(contract) == [], version


def test_high_value_classification_exists_in_0_2_0_and_0_3_0_but_not_0_1_0():
    contract = _minimal_contract()
    contract["scope"]["open_questions"] = [
        {"question": "q", "classification": "high_value", "resolution_status": "open"}
    ]
    for version in ("0.2.0", "0.3.0"):
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
