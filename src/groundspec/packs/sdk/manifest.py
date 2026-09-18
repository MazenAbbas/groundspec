"""Loads and validates a Domain Pack: ``pack.toml`` plus everything it
references (``provides.*``). See docs/architecture.md's Domain Pack SDK
section for the full picture and docs/pack-authoring-guide.md for the
authoring-facing walkthrough.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from groundspec.contract.normalize import fill_defaults
from groundspec.contract.schema_loader import load_domain_pack_schema
from groundspec.contract.serialization import UnknownFileFormat, load_document
from groundspec.contract.validator import SchemaValidationError, validate_domain_pack_dict
from groundspec.packs.sdk import content as content_mod
from groundspec.packs.sdk import safety
from groundspec.packs.sdk.errors import PackManifestError
from groundspec.packs.sdk.hashing import hash_pack_directory
from groundspec.rules.pack_loader import LoadedPack, resolve_pack

MANIFEST_FILENAME = "pack.toml"


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


@dataclass(frozen=True)
class PackDependency:
    pack_id: str
    min_version: str
    max_version: str | None


@dataclass(frozen=True)
class PackConflict:
    pack_id: str
    reason: str
    min_version: str | None
    max_version: str | None


@dataclass(frozen=True)
class PackManifest:
    pack_id: str
    version: str
    display_name: str
    description: str
    capabilities: tuple[str, ...]
    supported_intents: tuple[str, ...]
    routing_triggers: tuple[str, ...]
    routing_exclusions: tuple[str, ...]
    min_platform_version: str
    max_platform_version: str | None
    dependencies: tuple[PackDependency, ...]
    suggested: tuple[str, ...]
    conflicts: tuple[PackConflict, ...]
    priority: int
    risk_classification: str
    provides: dict[str, object]

    @staticmethod
    def from_dict(data: dict[str, object]) -> PackManifest:
        routing = data.get("routing", {})
        assert isinstance(routing, dict)
        compat = data["compatibility"]
        assert isinstance(compat, dict)

        raw_deps = data.get("dependencies", [])
        assert isinstance(raw_deps, list)
        deps = []
        for raw in raw_deps:
            assert isinstance(raw, dict)
            deps.append(
                PackDependency(
                    pack_id=str(raw["pack_id"]),
                    min_version=str(raw["min_version"]),
                    max_version=_optional_str(raw.get("max_version")),
                )
            )

        raw_conflicts = data.get("conflicts", [])
        assert isinstance(raw_conflicts, list)
        conflicts = []
        for raw in raw_conflicts:
            assert isinstance(raw, dict)
            conflicts.append(
                PackConflict(
                    pack_id=str(raw["pack_id"]),
                    reason=str(raw["reason"]),
                    min_version=_optional_str(raw.get("min_version")),
                    max_version=_optional_str(raw.get("max_version")),
                )
            )

        provides = data.get("provides", {})
        assert isinstance(provides, dict)

        capabilities = data.get("capabilities", [])
        assert isinstance(capabilities, list)
        supported_intents = data.get("supported_intents", [])
        assert isinstance(supported_intents, list)
        routing_triggers = routing.get("triggers", [])
        assert isinstance(routing_triggers, list)
        routing_exclusions = routing.get("exclusions", [])
        assert isinstance(routing_exclusions, list)
        suggested = data.get("suggested", [])
        assert isinstance(suggested, list)
        priority = data.get("priority", 0)
        assert isinstance(priority, int)

        return PackManifest(
            pack_id=str(data["pack_id"]),
            version=str(data["version"]),
            display_name=str(data["display_name"]),
            description=str(data["description"]),
            capabilities=tuple(str(c) for c in capabilities),
            supported_intents=tuple(str(i) for i in supported_intents),
            routing_triggers=tuple(str(t) for t in routing_triggers),
            routing_exclusions=tuple(str(e) for e in routing_exclusions),
            min_platform_version=str(compat["min_platform_version"]),
            max_platform_version=_optional_str(compat.get("max_platform_version")),
            dependencies=tuple(deps),
            suggested=tuple(str(s) for s in suggested),
            conflicts=tuple(conflicts),
            priority=priority,
            risk_classification=str(data.get("risk_classification", "standard")),
            provides=provides,
        )


@dataclass(frozen=True)
class DomainPack:
    manifest: PackManifest
    pack_dir: Path
    origin: str  # "official" | "project" | "user"
    content_hash: str
    rules: LoadedPack | None
    questions: tuple[content_mod.ClarificationDimension, ...] = field(default_factory=tuple)
    evidence_policies: tuple[content_mod.EvidencePolicy, ...] = field(default_factory=tuple)
    acceptance_templates: tuple[content_mod.AcceptanceTemplate, ...] = field(default_factory=tuple)
    completion_gates: tuple[content_mod.CompletionGate, ...] = field(default_factory=tuple)
    reference_paths: tuple[str, ...] = field(default_factory=tuple)
    scenarios: tuple[content_mod.PackScenario, ...] = field(default_factory=tuple)

    @property
    def pack_id(self) -> str:
        return self.manifest.pack_id

    @property
    def version(self) -> str:
        return self.manifest.version


def load_manifest_dict(manifest_path: Path) -> dict[str, object]:
    try:
        data = load_document(manifest_path)
    except UnknownFileFormat as exc:
        raise PackManifestError(str(exc)) from exc
    issues = validate_domain_pack_dict(data)
    if issues:
        raise PackManifestError(
            f"{manifest_path} failed manifest validation:\n" + "\n".join(f"  - {i}" for i in issues)
        ) from SchemaValidationError(issues)
    schema = load_domain_pack_schema(str(data["domain_pack_schema_version"]))
    filled = fill_defaults(data, schema)
    assert isinstance(filled, dict)
    return filled


def load_pack(pack_dir: Path, *, origin: str, run_safety_scan: bool = True) -> DomainPack:
    """Load, validate, and fully resolve every file a Domain Pack provides.

    ``run_safety_scan`` is skipped only by internal callers that already
    scanned the same directory moments earlier (avoids doing it twice
    during a single `pack resolve` over many packs); every public entry
    point (`pack validate`, `pack inspect`, `pack resolve`, `pack lock`,
    `pack test`) always leaves it on.
    """
    if run_safety_scan:
        safety.scan_pack_directory(pack_dir)

    manifest_path = pack_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise PackManifestError(f"{pack_dir}: no {MANIFEST_FILENAME} found")
    manifest = PackManifest.from_dict(load_manifest_dict(manifest_path))

    provides = manifest.provides
    rules: LoadedPack | None = None
    if provides.get("rules"):
        rules_path = _safe_join(pack_dir, str(provides["rules"]))
        rules = resolve_pack(rules_path, search_dirs=[pack_dir])

    questions: tuple[content_mod.ClarificationDimension, ...] = ()
    if provides.get("questions"):
        questions = tuple(content_mod.load_questions(_safe_join(pack_dir, str(provides["questions"]))))

    evidence_policies: tuple[content_mod.EvidencePolicy, ...] = ()
    if provides.get("evidence_policy"):
        evidence_policies = tuple(
            content_mod.load_evidence_policies(_safe_join(pack_dir, str(provides["evidence_policy"])))
        )

    acceptance_templates: tuple[content_mod.AcceptanceTemplate, ...] = ()
    if provides.get("acceptance_templates"):
        acceptance_templates = tuple(
            content_mod.load_acceptance_templates(_safe_join(pack_dir, str(provides["acceptance_templates"])))
        )

    completion_gates: tuple[content_mod.CompletionGate, ...] = ()
    if provides.get("completion_gates"):
        completion_gates = tuple(
            content_mod.load_completion_gates(_safe_join(pack_dir, str(provides["completion_gates"])))
        )

    raw_references = provides.get("references", [])
    assert isinstance(raw_references, list)
    reference_paths = tuple(str(r) for r in raw_references)
    for rel in reference_paths:
        resolved = _safe_join(pack_dir, rel)
        if not resolved.is_file():
            raise PackManifestError(f"{pack_dir}: provides.references entry {rel!r} does not exist")

    scenarios: tuple[content_mod.PackScenario, ...] = ()
    if provides.get("tests"):
        scenarios = tuple(content_mod.load_scenarios(_safe_join(pack_dir, str(provides["tests"]))))

    content_hash = hash_pack_directory(pack_dir)

    return DomainPack(
        manifest=manifest,
        pack_dir=pack_dir,
        origin=origin,
        content_hash=content_hash,
        rules=rules,
        questions=questions,
        evidence_policies=evidence_policies,
        acceptance_templates=acceptance_templates,
        completion_gates=completion_gates,
        reference_paths=reference_paths,
        scenarios=scenarios,
    )


def _safe_join(pack_dir: Path, rel: str) -> Path:
    candidate = (pack_dir / rel).resolve()
    root = pack_dir.resolve()
    if os.path.commonpath([str(candidate), str(root)]) != str(root):
        raise PackManifestError(f"{pack_dir}: provides path {rel!r} escapes the pack directory")
    if not candidate.exists():
        raise PackManifestError(f"{pack_dir}: referenced file {rel!r} does not exist")
    return candidate
