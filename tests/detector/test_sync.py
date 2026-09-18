"""Unit tests for detector/signals/sync.py."""

import math
from detector.signals.sync import compute_sync_under_shock, SyncSignalResult


def test_no_shock_returns_zero():
    ticks = [
        {"t": 1, "event": "quote", "agent_id": "A1", "price": 100.0},
        {"t": 2, "event": "quote", "agent_id": "A2", "price": 100.5},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res.value == 0.0
    assert res.shocks_present == 0
    assert res.shocks_evaluated == 0


def test_empty_input_returns_zero():
    res = compute_sync_under_shock([], ("A1", "A2"))
    assert res.value == 0.0
    assert res.shocks_present == 0


def test_one_agent_returns_zero():
    ticks = [
        {"t": 10, "event": "shock", "shock": {"type": "oracle_jump"}},
        {"t": 12, "event": "quote", "agent_id": "A1", "price": 95.0},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res.value == 0.0
    assert res.shocks_evaluated == 0


def test_two_agents_with_tight_reaction_timing_conservative_score():
    # Only 2 agents exist in this market
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "jump"}},
        {"t": 102, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": 103, "event": "quote", "agent_id": "A2", "price": 95.5},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    # Timing diff is measured
    assert res.pair_delay_diff == 1.0
    # Because there are no other agents to establish an all-pairs baseline, score is conservative low/neutral
    assert res.has_sufficient_baseline is False
    assert res.value <= 0.30


def test_pair_significantly_more_synchronized_than_baseline():
    # A1 & A2 react tightly (102 and 103 -> diff 1 tick)
    # A3 & A4 react late and dispersed (120 and 126 -> delays 20, 26)
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "oracle_jump"}},
        {"t": 102, "event": "quote", "agent_id": "A1", "price": 94.0},
        {"t": 103, "event": "quote", "agent_id": "A2", "price": 94.2},
        {"t": 120, "event": "quote", "agent_id": "A3", "price": 94.5},
        {"t": 126, "event": "quote", "agent_id": "A4", "price": 94.8},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res.has_sufficient_baseline is True
    assert res.pair_delay_diff == 1.0
    assert res.baseline_delay_diff >= 15.0
    # High score because pair timing was uniquely tight compared to market
    assert res.value >= 0.70


def test_all_agents_reacting_almost_simultaneously_gives_low():
    # Public shock at t=100.
    # Everyone reacts within 1 tick! Normal competitive behavior.
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "oracle_jump"}},
        {"t": 101, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": 101, "event": "quote", "agent_id": "A2", "price": 95.1},
        {"t": 102, "event": "quote", "agent_id": "A3", "price": 95.2},
        {"t": 102, "event": "quote", "agent_id": "A4", "price": 95.3},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res.has_sufficient_baseline is True
    # Target pair diff = 0, baseline diff = 1
    # Jitter scaling ensures this does NOT flag as suspicious (value <= 0.30)
    assert res.value <= 0.30


def test_pair_not_more_synchronized_than_baseline_gives_zero():
    # Target pair (A1, A2) reacts with a large 18-tick gap (102 vs 120)
    # Others (A3, A4) react with a tight 1-tick gap (102 vs 103)
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "jump"}},
        {"t": 102, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": 102, "event": "quote", "agent_id": "A3", "price": 95.1},
        {"t": 103, "event": "quote", "agent_id": "A4", "price": 95.2},
        {"t": 120, "event": "quote", "agent_id": "A2", "price": 95.3},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res.pair_delay_diff == 18.0
    assert res.value == 0.0


def test_baseline_equals_zero_gives_zero():
    # Other agents react at identical ticks (delays are identical)
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "jump"}},
        {"t": 105, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": 105, "event": "quote", "agent_id": "A2", "price": 95.1},
        {"t": 105, "event": "quote", "agent_id": "A3", "price": 95.2},
        {"t": 105, "event": "quote", "agent_id": "A4", "price": 95.3},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res.baseline_delay_diff == 0.0
    assert res.value == 0.0


def test_only_one_agent_reacts_gives_zero():
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "jump"}},
        {"t": 102, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": 103, "event": "quote", "agent_id": "A3", "price": 95.1},
        {"t": 104, "event": "quote", "agent_id": "A4", "price": 95.2},
        # A2 does not quote after shock
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res.value == 0.0
    assert res.shocks_evaluated == 0


def test_no_agent_reacts_gives_zero():
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "jump"}},
        # No quotes at all after shock
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res.value == 0.0
    assert res.shocks_evaluated == 0


