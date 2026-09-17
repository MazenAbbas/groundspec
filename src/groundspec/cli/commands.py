"""Implementations of each `groundspec` subcommand.

Every command here is deterministic and offline: no network access, no API
key, no model call. Natural-language understanding (turning a vague brief
into a first-draft contract) is explicitly out of scope for this CLI -- see
docs/architecture.md's deterministic/model-dependent boundary. That is what
the Claude Code / Codex Skill is for.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from groundspec.__about__ import CONTRACT_SCHEMA_VERSION, __version__
from groundspec.budget.model import forbid_silent_skip_on_expiry
from groundspec.contract.factory import new_contract
from groundspec.contract.normalize import fill_defaults
from groundspec.contract.schema_loader import load_contract_schema
from groundspec.contract.serialization import UnknownFileFormat, dump_document, load_document
from groundspec.contract.validator import SchemaValidationError, validate_contract_dict
from groundspec.metaskill.claude_export import render_claude_meta_skill
from groundspec.metaskill.codex_export import render_codex_meta_skill
from groundspec.metaskill.completion import (
    derive_completion_state,
    evaluate_acceptance_criteria,
    residual_risk_blocks_completion,
)
from groundspec.metaskill.export import (
    DestinationExists,
    ExportError,
    export_file_set,
)
from groundspec.metaskill.validate import validate_skill_files
from groundspec.packs.registry import (
    CORE_PACK_ID,
    DOMAIN_PACK_IDS,
    RISK_OVERLAY_PACK_IDS,
    BuiltinPackNotFound,
    load_builtin,
    select_packs_for_contract,
)
from groundspec.rules.errors import RulePackError
from groundspec.rules.evaluator import applicable, evaluate_rule_set
from groundspec.rules.pack_loader import load_pack_file, resolve_pack
from groundspec.rules.precedence import build_rule_set
from groundspec.scoring.rubric import score as score_rubric

OK = "[OK]"
FAIL = "[FAIL]"


def _load_contract_or_die(path: Path) -> dict[str, object]:
    try:
        data = load_document(path)
    except UnknownFileFormat as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except FileNotFoundError:
        print(f"{FAIL} no such file: {path}", file=sys.stderr)
        raise SystemExit(2) from None
    try:
        validated = dict(data)
        issues = validate_contract_dict(validated)
        if issues:
            raise SchemaValidationError(issues)
    except SchemaValidationError as exc:
        print(f"{FAIL} {path} is not a valid Task Contract:", file=sys.stderr)
        for issue in exc.issues:
            print(f"  - {issue}", file=sys.stderr)
        raise SystemExit(1) from exc
    schema = load_contract_schema(str(validated["contract_schema_version"]))
    return dict(fill_defaults(validated, schema))


def cmd_init(args: object) -> int:
    target = Path(getattr(args, "dir", ".")).resolve()
    groundspec_dir = target / ".groundspec"
    packs_dir = groundspec_dir / "packs"
    if groundspec_dir.exists():
        print(f"{OK} {groundspec_dir} already exists; nothing to do.")
        return 0
    packs_dir.mkdir(parents=True)
    config = (
        "# groundspec project configuration\n"
        "# Add local rule-pack search directories here (relative to this file's directory).\n"
        'project_pack_search_dirs = ["packs"]\n'
    )
    (groundspec_dir / "config.toml").write_text(config, encoding="utf-8", newline="\n")
    print(f"{OK} initialized {groundspec_dir}")
    print(f"  - {packs_dir} (put project rule packs here)")
    print(f"  - {groundspec_dir / 'config.toml'}")
    return 0


def cmd_create(args: object) -> int:
    task_id = getattr(args, "task_id", None) or input("Short task id (e.g. write-launch-post): ").strip()
    brief_text = getattr(args, "brief", None) or input("What do you want done, in your own words: ").strip()
    goal = getattr(args, "goal", None) or input("In one sentence, what does 'done' produce: ").strip()
    problem = getattr(args, "problem", None) or (
        f"No {task_id.replace('-', ' ')} currently exists to meet this need."
    )
    users_arg = getattr(args, "user", None) or []
    if not users_arg:
        raw = input("Who is this for (comma-separated): ").strip()
        users_arg = [u.strip() for u in raw.split(",") if u.strip()] or ["the requesting user"]
    deliverables_arg = getattr(args, "deliverable", None) or []
    if not deliverables_arg:
        deliverables_arg = [f"{task_id}_output:The finished result of this task"]

    deliverables = []
    for item in deliverables_arg:
        name, _, desc = item.partition(":")
        deliverables.append({"name": name.strip() or "output", "description": desc.strip() or name.strip()})

    risk_overlays = getattr(args, "risk_overlay", None) or ["informational"]
    for overlay in risk_overlays:
        if overlay not in RISK_OVERLAY_PACK_IDS:
            valid = ", ".join(RISK_OVERLAY_PACK_IDS)
            print(f"{FAIL} unknown risk overlay {overlay!r}. Valid: {valid}", file=sys.stderr)
            return 2

    contract = new_contract(
        task_id=task_id,
        raw_user_brief=brief_text,
        normalized_problem_statement=problem,
        goal=goal,
        target_users=users_arg,
        expected_deliverables=deliverables,
        risk_overlays=risk_overlays,
        risk_level=getattr(args, "risk_level", None) or "low",
    )

    routing = contract["routing"]
    assert isinstance(routing, dict)
    domain_packs = routing["domain_packs"]
    assert isinstance(domain_packs, list)
    for domain in getattr(args, "domain", None) or []:
        if domain not in DOMAIN_PACK_IDS:
            valid = ", ".join(DOMAIN_PACK_IDS)
            print(f"{FAIL} unknown domain {domain!r}. Valid: {valid}", file=sys.stderr)
            return 2
        domain_packs.append({"pack_id": domain, "version": "0.1.0"})

    out_path = Path(getattr(args, "out", None) or f"{task_id}.toml")
    dump_document(contract, out_path)
    print(f"{OK} wrote {out_path}")
    print("  Open it, fill in acceptance.criteria and scope.constraints, then run:")
    print(f"    groundspec validate {out_path}")
    return 0


def cmd_validate(args: object) -> int:
    path = Path(args.contract)  # type: ignore[attr-defined]
    try:
        data = load_document(path)
    except (UnknownFileFormat, FileNotFoundError) as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        return 2
    issues = validate_contract_dict(data)
    if issues:
        print(f"{FAIL} {path}: {len(issues)} issue(s)")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(f"{OK} {path} is a valid Task Contract (schema {data.get('contract_schema_version')})")
    return 0


def _write_files(base: Path, files: dict[str, str]) -> None:
    for rel_path, content in files.items():
        full = base / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8", newline="\n")


def cmd_compile(args: object) -> int:
    contract = _load_contract_or_die(Path(args.contract))  # type: ignore[attr-defined]
    target = args.target  # type: ignore[attr-defined]
    out_dir = Path(getattr(args, "out", None) or ".")
    project_packs = [Path(p) for p in (getattr(args, "project_pack", None) or [])]

    try:
        packs = select_packs_for_contract(contract, project_pack_paths=project_packs)
    except (BuiltinPackNotFound, RulePackError) as exc:
        print(f"{FAIL} could not resolve rule packs: {exc}", file=sys.stderr)
        return 1

    rule_set = build_rule_set(packs)
    if rule_set.conflicts:
        print("Precedence conflicts resolved deterministically:")
        for conflict in rule_set.conflicts:
            print(f"  - {conflict.explanation}")

    applied = evaluate_rule_set(rule_set, contract)
    task_id = contract["task_id"]

    if target == "generic":
        from groundspec.adapters.generic import render_generic_prompt

        text = render_generic_prompt(contract, applied)
        out_path = out_dir / f"{task_id}.groundspec-prompt.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8", newline="\n")
        print(f"{OK} wrote {out_path}")
    elif target == "claude-code":
        from groundspec.adapters.claude_skill import render_claude_skill

        files = render_claude_skill(contract, applied)
        skill_dir = out_dir / ".claude" / "skills" / str(task_id)
        _write_files(skill_dir, files)
        print(f"{OK} wrote Claude Code Skill to {skill_dir}")
    elif target == "codex":
        from groundspec.adapters.codex_skill import render_codex_skill

        files = render_codex_skill(contract, applied)
        skill_dir = out_dir / ".agents" / "skills" / str(task_id)
        _write_files(skill_dir, files)
        print(f"{OK} wrote Codex Skill to {skill_dir}")
    else:
        print(f"{FAIL} unknown target {target!r}", file=sys.stderr)
        return 2
    return 0


def cmd_audit(args: object) -> int:
    contract = _load_contract_or_die(Path(args.contract))  # type: ignore[attr-defined]
    ok = True

    budget = contract["budget"]
    assert isinstance(budget, dict)
    if not (0 <= budget["reserved_verification_fraction"] <= 0.9):
        print(f"{FAIL} budget.reserved_verification_fraction out of [0, 0.9]")
        ok = False

    status = contract["status"]
    assert isinstance(status, dict)
    for violation in forbid_silent_skip_on_expiry(status):
        print(f"{FAIL} {violation}")
        ok = False

    project_packs = [Path(p) for p in (getattr(args, "project_pack", None) or [])]
    try:
        packs = select_packs_for_contract(contract, project_pack_paths=project_packs)
    except (BuiltinPackNotFound, RulePackError) as exc:
        print(f"{FAIL} could not resolve rule packs: {exc}")
        return 1

    rule_set = build_rule_set(packs)
    for conflict in rule_set.conflicts:
        print(f"[CONFLICT] {conflict.explanation}")

    applied = evaluate_rule_set(rule_set, contract)
    hard = applicable(applied, severity="hard_constraint")
    print(f"\n{len(hard)} applicable hard constraint(s):")
    for a in hard:
        auto = a.qualified.rule["verification_method"] in ("automated_test",)
        tag = "mechanically checkable" if auto else "needs human/model judgment with evidence"
        print(f"  - [{a.qualified.fq_id}] ({tag}) {a.qualified.rule['requirement']}")

    print(f"\n{OK if ok else FAIL} static audit {'passed' if ok else 'found issues'}")
    return 0 if ok else 1


def cmd_evaluate(args: object) -> int:
    contract = _load_contract_or_die(Path(args.contract))  # type: ignore[attr-defined]
    result_dir = Path(args.result_dir)  # type: ignore[attr-defined]
    evidence_path = result_dir / "evidence.json"
    if not evidence_path.is_file():
        print(
            f"{FAIL} expected {evidence_path} (see docs/evaluation-methodology.md for its format)",
            file=sys.stderr,
        )
        return 2
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    status = contract["status"]
    assert isinstance(status, dict)
    expiry_violations = forbid_silent_skip_on_expiry(status)
    for violation in expiry_violations:
        print(f"{FAIL} {violation}")

    quality = contract["quality"]
    assert isinstance(quality, dict)
    result = score_rubric(
        soft_objectives=list(quality["soft_objectives"]),
        hard_constraint_results=evidence.get("hard_constraint_results", {}),
        dimension_scores=evidence.get("dimension_scores", {}),
    )

    print(f"Verdict: {result.verdict}")
    if not result.hard_constraints_passed:
        print(f"{FAIL} failed hard constraints: {', '.join(result.failed_hard_constraint_ids)}")
    for dim in result.dimension_scores:
        label = "insufficient evidence" if dim.insufficient_evidence else f"{dim.score:.2f}"
        subj = "subjective" if dim.subjective else "objective"
        print(f"  - {dim.dimension} ({subj}, weight {dim.weight}): {label}")
    if result.weighted_total is not None:
        print(f"Weighted total: {result.weighted_total:.3f}")

    passed = result.hard_constraints_passed and not expiry_violations

    # Additive, backward-compatible: only computed when the caller actually
    # supplies acceptance_criteria_results (new in 0.2.0rc1). Older
    # evidence.json files (no such key) keep the exact 0.1.0rc1 behavior
    # above -- this block never changes their exit code.
    if "acceptance_criteria_results" in evidence:
        acceptance = contract["acceptance"]
        assert isinstance(acceptance, dict)
        scope = contract["scope"]
        assert isinstance(scope, dict)
        criteria = acceptance["criteria"]
        assert isinstance(criteria, list)
        acceptance_eval = evaluate_acceptance_criteria(criteria, evidence["acceptance_criteria_results"])
        open_questions = scope["open_questions"]
        assert isinstance(open_questions, list)
        has_blocking = any(
            q["classification"] == "blocking" and q["resolution_status"] == "open" for q in open_questions
        )
        residual_risks = status["residual_risks"]
        assert isinstance(residual_risks, list)
        authorization_violations = evidence.get("authorization_violations", [])
        state = derive_completion_state(
            hard_constraints_passed=result.hard_constraints_passed,
            has_unresolved_blocking_questions=has_blocking,
            budget_expired=bool(status.get("budget_expired", False)),
            acceptance_criteria_met=acceptance_eval.must_criteria_met,
            authorization_boundary_violated=bool(authorization_violations),
            unresolved_critical_risk_to_validity=residual_risk_blocks_completion(residual_risks),
        )
        print(f"Completion state: {state}")
        if authorization_violations:
            print(f"{FAIL} authorization boundary violated: {'; '.join(authorization_violations)}")
        if acceptance_eval.missing_evidence_ids:
            print(f"  missing evidence for: {', '.join(acceptance_eval.missing_evidence_ids)}")
        if acceptance_eval.inadequate_evidence_ids:
            print(f"  inadequate evidence (weak label for a strong-evidence criterion): "
                  f"{', '.join(acceptance_eval.inadequate_evidence_ids)}")
        if acceptance_eval.unmet_must_ids:
            print(f"  unmet 'must' criteria: {', '.join(acceptance_eval.unmet_must_ids)}")
        return 0 if state in ("PASS", "PASS_WITH_CAVEATS") else 1

    return 0 if passed else 1


def cmd_pack_validate(args: object) -> int:
    path = Path(args.path)  # type: ignore[attr-defined]
    try:
        data = load_pack_file(path)
        resolve_pack(path, search_dirs=[path.parent])
    except (RulePackError, SchemaValidationError, UnknownFileFormat, FileNotFoundError) as exc:
        print(f"{FAIL} {path}: {exc}", file=sys.stderr)
        return 1
    rules = data["rules"]
    assert isinstance(rules, list)
    print(f"{OK} {path}: pack {data['pack_id']!r} v{data['version']} ({len(rules)} rule(s)) is valid")
    return 0


def cmd_example(args: object) -> int:
    from groundspec import examples as examples_module

    out_dir = Path(getattr(args, "out", None) or ".")
    out_dir.mkdir(parents=True, exist_ok=True)
    written = examples_module.write_bundled_examples(out_dir)
    for path in written:
        print(f"{OK} wrote {path}")
    return 0


def cmd_doctor(args: object) -> int:
    ok = True
    print(f"groundspec {__version__} (contract schema {CONTRACT_SCHEMA_VERSION})")
    print(f"Python {sys.version.split()[0]} on {sys.platform}")

    try:
        load_contract_schema(CONTRACT_SCHEMA_VERSION)
        print(f"{OK} contract schema loads")
    except Exception as exc:  # noqa: BLE001
        print(f"{FAIL} contract schema failed to load: {exc}")
        ok = False

    all_ids = [CORE_PACK_ID, *RISK_OVERLAY_PACK_IDS.values(), *DOMAIN_PACK_IDS.values()]
    for pack_id in all_ids:
        try:
            load_builtin(pack_id)
        except Exception as exc:  # noqa: BLE001
            print(f"{FAIL} built-in pack {pack_id!r} failed to load: {exc}")
            ok = False
    print(f"{OK} {len(all_ids)} built-in rule packs load" if ok else f"{FAIL} some built-in packs failed")

    for name, renderer in (("claude-code", render_claude_meta_skill), ("codex", render_codex_meta_skill)):
        try:
            issues = validate_skill_files(renderer())
        except Exception as exc:  # noqa: BLE001
            print(f"{FAIL} meta-skill export for {name!r} failed to render: {exc}")
            ok = False
            continue
        if issues:
            print(f"{FAIL} meta-skill export for {name!r} failed structural validation:")
            for issue in issues:
                print(f"  - {issue}")
            ok = False
        else:
            print(f"{OK} meta-skill export for {name!r} is structurally valid")

    print(f"\n{OK if ok else FAIL} doctor {'found no problems' if ok else 'found problems'}")
    return 0 if ok else 1


_SKILL_RENDERERS = {"claude-code": render_claude_meta_skill, "codex": render_codex_meta_skill}
_SKILL_SCOPE_DIR = {"claude-code": ".claude", "codex": ".agents"}
_SKILL_USER_HOME_DIR = {"claude-code": ".claude", "codex": ".agents"}


def _skill_destination(target: str, output: str | None, scope: str) -> Path:
    if scope == "user":
        return Path.home() / _SKILL_USER_HOME_DIR[target] / "skills" / "groundspec"
    base = Path(output or ".")
    return base / _SKILL_SCOPE_DIR[target] / "skills" / "groundspec"


def cmd_skill_export(args: object) -> int:
    target = args.target  # type: ignore[attr-defined]
    scope = getattr(args, "scope", "project") or "project"
    force = bool(getattr(args, "force", False))

    renderer = _SKILL_RENDERERS.get(target)
    if renderer is None:
        print(f"{FAIL} unknown target {target!r}", file=sys.stderr)
        return 2

    files = renderer()
    issues = validate_skill_files(files)
    if issues:
        print(f"{FAIL} generated meta-skill failed structural validation (this is a groundspec bug):")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    destination = _skill_destination(target, getattr(args, "output", None), scope)
    try:
        result = export_file_set(files, destination, force=force)
    except DestinationExists as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        print("Pass --force to overwrite the existing export.", file=sys.stderr)
        return 1
    except ExportError as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        return 1

    print(f"{OK} exported {len(result.files)} file(s) to {result.destination}")
    for entry in sorted(result.files, key=lambda f: f.relative_path):
        print(f"  - {entry.relative_path} ({entry.size} bytes, sha256 {entry.sha256[:12]}...)")
    if target == "claude-code":
        print("\nClaude Code will discover this under its skills directory; invoke with /groundspec.")
    else:
        print("\nCodex will discover this under its skills directory; invoke with $groundspec.")
    return 0


def cmd_skill_validate(args: object) -> int:
    path = Path(args.path)  # type: ignore[attr-defined]
    if not path.is_dir():
        print(f"{FAIL} {path} is not a directory", file=sys.stderr)
        return 2

    skill_md_path = path / "SKILL.md"
    if not skill_md_path.is_file():
        print(f"{FAIL} {path}: no SKILL.md found", file=sys.stderr)
        return 1

    files = {"SKILL.md": skill_md_path.read_text(encoding="utf-8")}
    refs_dir = path / "references"
    if refs_dir.is_dir():
        for md_path in refs_dir.rglob("*.md"):
            rel = "references/" + md_path.relative_to(refs_dir).as_posix()
            files[rel] = md_path.read_text(encoding="utf-8")

    issues = validate_skill_files(files)
    if issues:
        print(f"{FAIL} {path}: {len(issues)} structural issue(s)")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(f"{OK} {path}: Skill structure is valid ({len(files)} file(s))")
    return 0
