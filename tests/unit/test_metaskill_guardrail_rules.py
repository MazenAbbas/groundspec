"""Guards the Meta-Skill's guardrail wording against silent removal.

These are presence checks on model-facing prose, not proof that a model
obeys it -- the behavioural evidence lives in docs/forward-tests-*.md. They
exist so a later edit cannot quietly delete a rule that a real user test
showed was necessary.
"""

from pathlib import Path

import groundspec.metaskill

CANONICAL = Path(groundspec.metaskill.__file__).parent / "canonical" / "groundspec"


def _read(rel: str) -> str:
    return (CANONICAL / rel).read_text(encoding="utf-8")


def test_skill_forbids_unconfirmed_installs_and_limit_changes():
    body = _read("SKILL.body.md")
    assert "Never install, download, or repair anything over the network" in body
    assert "never raise or relax a budget" in body


def test_authorization_section_lists_installs_and_limit_edits_as_external_actions():
    text = _read("references/execution-and-verification.md")
    assert "installing or downloading anything" in text
    assert "raising, relaxing, or otherwise editing a limit" in text
    assert "A broken or incomplete environment is not a license to fix it yourself" in text
    assert "Never raise, relax, or edit a budget or limit on your own" in text


def test_workflow_requires_reconciling_contract_text_before_evaluate():
    text = _read("references/task-contract-workflow.md")
    assert "Reconcile the contract with what actually happened, before evaluating" in text
    assert "The budget is the user's limit, not yours" in text


def test_research_guidance_documents_regulatory_source_recency():
    text = _read("references/domain-guidance/research-and-analysis.md")
    assert "Recency of regulatory sources" in text
    assert "24 months" in text


def test_evidence_guidance_separates_checked_and_failed_from_could_not_run():
    text = _read("references/execution-and-verification.md")
    assert "Record `false` only for a check that actually ran and failed" in text


def test_workflow_requires_feasibility_check_for_user_stated_limits():
    text = _read("references/task-contract-workflow.md")
    assert "Check that a stated limit is feasible before starting, and record it" in text


def test_workflow_documents_budget_flags_and_all_five_domains():
    text = _read("references/task-contract-workflow.md")
    assert "--tool-call-budget" in text
    assert "--time-budget-minutes" in text
    assert "product-management|data-science-ml" in text


def test_workflow_forbids_reordering_contract_steps_to_save_calls():
    text = _read("references/task-contract-workflow.md")
    assert "A tight limit never justifies skipping or reordering the contract steps" in text
