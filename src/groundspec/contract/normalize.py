"""Explicit, schema-driven default-filling.

This is kept separate from validation on purpose: validation never mutates
data or invents values, and normalization never decides whether data is
valid. Only ``default`` values declared in the schema itself are applied
here -- nothing is inferred from context.
"""

from __future__ import annotations

import copy
from typing import Any


def _resolve(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        ref = schema["$ref"]
        assert ref.startswith("#/$defs/"), f"only local $defs refs are supported, got {ref!r}"
        return root["$defs"][ref.removeprefix("#/$defs/")]  # type: ignore[no-any-return]
    return schema


def fill_defaults(data: Any, schema: dict[str, Any], root: dict[str, Any] | None = None) -> Any:
    """Return a deep copy of ``data`` with declared schema defaults filled in."""
    if root is None:
        root = schema
    schema = _resolve(schema, root)

    if "oneOf" in schema:
        # Only used for nullable fields in this schema family: null | $ref.
        if data is None:
            return None
        for branch in schema["oneOf"]:
            branch = _resolve(branch, root)
            if branch.get("type") == "null":
                continue
            return fill_defaults(data, branch, root)
        return data

    schema_type = schema.get("type")

    if schema_type == "object" or "properties" in schema:
        result: dict[str, Any] = copy.deepcopy(data) if isinstance(data, dict) else {}
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            if prop_name not in result:
                if "default" in prop_schema:
                    result[prop_name] = copy.deepcopy(prop_schema["default"])
                else:
                    continue
            result[prop_name] = fill_defaults(result[prop_name], prop_schema, root)
        return result

    if schema_type == "array" and isinstance(data, list):
        item_schema = schema.get("items")
        if item_schema is None:
            return data
        return [fill_defaults(item, item_schema, root) for item in data]

    return data
