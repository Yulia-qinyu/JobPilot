from scripts.evaluate_discovery_phase7d import benchmark, render


def test_phase7d_artifact_covers_ab_grounding_constraints_and_privacy() -> None:
    report = render()
    assert report.count("| OFF / ON / Same |") == 25
    assert "Candidate context provider calls while OFF = 0" in report
    assert "Claude personalization calls = 0" in report
    assert "Source refetch count on toggle = 0" in report
    assert "Shanghai FinTech Product" in report
    assert "PotentialGap" in report and "Unknown" in report and "Supported" in report
    assert report.count("| Yes / No |") >= 10


def test_500_result_personalization_is_bounded_and_fast() -> None:
    assert benchmark(500) < 500
