"""Loads the versioned, canonical JSON Schemas bundled with this package.

Schemas are read-only data files, never generated at runtime, so that the
schema a user inspects on disk is exactly the schema tooling validates
against.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any

SUPPORTED_CONTRACT_VERSIONS = ("0.1.0", "0.2.0", "0.3.0")
SUPPORTED_RULE_PACK_VERSIONS = ("0.1.0",)


class UnsupportedSchemaVersion(ValueError):
    """Raised when a document declares a schema version this build does not ship."""


@cache
def load_contract_schema(version: str = "0.1.0") -> dict[str, Any]:
    if version not in SUPPORTED_CONTRACT_VERSIONS:
        raise UnsupportedSchemaVersion(
            f"contract_schema_version {version!r} is not supported by this build "
            f"(supported: {', '.join(SUPPORTED_CONTRACT_VERSIONS)}). "
            "Refusing to guess: upgrade the tool or migrate the contract."
        )
    filename = f"task_contract.v{version.replace('.', '_')}.schema.json"
    return _read_schema(filename)


@cache
def load_rule_pack_schema(version: str = "0.1.0") -> dict[str, Any]:
    if version not in SUPPORTED_RULE_PACK_VERSIONS:
        raise UnsupportedSchemaVersion(
            f"rule_pack_schema_version {version!r} is not supported by this build "
            f"(supported: {', '.join(SUPPORTED_RULE_PACK_VERSIONS)})."
        )
    filename = f"rule_pack.v{version.replace('.', '_')}.schema.json"
    return _read_schema(filename)


def _read_schema(filename: str) -> dict[str, Any]:
    package = resources.files("groundspec.schema")
    with (package / filename).open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data
