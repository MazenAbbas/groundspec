"""``groundspec pack init``: the smallest possible valid Domain Pack.

No executable code, no unnecessary files: a manifest, one example rule,
and one short guidance note -- enough to pass `pack validate` immediately
and to show an author every required manifest field by example.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

from groundspec.__about__ import PACK_PLATFORM_VERSION
from groundspec.packs.sdk.errors import PackManifestError

_PACK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,63}$")


class DestinationExists(PackManifestError):
    pass


def _pack_toml(pack_id: str) -> str:
    return f"""domain_pack_schema_version = "0.1.0"
pack_id = "{pack_id}"
version = "0.1.0"
display_name = "{pack_id.replace('-', ' ').title()}"
description = "Describe in one or two sentences what this pack is for."

[compatibility]
min_platform_version = "{PACK_PLATFORM_VERSION}"

[provides]
rules = "rules.toml"
references = ["references/domain-guidance.md"]
"""


def _rules_toml(pack_id: str) -> str:
    return f"""rule_pack_schema_version = "0.1.0"
pack_id = "{pack_id}"
version = "0.1.0"
layer = "domain"
title = "Domain pack: {pack_id}"
description = "Replace this with a real description."

[[rules]]
id = "example-rule"
version = "0.1.0"
title = "Replace this with a real rule"
purpose = "Explain what this rule prevents."
scope = "When does this rule apply?"
applies_when = true
severity = "advisory"
requirement = "State the actual requirement here."
verification_method = "manual_inspection"
evidence_requirement = "What would a reviewer check?"
failure_behavior = "warn_only"
source_or_rationale = "Why does this rule exist?"
"""


def _guidance_md(pack_id: str) -> str:
    title = pack_id.replace("-", " ").title()
    return f"""# Domain guidance: {title}

Replace this with real guidance for the Meta-Skill: when to select this
pack, what clarification questions matter, and what evidence a claim in
this domain actually needs.
"""


def init_pack(pack_id: str, output: Path, *, force: bool = False) -> Path:
    if not _PACK_ID_PATTERN.match(pack_id):
        raise PackManifestError(f"invalid pack id {pack_id!r}: must match {_PACK_ID_PATTERN.pattern!r}")

    pack_dir = output / pack_id
    if pack_dir.exists() and not force:
        raise DestinationExists(f"{pack_dir} already exists; pass --force to overwrite")

    files = {
        "pack.toml": _pack_toml(pack_id),
        "rules.toml": _rules_toml(pack_id),
        "references/domain-guidance.md": _guidance_md(pack_id),
    }

    with tempfile.TemporaryDirectory(dir=output if output.is_dir() else None) as tmp:
        tmp_path = Path(tmp) / pack_id
        for rel, content in files.items():
            full = tmp_path / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8", newline="\n")

        if pack_dir.exists():
            shutil.rmtree(pack_dir)
        pack_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_path, pack_dir)

    return pack_dir
