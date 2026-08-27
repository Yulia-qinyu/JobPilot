from scripts.evaluate_discovery_phase7c1 import render


def test_phase7c1_artifact_is_computed_from_current_deterministic_rules() -> None:
    report = render()
    assert "大模型应用, AI 平台" in report
    assert "| 帮我找 AI 工作 | Required | job_function |" in report
    assert "| 北京 AI Agent 产品经理 大厂 | Optional | business_scenario |" in report
    assert "| Engineering Manager, Agent Cloud Platform | engineering | Low |" in report
    assert "| Applied AI Engineer | engineering | Low |" in report
    assert "| True experience |" in report and "明确要求 6+ 年经验" in report
    assert "| Responsibility |" in report and "| None |" in report
    assert "Claude calls: 0" in report
