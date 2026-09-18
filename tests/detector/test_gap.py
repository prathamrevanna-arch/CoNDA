"""Unit tests for detector/signals/gap.py."""

import math
from detector.signals.gap import compute_counterfactual_gap, GapSignalResult


def _make_pool_tick(agent_id: str, price: float, side: str = "ask", ref_price: float = 100.0) -> dict:
    """Helper to create a well-formed quote tick with a known reference price."""
    # With oracle_price = ref_price and pool matching ref_price with 0 fee, ref is exactly ref_price
    return {
        "event": "quote",
        "agent_id": agent_id,
        "side": side,
        "price": price,
        "oracle_price": ref_price,
        "pool": {
            "reserve_x": 10000.0,
            "reserve_y": 10000.0 * ref_price,
            "fee_bps": 0,
        },
    }


def test_zero_deviation_and_identical_prices():
    # Both agents quote exactly the reference price (100.0)
    ticks = [
        _make_pool_tick("A1", 100.0) if i % 2 == 0 else _make_pool_tick("A2", 100.0)
        for i in range(50)
    ]
    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    assert res.value == 0.0
    assert res.median_gap_pct == 0.0
    assert res.persistence_ratio == 0.0
    assert res.sample_count == 50
    assert res.obs_a_count == 25
    assert res.obs_b_count == 25


def test_persistent_small_deviation():
    # Both agents quote 101.5 (1.5% above reference 100.0)
    # With GAP_REFERENCE_SCALE=0.05: normalized_value = (0.015 * 1.0) / 0.05 = 0.30
    ticks = [
        _make_pool_tick("A1", 101.5) if i % 2 == 0 else _make_pool_tick("A2", 101.5)
        for i in range(40)
    ]
    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    assert math.isclose(res.value, 0.30, abs_tol=0.01)  # 1.5% / 5% reference scale = 0.30
    assert math.isclose(res.median_gap_pct, 1.5, abs_tol=0.1)
    assert res.persistence_ratio == 1.0


def test_persistent_large_deviation():
    # Both agents quote 115.0 (15% above reference 100.0)
    # With GAP_REFERENCE_SCALE=0.05: tanh(0.15/0.05) = tanh(3) ≈ 0.9951 (near-max, NOT exactly 1.0)
    # tanh asymptotes to 1.0 — this is intentional: large gaps are near-max but still graded.
    ticks = [
        _make_pool_tick("A1", 115.0) if i % 2 == 0 else _make_pool_tick("A2", 115.0)
        for i in range(50)
    ]
    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    assert res.value > 0.99        # tanh(3) = 0.9951 — near max
    assert res.value < 1.0         # tanh never reaches exactly 1.0 (asymptote) — signal is graded
    assert math.isclose(res.median_gap_pct, 15.0, abs_tol=0.1)
    assert res.persistence_ratio == 1.0



def test_one_outlier_should_not_dominate():
    # 49 quotes at competitive reference (100.0), and 1 single rogue quote at 200.0 (100% gap)
    ticks = [
        _make_pool_tick("A1" if i % 2 == 0 else "A2", 100.0)
        for i in range(49)
    ]
    # Single outlier from A1
    ticks.append(_make_pool_tick("A1", 200.0))

    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    # Median deviation is 0.0, persistence ratio is 1/50 = 0.02
    assert res.value == 0.0
    assert res.median_gap_pct == 0.0
    assert res.persistence_ratio < 0.05


def test_zero_reference_price():
    # If pool reserves and oracle are zero/invalid, reference cannot be computed
    ticks = [
        {
            "event": "quote",
            "agent_id": "A1" if i % 2 == 0 else "A2",
            "price": 100.0,
            "oracle_price": 0.0,
            "pool": {"reserve_x": 0.0, "reserve_y": 0.0, "fee_bps": 0},
        }
        for i in range(20)
    ]
    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    assert res.value == 0.0
    assert res.sample_count == 0


def test_missing_prices():
    ticks = [
        {"event": "quote", "agent_id": "A1"},
        {"event": "quote", "agent_id": "A2", "price": None},
    ]
    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    assert res.value == 0.0
    assert res.sample_count == 0


def test_nan_and_infinity():
    ticks = [
        _make_pool_tick("A1", float("nan")),
        _make_pool_tick("A2", float("inf")),
        _make_pool_tick("A1", -100.0),
    ]
    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    assert res.value == 0.0
    assert not math.isnan(res.value)
    assert not math.isinf(res.value)


def test_empty_window():
    res = compute_counterfactual_gap([], ("A1", "A2"))
    assert res.value == 0.0
    assert res.sample_count == 0


def test_pair_with_missing_observations():
    # Only A1 quotes, A2 has zero quotes in the window
    ticks = [_make_pool_tick("A1", 105.0) for _ in range(20)]
    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    # Insufficient pairwise evidence
    assert res.value == 0.0
    assert res.obs_b_count == 0


def test_deterministic_result():
    ticks = [
        _make_pool_tick("A1", 104.3) if i % 2 == 0 else _make_pool_tick("A2", 104.3)
        for i in range(50)
    ]
    res1 = compute_counterfactual_gap(ticks, ("A1", "A2"))
    res2 = compute_counterfactual_gap(ticks, ("A1", "A2"))

    assert res1.value == res2.value
    assert res1.median_gap_pct == res2.median_gap_pct
    assert res1.persistence_ratio == res2.persistence_ratio
    assert res1.to_dict() == res2.to_dict()


def test_value_always_bounded_in_zero_to_one():
    # Extremely massive quotes (e.g. 10000.0 vs 100.0)
    ticks = [
        _make_pool_tick("A1", 10000.0) if i % 2 == 0 else _make_pool_tick("A2", 10000.0)
        for i in range(20)
    ]
    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    assert 0.0 <= res.value <= 1.0
    assert res.value <= 1.0


def test_to_dict_schema():
    ticks = [
        _make_pool_tick("A1", 104.3) if i % 2 == 0 else _make_pool_tick("A2", 104.3)
        for i in range(20)
    ]
    res = compute_counterfactual_gap(ticks, ("A1", "A2"))
    d = res.to_dict()
    assert "value" in d
    assert "median_gap_pct" in d
    assert "persistence_ratio" in d
    assert "sample_count" in d
    assert "side_evaluated" in d
