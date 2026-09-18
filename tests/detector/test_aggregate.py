"""Unit tests for detector/aggregate.py."""

from detector.aggregate import aggregate_signals, allocate_contributions, get_verdict


def test_zero_signals_returns_zero_risk():
    res = aggregate_signals({})
    assert res.risk_score == 0
    assert res.verdict == "LOW"
    assert res.contributions == {}


def test_only_gap_signal_renormalizes_weight():
    # Only gap present with value 0.70. Since it's the only signal, weight renormalizes to 1.0.
    res = aggregate_signals({"counterfactual_gap": 0.70})
    assert res.risk_score == 70
    assert res.verdict == "HIGH"
    assert res.contributions == {"counterfactual_gap": 70}
    assert sum(res.contributions.values()) == res.risk_score


def test_only_sync_signal_renormalizes_weight():
    # Only sync present with value 0.50. Renormalizes to 1.0.
    res = aggregate_signals({"sync_under_shock": 0.50})
    assert res.risk_score == 50
    assert res.verdict == "MEDIUM"
    assert res.contributions == {"sync_under_shock": 50}
    assert sum(res.contributions.values()) == res.risk_score


def test_both_signals_aggregation():
    # gap = 0.80 (weight 0.60 -> 48.0)
    # sync = 0.60 (weight 0.40 -> 24.0)
    # total = 72.0 -> risk_score = 72
    res = aggregate_signals(
        {"counterfactual_gap": 0.80, "sync_under_shock": 0.60},
        weights={"counterfactual_gap": 0.60, "sync_under_shock": 0.40},
    )
    assert res.risk_score == 72
    assert res.verdict == "HIGH"
    assert res.contributions["counterfactual_gap"] == 48
    assert res.contributions["sync_under_shock"] == 24
    assert sum(res.contributions.values()) == 72


def test_verdict_thresholds():
    assert get_verdict(0) == "LOW"
    assert get_verdict(39) == "LOW"
    assert get_verdict(40) == "MEDIUM"
    assert get_verdict(55) == "MEDIUM"
    assert get_verdict(69) == "MEDIUM"
    assert get_verdict(70) == "HIGH"
    assert get_verdict(100) == "HIGH"


def test_contributions_sum_exactly_to_risk_score():
    # Test across multiple fractional inputs where naive independent rounding would cause sum drift
    test_cases = [
        {"counterfactual_gap": 0.43, "sync_under_shock": 0.82},
        {"counterfactual_gap": 0.333, "sync_under_shock": 0.667},
        {"counterfactual_gap": 0.043, "sync_under_shock": 0.82},
        {"counterfactual_gap": 0.17, "sync_under_shock": 0.19},
        {"counterfactual_gap": 0.999, "sync_under_shock": 0.001},
    ]
    for case in test_cases:
        res = aggregate_signals(case)
        assert sum(res.contributions.values()) == res.risk_score
        assert 0 <= res.risk_score <= 100


def test_missing_signal_omitted_from_output():
    # When sync_under_shock is absent, it must NOT appear in contributions
    res = aggregate_signals({"counterfactual_gap": 0.50})
    assert "sync_under_shock" not in res.contributions
    assert "counterfactual_gap" in res.contributions


def test_nan_signal_treated_safely():
    res = aggregate_signals({"counterfactual_gap": float("nan"), "sync_under_shock": 0.50})
    assert sum(res.contributions.values()) == res.risk_score
    assert not any(map(lambda v: v != v, res.contributions.values()))


def test_infinity_signal_clamped_to_one():
    res = aggregate_signals({"counterfactual_gap": float("inf"), "sync_under_shock": 0.0})
    assert res.normalized_values["counterfactual_gap"] == 1.0
    assert 0 <= res.risk_score <= 100
    assert sum(res.contributions.values()) == res.risk_score


def test_negative_signal_clamped_to_zero():
    res = aggregate_signals({"counterfactual_gap": -0.5, "sync_under_shock": 0.5})
    assert res.normalized_values["counterfactual_gap"] == 0.0
    assert res.contributions["counterfactual_gap"] == 0
    assert sum(res.contributions.values()) == res.risk_score


def test_signal_greater_than_one_clamped_to_one():
    res = aggregate_signals({"counterfactual_gap": 5.0, "sync_under_shock": 0.5})
    assert res.normalized_values["counterfactual_gap"] == 1.0
    assert sum(res.contributions.values()) == res.risk_score


def test_deterministic_output():
    signals = {"counterfactual_gap": 0.45, "sync_under_shock": 0.75}
    res1 = aggregate_signals(signals)
    res2 = aggregate_signals(signals)
    assert res1.risk_score == res2.risk_score
    assert res1.verdict == res2.verdict
    assert res1.contributions == res2.contributions
    assert res1.to_dict() == res2.to_dict()


def test_tie_breaking_during_contribution_allocation():
    # Two signals with identical remainder:
    # raw: s1 = 10.5, s2 = 10.5 -> total_target = 21
    # floor: s1 = 10, s2 = 10 (sum 20) -> surplus = 1
    # Tie-breaking by alphabetical order: 'signal_a' vs 'signal_b'
    raw = {"signal_b": 10.5, "signal_a": 10.5}
    allocated = allocate_contributions(raw, total_target=21)
    assert sum(allocated.values()) == 21
    # 'signal_a' comes before 'signal_b' alphabetically, so it receives the tie-broken point
    assert allocated["signal_a"] == 11
    assert allocated["signal_b"] == 10