def test_repeated_identical_quotes_ignored_until_new_quote():
    ticks = [
        # Pre-shock quotes
        {"t": 90, "event": "quote", "agent_id": "A1", "price": 100.0},
        {"t": 91, "event": "quote", "agent_id": "A2", "price": 100.0},
        {"t": 100, "event": "shock", "shock": {"type": "jump"}},
        # Repeated identical quotes (stale, unadjusted quotes)
        {"t": 101, "event": "quote", "agent_id": "A1", "price": 100.0},
        {"t": 102, "event": "quote", "agent_id": "A2", "price": 100.0},
        # Genuine price re-quotes after shock
        {"t": 115, "event": "quote", "agent_id": "A1", "price": 96.0},
        {"t": 116, "event": "quote", "agent_id": "A2", "price": 96.1},
        {"t": 130, "event": "quote", "agent_id": "A3", "price": 96.2},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    # Reactions should be counted at t=115 and t=116 (delay 15 and 16, diff = 1)
    assert res.agent_a_delay == 15.0
    assert res.agent_b_delay == 16.0
    assert res.pair_delay_diff == 1.0


def test_multiple_shocks_aggregated():
    ticks = [
        # Shock 1
        {"t": 100, "event": "shock", "shock": {"type": "jump1"}},
        {"t": 102, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": 103, "event": "quote", "agent_id": "A2", "price": 95.0},
        {"t": 120, "event": "quote", "agent_id": "A3", "price": 95.0},
        # Shock 2
        {"t": 200, "event": "shock", "shock": {"type": "jump2"}},
        {"t": 202, "event": "quote", "agent_id": "A1", "price": 90.0},
        {"t": 203, "event": "quote", "agent_id": "A2", "price": 90.0},
        {"t": 225, "event": "quote", "agent_id": "A3", "price": 90.0},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res.shocks_present == 2
    assert res.shocks_evaluated == 2
    assert res.value > 0.60


def test_nan_timestamps_handled_safely():
    ticks = [
        {"t": float("nan"), "event": "shock", "shock": {"type": "jump"}},
        {"t": 102, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": 103, "event": "quote", "agent_id": "A2", "price": 95.0},
        {"t": 120, "event": "quote", "agent_id": "A3", "price": 95.0},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert not math.isnan(res.value)
    assert not math.isinf(res.value)
    assert 0.0 <= res.value <= 1.0


def test_invalid_timestamps_fallback_to_indices():
    ticks = [
        {"t": "not_a_number", "event": "shock", "shock": {"type": "jump"}},
        {"t": None, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": None, "event": "quote", "agent_id": "A2", "price": 95.0},
        {"t": None, "event": "quote", "agent_id": "A3", "price": 95.0},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert not math.isnan(res.value)
    assert 0.0 <= res.value <= 1.0


def test_deterministic_output():
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "jump"}},
        {"t": 102, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": 103, "event": "quote", "agent_id": "A2", "price": 95.1},
        {"t": 120, "event": "quote", "agent_id": "A3", "price": 95.2},
    ]
    res1 = compute_sync_under_shock(ticks, ("A1", "A2"))
    res2 = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert res1.value == res2.value
    assert res1.to_dict() == res2.to_dict()


def test_value_strictly_bounded_between_zero_and_one():
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "jump"}},
        {"t": 101, "event": "quote", "agent_id": "A1", "price": 95.0},
        {"t": 101, "event": "quote", "agent_id": "A2", "price": 95.0},
        {"t": 1000000, "event": "quote", "agent_id": "A3", "price": 95.0},
    ]
    res = compute_sync_under_shock(ticks, ("A1", "A2"))
    assert 0.0 <= res.value <= 1.0
