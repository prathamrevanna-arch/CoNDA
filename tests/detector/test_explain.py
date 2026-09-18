"""Unit tests for detector/explain.py."""

from detector.explain import explain_gap, explain_sync, explain_signal, explain_signals
from detector.signals.gap import GapSignalResult
from detector.signals.sync import SyncSignalResult


def test_gap_explanation_contains_metrics():
    # Construct a representative GapSignalResult
    gap_res = GapSignalResult(
        value=0.043,
        median_gap_pct=4.3,
        mean_gap_pct=4.5,
        signed_median_gap_pct=4.3,
        persistence_ratio=0.82,
        sample_count=50,
        obs_a_count=25,
        obs_b_count=25,
        observed_median_price=104.1,
        reference_median_price=99.8,
        side_evaluated="ask",
    )
    explanation = explain_gap(gap_res)
    assert "4.3%" in explanation
    assert "above" in explanation
    assert "104.1 vs 99.8" in explanation
    assert "82%" in explanation


def test_gap_explanation_zero_deviation():
    gap_res = GapSignalResult(
        value=0.0,
        median_gap_pct=0.0,
        mean_gap_pct=0.0,
        signed_median_gap_pct=0.0,
        persistence_ratio=0.0,
        sample_count=20,
        obs_a_count=10,
        obs_b_count=10,
        observed_median_price=100.0,
        reference_median_price=100.0,
        side_evaluated="ask",
    )
    explanation = explain_gap(gap_res)
    assert "aligned with the competitive reference" in explanation


def test_gap_explanation_insufficient_samples():
    explanation = explain_gap({"sample_count": 0})
    assert "Insufficient comparable quote observations" in explanation


def test_sync_explanation_contains_timing_and_baseline():
    sync_res = SyncSignalResult(
        value=0.82,
        pair_delay_diff=1.0,
        baseline_delay_diff=17.0,
        shocks_evaluated=1,
        shocks_present=1,
        reacting_agents_count=4,
        agent_a_delay=2.0,
        agent_b_delay=3.0,
        has_sufficient_baseline=True,
    )
    explanation = explain_sync(sync_res)
    assert "1 tick" in explanation
    assert "17-tick" in explanation
    assert "baseline" in explanation


def test_sync_explanation_no_shock():
    explanation = explain_sync({"shocks_present": 0})
    assert "No public shock occurred in this window" in explanation


def test_sync_explanation_insufficient_reaction_data():
    explanation = explain_sync({"shocks_present": 1, "shocks_evaluated": 0})
    assert "Insufficient post-shock reaction data" in explanation


def test_sync_explanation_insufficient_baseline():
    sync_res = SyncSignalResult(
        value=0.0,
        pair_delay_diff=1.0,
        baseline_delay_diff=0.0,
        shocks_evaluated=1,
        shocks_present=1,
        reacting_agents_count=2,
        agent_a_delay=2.0,
        agent_b_delay=3.0,
        has_sufficient_baseline=False,
    )
    explanation = explain_sync(sync_res)
    assert "insufficient market agents reacted" in explanation


def test_missing_fields_and_none_handling():
    assert isinstance(explain_gap(None), str)
    assert isinstance(explain_sync(None), str)
    assert isinstance(explain_gap({}), str)
    assert isinstance(explain_sync({}), str)


def test_nan_and_infinity_handling():
    bad_gap = {
        "sample_count": 10,
        "median_gap_pct": float("nan"),
        "observed_median_price": float("inf"),
        "reference_median_price": float("-inf"),
    }
    exp = explain_gap(bad_gap)
    assert "nan" not in exp.lower()
    assert "inf" not in exp.lower()

    bad_sync = {
        "shocks_present": 1,
        "shocks_evaluated": 1,
        "pair_delay_diff": float("nan"),
        "baseline_delay_diff": float("inf"),
    }
    exp_sync = explain_sync(bad_sync)
    assert "nan" not in exp_sync.lower()
    assert "inf" not in exp_sync.lower()


def test_unknown_signal():
    exp = explain_signal("order_flow_toxicity", {"value": 0.4567})
    assert "order_flow_toxicity" in exp
    assert "0.4567" in exp


def test_deterministic_output():
    data = {"sample_count": 50, "median_gap_pct": 5.0, "persistence_ratio": 0.75}
    exp1 = explain_gap(data)
    exp2 = explain_gap(data)
    assert exp1 == exp2


def test_explain_signals_batch():
    signals = {
        "counterfactual_gap": {"sample_count": 0},
        "sync_under_shock": {"shocks_present": 0},
    }
    batch = explain_signals(signals)
    assert "counterfactual_gap" in batch
    assert "sync_under_shock" in batch


def test_no_guilt_or_collusion_claims():
    # Ensure neither generator ever emits accusatory terms
    forbidden_terms = ["guilty", "collud", "cartel", "intentional", "convict"]

    samples = [
        explain_gap(GapSignalResult(0.9, 15.0, 15.0, 15.0, 1.0, 100, 50, 50, 115.0, 100.0, "ask")),
        explain_sync(SyncSignalResult(0.95, 0.0, 25.0, 1, 1, 5, 1.0, 1.0, True)),
        explain_gap(None),
        explain_sync(None),
        explain_signal("test", 0.5),
    ]

    for text in samples:
        lower_text = text.lower()
        for term in forbidden_terms:
            assert term not in lower_text, f"Accusatory term '{term}' found in explanation: {text}"
