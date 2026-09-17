import json
from pathlib import Path

from groundspec.cli.main import main


def run(argv: list[str]) -> int:
    return main(argv)


def _make_contract(tmp_path: Path) -> Path:
    contract_path = tmp_path / "demo.toml"
    run(
        [
            "create",
            "--task-id",
            "demo-task",
            "--brief",
            "b",
            "--goal",
            "g",
            "--user",
            "u",
            "--deliverable",
            "d:desc",
            "--out",
            str(contract_path),
        ]
    )
    return contract_path


def test_old_style_evidence_without_acceptance_results_keeps_0_1_0_behavior(tmp_path: Path, capsys):
    """Backward compatibility: an evidence.json with no
    acceptance_criteria_results key must behave exactly like the published
    v0.1.0rc1 CLI -- no 'Completion state' line, same exit-code logic."""
    contract_path = _make_contract(tmp_path)
    result_dir = tmp_path / "result"
    result_dir.mkdir()
    (result_dir / "evidence.json").write_text(
        json.dumps({"hard_constraint_results": {"x": True}, "dimension_scores": {}}), encoding="utf-8"
    )
    rc = run(["evaluate", str(contract_path), str(result_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Completion state" not in out


def test_new_style_evidence_reports_pass(tmp_path: Path, capsys):
    contract_path = _make_contract(tmp_path)
    result_dir = tmp_path / "result"
    result_dir.mkdir()
    (result_dir / "evidence.json").write_text(
        json.dumps(
            {
                "hard_constraint_results": {},
                "dimension_scores": {},
                "acceptance_criteria_results": {},
            }
        ),
        encoding="utf-8",
    )
    rc = run(["evaluate", str(contract_path), str(result_dir)])
    out = capsys.readouterr().out
    # demo-task's factory-generated contract has zero acceptance criteria,
    # so must_criteria_met is vacuously true -> PASS.
    assert "Completion state: PASS" in out
    assert rc == 0


def test_new_style_evidence_reports_incomplete_when_must_criterion_missing(tmp_path: Path, capsys):
    contract_path = _make_contract(tmp_path)

    # Add a 'must' acceptance criterion via the public serialization API.
    from groundspec.contract.serialization import dump_document, load_document

    data = load_document(contract_path)
    data["acceptance"]["criteria"] = [
        {
            "id": "c1",
            "description": "d",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "e",
        }
    ]
    dump_document(data, contract_path)

    result_dir = tmp_path / "result"
    result_dir.mkdir()
    (result_dir / "evidence.json").write_text(
        json.dumps(
            {"hard_constraint_results": {}, "dimension_scores": {}, "acceptance_criteria_results": {}}
        ),
        encoding="utf-8",
    )
    rc = run(["evaluate", str(contract_path), str(result_dir)])
    out = capsys.readouterr().out
    assert "Completion state: INCOMPLETE" in out
    assert "missing evidence for: c1" in out
    assert rc == 1


def test_new_style_evidence_reports_blocked_when_open_question_unresolved(tmp_path: Path, capsys):
    contract_path = _make_contract(tmp_path)
    from groundspec.contract.serialization import dump_document, load_document

    data = load_document(contract_path)
    data["scope"]["open_questions"] = [
        {"question": "which target?", "classification": "blocking", "resolution_status": "open"}
    ]
    dump_document(data, contract_path)

    result_dir = tmp_path / "result"
    result_dir.mkdir()
    (result_dir / "evidence.json").write_text(
        json.dumps(
            {"hard_constraint_results": {}, "dimension_scores": {}, "acceptance_criteria_results": {}}
        ),
        encoding="utf-8",
    )
    rc = run(["evaluate", str(contract_path), str(result_dir)])
    out = capsys.readouterr().out
    assert "Completion state: BLOCKED" in out
    assert rc == 1
