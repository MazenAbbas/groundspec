from groundspec.contract.factory import new_contract
from groundspec.contract.normalize import fill_defaults
from groundspec.contract.schema_loader import load_contract_schema
from groundspec.contract.serialization import (
    canonical_json_dumps,
    canonical_json_loads,
    canonical_toml_dumps,
    canonical_toml_loads,
)
from groundspec.contract.validator import validate_contract_dict


def _minimal_contract() -> dict:
    return new_contract(
        task_id="write-launch-post",
        raw_user_brief="write a linkedin post announcing our launch",
        normalized_problem_statement="No announcement content exists for the product launch.",
        goal="Produce one LinkedIn post announcing the launch.",
        target_users=["prospective customers following the company page"],
        expected_deliverables=[{"name": "post_draft", "description": "Final LinkedIn post text"}],
    )


def test_factory_output_is_schema_valid():
    contract = _minimal_contract()
    issues = validate_contract_dict(contract)
    assert issues == [], "\n".join(str(i) for i in issues)


def test_unknown_top_level_key_is_rejected():
    contract = _minimal_contract()
    contract["unexpected_field"] = "should not be allowed"
    issues = validate_contract_dict(contract)
    assert any(i.schema_rule == "additionalProperties" for i in issues)


def test_missing_required_field_is_rejected():
    contract = _minimal_contract()
    del contract["brief"]["goal"]
    issues = validate_contract_dict(contract)
    assert any("required" in i.schema_rule for i in issues)


def test_wrong_type_is_not_coerced():
    contract = _minimal_contract()
    contract["budget"]["time_budget_minutes"] = "sixty"
    issues = validate_contract_dict(contract)
    assert any(i.path == "budget.time_budget_minutes" for i in issues)


def test_unsupported_schema_version_is_rejected():
    contract = _minimal_contract()
    contract["contract_schema_version"] = "99.0.0"
    issues = validate_contract_dict(contract)
    assert len(issues) == 1
    assert issues[0].path == "contract_schema_version"


def test_json_canonical_dump_is_deterministic_regardless_of_key_order():
    contract = _minimal_contract()
    reordered = dict(reversed(list(contract.items())))
    assert canonical_json_dumps(contract) == canonical_json_dumps(reordered)


def test_json_roundtrip_preserves_semantics():
    contract = _minimal_contract()
    text = canonical_json_dumps(contract)
    restored = canonical_json_loads(text)
    assert restored == contract


def test_toml_roundtrip_preserves_semantics_after_default_fill():
    contract = fill_defaults(_minimal_contract(), load_contract_schema("0.1.0"))
    toml_text = canonical_toml_dumps(contract)
    restored = canonical_toml_loads(toml_text)
    restored_filled = fill_defaults(restored, load_contract_schema("0.1.0"))
    assert restored_filled == contract
    assert validate_contract_dict(restored_filled) == []


def test_toml_output_is_deterministic():
    contract = fill_defaults(_minimal_contract(), load_contract_schema("0.1.0"))
    first = canonical_toml_dumps(contract)
    second = canonical_toml_dumps(dict(reversed(list(contract.items()))))
    assert first == second
