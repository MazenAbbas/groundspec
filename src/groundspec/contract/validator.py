"""Strict validation of Task Contracts and Rule Packs against their JSON Schemas.

No silent type coercion, no defaults invented here (see normalize.py for the
separate, explicit default-filling step), unknown keys always rejected
because every object schema sets ``additionalProperties: false``.
"""

from __future__ import annotations

from dataclasses import dataclass

import jsonschema

from groundspec.contract.schema_loader import (
    UnsupportedSchemaVersion,
    load_contract_schema,
    load_rule_pack_schema,
)


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    schema_rule: str

    def __str__(self) -> str:
        location = self.path or "<root>"
        return f"{location}: {self.message} (rule: {self.schema_rule})"


class SchemaValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        summary = "\n".join(str(issue) for issue in issues)
        super().__init__(f"{len(issues)} validation issue(s):\n{summary}")


def _collect(data: object, schema: dict[str, object]) -> list[ValidationIssue]:
    validator_cls = jsonschema.Draft202012Validator
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    issues: list[ValidationIssue] = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in error.absolute_path)
        rule = str(error.validator)
        issues.append(ValidationIssue(path=path, message=error.message, schema_rule=rule))
    return issues


def validate_contract_dict(data: object, *, version: str | None = None) -> list[ValidationIssue]:
    """Validate a raw dict against the Task Contract schema.

    Does not raise; returns the (possibly empty) list of issues so callers
    can decide how to report them.
    """
    declared = version
    if declared is None:
        if isinstance(data, dict) and isinstance(data.get("contract_schema_version"), str):
            declared = data["contract_schema_version"]
        else:
            return [
                ValidationIssue(
                    path="contract_schema_version",
                    message="missing or not a string; cannot select a schema to validate against",
                    schema_rule="required",
                )
            ]
    try:
        schema = load_contract_schema(declared)
    except UnsupportedSchemaVersion as exc:
        return [ValidationIssue(path="contract_schema_version", message=str(exc), schema_rule="version")]
    return _collect(data, schema)


def validate_rule_pack_dict(data: object, *, version: str | None = None) -> list[ValidationIssue]:
    declared = version
    if declared is None:
        if isinstance(data, dict) and isinstance(data.get("rule_pack_schema_version"), str):
            declared = data["rule_pack_schema_version"]
        else:
            return [
                ValidationIssue(
                    path="rule_pack_schema_version",
                    message="missing or not a string; cannot select a schema to validate against",
                    schema_rule="required",
                )
            ]
    try:
        schema = load_rule_pack_schema(declared)
    except UnsupportedSchemaVersion as exc:
        return [ValidationIssue(path="rule_pack_schema_version", message=str(exc), schema_rule="version")]
    return _collect(data, schema)


def require_valid_contract(data: object, *, version: str | None = None) -> dict[str, object]:
    issues = validate_contract_dict(data, version=version)
    if issues:
        raise SchemaValidationError(issues)
    assert isinstance(data, dict)
    return data


def require_valid_rule_pack(data: object, *, version: str | None = None) -> dict[str, object]:
    issues = validate_rule_pack_dict(data, version=version)
    if issues:
        raise SchemaValidationError(issues)
    assert isinstance(data, dict)
    return data
