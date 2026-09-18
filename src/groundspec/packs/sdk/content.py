"""Loaders and structural validators for a Domain Pack's secondary content
files: ``questions.toml``, ``evidence-policy.toml``, ``acceptance-templates.toml``,
``completion-gates.toml``, and ``tests/scenarios.toml``.

These are hand-validated (isinstance/regex checks) rather than given their
own JSON Schema files, unlike the manifest (``pack.toml``, validated against
``domain_pack.v0_1_0.schema.json``) and rules (``rule_pack.v0_1_0.schema.json``,
already schema-validated by the existing loader). This is a deliberate,
documented scope trade-off for this release -- see docs/pack-authoring-guide.md
-- not an oversight: these files are simpler, flatter structures where a
hand-written check is exactly as strict and considerably less code than a
five-schema-file bundle would be.

Every one of these files is pure data: read, validated, and (for
completion gates) evaluated through the existing safe condition DSL
(``groundspec.rules.condition``). None of it is ever executed as code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from groundspec.contract.serialization import UnknownFileFormat, load_document
from groundspec.packs.sdk.errors import PackContentError

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
_VALID_GATE_ACTIONS = frozenset({"downgrade_to_caveats", "downgrade_to_incomplete", "downgrade_to_fail"})
_VALID_EVAL_KINDS = frozenset(
    {"deterministic", "model_evaluated", "human_reviewed", "pending_external_validation"}
)


def _require_id(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _ID_PATTERN.match(value):
        raise PackContentError(f"{where}: 'id' must match {_ID_PATTERN.pattern!r}, got {value!r}")
    return value


def _require_str(data: dict[str, object], key: str, *, where: str, max_len: int = 2000) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PackContentError(f"{where}: {key!r} must be a non-empty string")
    if len(value) > max_len:
        raise PackContentError(f"{where}: {key!r} exceeds {max_len} characters")
    return value


def _load_toml(path: Path) -> dict[str, object]:
    try:
        data = load_document(path)
    except UnknownFileFormat as exc:
        raise PackContentError(str(exc)) from exc
    if not isinstance(data, dict):
        raise PackContentError(f"{path}: top level must be a table/object")
    return data


def _check_unique_ids(items: list[dict[str, object]], *, where: str) -> None:
    seen: set[str] = set()
    for item in items:
        item_id = item["id"]
        assert isinstance(item_id, str)
        if item_id in seen:
            raise PackContentError(f"{where}: duplicate id {item_id!r}")
        seen.add(item_id)


# --- questions.toml ---------------------------------------------------


@dataclass(frozen=True)
class ClarificationDimension:
    id: str
    question: str
    why_material: str
    classification_guidance: str


def load_questions(path: Path) -> list[ClarificationDimension]:
    data = _load_toml(path)
    raw = data.get("questions", [])
    if not isinstance(raw, list):
        raise PackContentError(f"{path}: 'questions' must be an array")
    result = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise PackContentError(f"{path}: each question entry must be a table")
        where = f"{path}#{entry.get('id')}"
        result.append(
            ClarificationDimension(
                id=_require_id(entry.get("id"), where=where),
                question=_require_str(entry, "question", where=where, max_len=500),
                why_material=_require_str(entry, "why_material", where=where),
                classification_guidance=_require_str(
                    entry, "classification_guidance", where=where, max_len=500
                ),
            )
        )
    _check_unique_ids([{"id": d.id} for d in result], where=str(path))
    return result


# --- evidence-policy.toml ----------------------------------------------


@dataclass(frozen=True)
class EvidencePolicy:
    id: str
    description: str
    applies_to_claim_categories: tuple[str, ...]
    guidance: str


def load_evidence_policies(path: Path) -> list[EvidencePolicy]:
    data = _load_toml(path)
    raw = data.get("policies", [])
    if not isinstance(raw, list):
        raise PackContentError(f"{path}: 'policies' must be an array")
    result = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise PackContentError(f"{path}: each policy entry must be a table")
        where = f"{path}#{entry.get('id')}"
        categories = entry.get("applies_to_claim_categories", [])
        if not isinstance(categories, list) or not all(isinstance(c, str) for c in categories):
            raise PackContentError(f"{where}: 'applies_to_claim_categories' must be an array of strings")
        result.append(
            EvidencePolicy(
                id=_require_id(entry.get("id"), where=where),
                description=_require_str(entry, "description", where=where),
                applies_to_claim_categories=tuple(categories),
                guidance=_require_str(entry, "guidance", where=where),
            )
        )
    _check_unique_ids([{"id": p.id} for p in result], where=str(path))
    return result


# --- acceptance-templates.toml ------------------------------------------

_VALID_PRIORITIES = frozenset({"must", "should", "could"})
_VALID_VERIFICATION_METHODS = frozenset(
    {
        "automated_test", "manual_inspection", "user_confirmation",
        "external_reference_check", "reproducible_command", "static_analysis", "other",
    }
)


@dataclass(frozen=True)
class AcceptanceTemplate:
    id: str
    description_template: str
    default_priority: str
    default_verification_method: str
    default_evidence_required: str


def load_acceptance_templates(path: Path) -> list[AcceptanceTemplate]:
    data = _load_toml(path)
    raw = data.get("templates", [])
    if not isinstance(raw, list):
        raise PackContentError(f"{path}: 'templates' must be an array")
    result = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise PackContentError(f"{path}: each template entry must be a table")
        where = f"{path}#{entry.get('id')}"
        priority = entry.get("default_priority")
        if priority not in _VALID_PRIORITIES:
            raise PackContentError(f"{where}: 'default_priority' must be one of {sorted(_VALID_PRIORITIES)}")
        method = entry.get("default_verification_method")
        if method not in _VALID_VERIFICATION_METHODS:
            raise PackContentError(
                f"{where}: 'default_verification_method' must be one of {sorted(_VALID_VERIFICATION_METHODS)}"
            )
        result.append(
            AcceptanceTemplate(
                id=_require_id(entry.get("id"), where=where),
                description_template=_require_str(entry, "description_template", where=where),
                default_priority=priority,
                default_verification_method=method,
                default_evidence_required=_require_str(entry, "default_evidence_required", where=where),
            )
        )
    _check_unique_ids([{"id": t.id} for t in result], where=str(path))
    return result


# --- completion-gates.toml ----------------------------------------------


@dataclass(frozen=True)
class CompletionGate:
    id: str
    description: str
    condition: object
    on_violation: str
    rationale: str


def load_completion_gates(path: Path) -> list[CompletionGate]:
    data = _load_toml(path)
    raw = data.get("gates", [])
    if not isinstance(raw, list):
        raise PackContentError(f"{path}: 'gates' must be an array")
    result = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise PackContentError(f"{path}: each gate entry must be a table")
        where = f"{path}#{entry.get('id')}"
        on_violation = entry.get("on_violation")
        if on_violation not in _VALID_GATE_ACTIONS:
            raise PackContentError(f"{where}: 'on_violation' must be one of {sorted(_VALID_GATE_ACTIONS)}")
        condition = entry.get("condition")
        if not isinstance(condition, (dict, bool)):
            raise PackContentError(
                f"{where}: 'condition' must be a condition object (see the rule condition DSL)"
            )
        result.append(
            CompletionGate(
                id=_require_id(entry.get("id"), where=where),
                description=_require_str(entry, "description", where=where),
                condition=condition,
                on_violation=on_violation,
                rationale=_require_str(entry, "rationale", where=where),
            )
        )
    _check_unique_ids([{"id": g.id} for g in result], where=str(path))
    return result


# --- tests/scenarios.toml ------------------------------------------------


@dataclass(frozen=True)
class PackScenario:
    id: str
    description: str
    evaluation_kind: str
    given_evidence: dict[str, object]
    given_contract_fragment: dict[str, object]
    expect_gates_triggered: tuple[str, ...]
    expect_gates_not_triggered: tuple[str, ...]
    expect_rules_apply: tuple[str, ...]
    expect_rules_not_apply: tuple[str, ...]


def load_scenarios(path: Path) -> list[PackScenario]:
    data = _load_toml(path)
    raw = data.get("scenarios", [])
    if not isinstance(raw, list):
        raise PackContentError(f"{path}: 'scenarios' must be an array")
    result = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise PackContentError(f"{path}: each scenario entry must be a table")
        where = f"{path}#{entry.get('id')}"
        kind = entry.get("evaluation_kind", "deterministic")
        if kind not in _VALID_EVAL_KINDS:
            raise PackContentError(f"{where}: 'evaluation_kind' must be one of {sorted(_VALID_EVAL_KINDS)}")
        given_evidence = entry.get("given_evidence", {})
        given_contract = entry.get("given_contract_fragment", {})
        if not isinstance(given_evidence, dict) or not isinstance(given_contract, dict):
            raise PackContentError(f"{where}: 'given_evidence'/'given_contract_fragment' must be tables")
        expect_triggered = entry.get("expect_gates_triggered", [])
        expect_not_triggered = entry.get("expect_gates_not_triggered", [])
        expect_rules_apply = entry.get("expect_rules_apply", [])
        expect_rules_not_apply = entry.get("expect_rules_not_apply", [])
        for name, value in (
            ("expect_gates_triggered", expect_triggered),
            ("expect_gates_not_triggered", expect_not_triggered),
            ("expect_rules_apply", expect_rules_apply),
            ("expect_rules_not_apply", expect_rules_not_apply),
        ):
            if not isinstance(value, list):
                raise PackContentError(f"{where}: {name!r} must be an array")
        result.append(
            PackScenario(
                id=_require_id(entry.get("id"), where=where),
                description=_require_str(entry, "description", where=where),
                evaluation_kind=kind,
                given_evidence=given_evidence,
                given_contract_fragment=given_contract,
                expect_gates_triggered=tuple(expect_triggered),
                expect_gates_not_triggered=tuple(expect_not_triggered),
                expect_rules_apply=tuple(expect_rules_apply),
                expect_rules_not_apply=tuple(expect_rules_not_apply),
            )
        )
    _check_unique_ids([{"id": s.id} for s in result], where=str(path))
    return result
