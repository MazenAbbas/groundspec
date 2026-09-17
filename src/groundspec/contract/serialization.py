"""Canonical (de)serialization of Task Contracts to/from JSON and TOML.

Canonical JSON follows the same spirit as RFC 8785 (JSON Canonicalization
Scheme): object keys are sorted so two semantically identical contracts
produce byte-identical files, which makes git diffs and golden fixtures
meaningful. Array order is never touched -- arrays in this schema are
always semantically ordered (e.g. acceptance criteria, stop conditions).

No timestamps are ever written by this module. If a caller wants one, it
must be a field the caller adds explicitly before serializing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from groundspec.contract.toml_codec import dumps_toml, loads_toml


def _sort_recursive(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_recursive(value[key]) for key in sorted(value.keys())}
    if isinstance(value, list):
        return [_sort_recursive(item) for item in value]
    return value


def canonical_json_dumps(data: dict[str, Any]) -> str:
    sorted_data = _sort_recursive(data)
    return json.dumps(sorted_data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def canonical_json_loads(text: str) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(text)
    return result


def canonical_toml_dumps(data: dict[str, Any]) -> str:
    sorted_data = _sort_recursive(data)
    return dumps_toml(sorted_data)


def canonical_toml_loads(text: str) -> dict[str, Any]:
    return loads_toml(text)


class UnknownFileFormat(ValueError):
    pass


def load_document(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        return canonical_json_loads(text)
    if suffix == ".toml":
        return canonical_toml_loads(text)
    raise UnknownFileFormat(f"unrecognized extension {suffix!r}; expected .json or .toml")


def dump_document(data: dict[str, Any], path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix == ".json":
        path.write_text(canonical_json_dumps(data), encoding="utf-8", newline="\n")
    elif suffix == ".toml":
        path.write_text(canonical_toml_dumps(data), encoding="utf-8", newline="\n")
    else:
        raise UnknownFileFormat(f"unrecognized extension {suffix!r}; expected .json or .toml")
