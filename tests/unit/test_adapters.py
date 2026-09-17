from groundspec.adapters.claude_skill import render_claude_skill
from groundspec.adapters.codex_skill import render_codex_skill
from groundspec.adapters.generic import render_generic_prompt
from groundspec.contract.factory import new_contract
from groundspec.packs.registry import select_packs_for_contract
from groundspec.rules.evaluator import evaluate_rule_set
from groundspec.rules.precedence import build_rule_set


def _contract_and_rules():
    contract = new_contract(
        task_id="research-market",
        raw_user_brief="research whether this market is promising",
        normalized_problem_statement="No evidence exists yet on whether this market is viable.",
        goal="Produce a go/no-go recommendation on entering the market, with sources.",
        target_users=["the founder deciding whether to build this"],
        expected_deliverables=[{"name": "market_report", "description": "A sourced market analysis"}],
        risk_overlays=["informational"],
        risk_level="low",
    )
    contract["routing"]["domain_packs"] = [{"pack_id": "research", "version": "0.1.0"}]
    contract["acceptance"]["criteria"] = [
        {
            "id": "sourced-recommendation",
            "description": "Recommendation is backed by at least 3 primary sources",
            "priority": "must",
            "verification_method": "manual_inspection",
            "evidence_required": "citations present next to each claim",
        }
    ]
    packs = select_packs_for_contract(contract)
    rule_set = build_rule_set(packs)
    applied = evaluate_rule_set(rule_set, contract)
    return contract, applied


def test_claude_skill_frontmatter_shape():
    contract, applied = _contract_and_rules()
    files = render_claude_skill(contract, applied)
    assert set(files) == {"SKILL.md", "reference.md"}
    assert files["SKILL.md"].startswith("---\n")
    assert "name: research-market" in files["SKILL.md"]
    assert "description:" in files["SKILL.md"]


def test_codex_skill_frontmatter_shape():
    contract, applied = _contract_and_rules()
    files = render_codex_skill(contract, applied)
    assert set(files) == {"SKILL.md", "references/contract.md"}
    assert files["SKILL.md"].startswith("---\n")
    assert "name: research-market" in files["SKILL.md"]


def test_generic_prompt_has_limitations_header():
    contract, applied = _contract_and_rules()
    text = render_generic_prompt(contract, applied)
    assert "Limitations of prompt-only enforcement" in text


def test_all_three_adapters_agree_on_load_bearing_content():
    contract, applied = _contract_and_rules()
    claude_text = "\n".join(render_claude_skill(contract, applied).values())
    codex_text = "\n".join(render_codex_skill(contract, applied).values())
    generic_text = render_generic_prompt(contract, applied)

    must_appear_everywhere = [
        contract["brief"]["goal"],
        "sourced-recommendation",
        "citations present next to each claim",
    ]
    hard_constraint_requirements = [
        a.qualified.rule["requirement"]
        for a in applied
        if a.applies and a.severity == "hard_constraint"
    ]
    assert hard_constraint_requirements, "fixture should trigger at least one hard constraint"
    must_appear_everywhere.extend(hard_constraint_requirements)

    for fragment in must_appear_everywhere:
        assert fragment in claude_text, f"missing from claude adapter: {fragment!r}"
        assert fragment in codex_text, f"missing from codex adapter: {fragment!r}"
        assert fragment in generic_text, f"missing from generic adapter: {fragment!r}"
