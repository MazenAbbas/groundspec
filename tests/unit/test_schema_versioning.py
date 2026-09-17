"""Confirms the 0.1.0 -> 0.2.0 contract schema change is purely additive and
backward compatible: 0.1.0 documents keep validating against the untouched
0.1.0 schema file forever, and the new 'high_value' open-question
classification exists only in 0.2.0. See docs/architecture.md's schema
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


def test_both_schema_versions_are_supported():
    assert "0.1.0" in SUPPORTED_CONTRACT_VERSIONS
    assert "0.2.0" in SUPPORTED_CONTRACT_VERSIONS


def test_new_contracts_default_to_0_2_0():
    contract = _minimal_contract()
    assert contract["contract_schema_version"] == "0.2.0"
    assert validate_contract_dict(contract) == []


def test_0_1_0_documents_remain_valid_forever():
    contract = _minimal_contract()
    contract["contract_schema_version"] = "0.1.0"
    assert validate_contract_dict(contract) == []


def test_high_value_classification_only_exists_in_0_2_0():
    contract = _minimal_contract()
    contract["scope"]["open_questions"] = [
        {"question": "q", "classification": "high_value", "resolution_status": "open"}
    ]

    contract["contract_schema_version"] = "0.2.0"
    assert validate_contract_dict(contract) == []

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

    # Everything else in $defs is untouched between versions.
    defs_01 = dict(schema_01["$defs"])
    defs_02 = dict(schema_02["$defs"])
    del defs_01["open_question"]
    del defs_02["open_question"]
    assert defs_01 == defs_02
