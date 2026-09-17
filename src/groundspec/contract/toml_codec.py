"""Deterministic, dependency-free TOML codec for Task Contracts.

Reading uses the standard library's ``tomllib``. Writing is hand-rolled
because the standard library has no TOML writer and we need byte-for-byte
determinism (stable key order, stable float/string formatting) rather than
whatever a general-purpose third-party writer happens to choose.

TOML has no null. A dict value of ``None`` is therefore omitted from the
TOML output entirely; :mod:`groundspec.contract.normalize` restores
it as an explicit ``null`` when re-loading, via the schema's declared
default. This is the one deliberate, documented lossy point in the
round-trip (see docs/schema-reference.md).
"""

from __future__ import annotations

import re
import tomllib
from typing import Any

_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def loads_toml(text: str) -> dict[str, Any]:
    return tomllib.loads(text)


def dumps_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    _emit_table(lines, [], data)
    return "\n".join(lines).rstrip("\n") + "\n" if lines else ""


def _toml_key(name: str) -> str:
    if _BARE_KEY_RE.match(name):
        return name
    return _toml_string(name)


def _toml_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):  # noqa: PLR0133
            raise ValueError("NaN/Infinity cannot be represented in TOML")
        return repr(value)
    if isinstance(value, str):
        return _toml_string(value)
    raise TypeError(f"unsupported scalar type for TOML: {type(value)!r}")


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (bool, int, float, str))


def _is_list_of_dicts(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0 and all(isinstance(v, dict) for v in value)


def _inline_array(value: list[Any]) -> str:
    parts = []
    for item in value:
        if item is None:
            raise ValueError("TOML arrays cannot contain null; omit or restructure the field")
        if _is_scalar(item):
            parts.append(_toml_scalar(item))
        elif isinstance(item, list):
            parts.append(_inline_array(item))
        else:
            raise TypeError("mixed/object arrays must use array-of-tables, not inline arrays")
    return "[" + ", ".join(parts) + "]"


def _emit_table(lines: list[str], path: list[str], table: dict[str, Any]) -> None:
    leaf_keys = []
    subtable_keys = []
    array_of_table_keys = []

    for key in sorted(table.keys()):
        value = table[key]
        if value is None:
            continue
        if isinstance(value, dict):
            subtable_keys.append(key)
        elif _is_list_of_dicts(value):
            array_of_table_keys.append(key)
        else:
            leaf_keys.append(key)

    if path and (leaf_keys or not (subtable_keys or array_of_table_keys)):
        lines.append(f"[{'.'.join(_toml_key(p) for p in path)}]")

    for key in leaf_keys:
        value = table[key]
        rendered = _inline_array(value) if isinstance(value, list) else _toml_scalar(value)
        lines.append(f"{_toml_key(key)} = {rendered}")

    for key in subtable_keys:
        _emit_table(lines, [*path, key], table[key])

    for key in array_of_table_keys:
        for item in table[key]:
            header_path = [*path, key]
            lines.append(f"[[{'.'.join(_toml_key(p) for p in header_path)}]]")
            _emit_array_table_body(lines, header_path, item)


def _emit_array_table_body(lines: list[str], path: list[str], table: dict[str, Any]) -> None:
    leaf_keys = []
    subtable_keys = []
    array_of_table_keys = []
    for key in sorted(table.keys()):
        value = table[key]
        if value is None:
            continue
        if isinstance(value, dict):
            subtable_keys.append(key)
        elif _is_list_of_dicts(value):
            array_of_table_keys.append(key)
        else:
            leaf_keys.append(key)

    for key in leaf_keys:
        value = table[key]
        rendered = _inline_array(value) if isinstance(value, list) else _toml_scalar(value)
        lines.append(f"{_toml_key(key)} = {rendered}")

    for key in subtable_keys:
        _emit_table(lines, [*path, key], table[key])

    for key in array_of_table_keys:
        for item in table[key]:
            header_path = [*path, key]
            lines.append(f"[[{'.'.join(_toml_key(p) for p in header_path)}]]")
            _emit_array_table_body(lines, header_path, item)
