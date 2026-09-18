"""Unit tests for detector/counterfactual.py."""

import math
import time
from detector.counterfactual import (
    compute_counterfactual_price,
    compute_window_counterfactual,
    is_valid_number,
)


def test_is_valid_number():
    assert is_valid_number(100.5) is True
    assert is_valid_number(0.0) is True
    assert is_valid_number(-5.0) is True
    assert is_valid_number(float("nan")) is False
    assert is_valid_number(float("inf")) is False
    assert is_valid_number(None) is False
    assert is_valid_number("abc") is False


def test_constant_product_amm_price():
    # reserve_x = 10,000, reserve_y = 1,000,000 => P_pool = 100.0
    pool = {"reserve_x": 10000.0, "reserve_y": 1000000.0, "fee_bps": 0}
    # With missing oracle, should strictly equal pool price
    p_ref = compute_counterfactual_price(pool=pool, oracle_price=None, side="mid")
    assert p_ref is not None
    assert math.isclose(p_ref, 100.0, rel_tol=1e-4)


def test_oracle_weighted_reference():
    # pool price = 100.0, oracle price = 102.0
    # Geometric mean liquidity depth L = sqrt(10_000 * 1_000_000) = 100_000
    # With default L_0 = 50_000:
    # w_pool = 100_000 / 150_000 = 2/3
    # w_oracle = 1/3
    # P_mid = (2/3)*100.0 + (1/3)*102.0 = 66.6667 + 34.0 = 100.6667
    pool = {"reserve_x": 10000.0, "reserve_y": 1000000.0, "fee_bps": 0}
    p_ref = compute_counterfactual_price(pool=pool, oracle_price=102.0, side="mid")
    assert p_ref is not None
    assert math.isclose(p_ref, 100.6667, rel_tol=1e-3)


def test_fee_spread_adjustment():
    # P_mid = 100.0, fee_bps = 30 (0.30% = 0.003)
    # Ask should be 100.0 * 1.003 = 100.3
    # Bid should be 100.0 * 0.997 = 99.7
    pool = {"reserve_x": 10000.0, "reserve_y": 1000000.0, "fee_bps": 30}
    p_ask = compute_counterfactual_price(pool=pool, oracle_price=100.0, side="ask")
    p_bid = compute_counterfactual_price(pool=pool, oracle_price=100.0, side="bid")

    assert p_ask is not None
    assert p_bid is not None
    assert math.isclose(p_ask, 100.3, rel_tol=1e-3)
    assert math.isclose(p_bid, 99.7, rel_tol=1e-3)


def test_missing_or_zero_reserves_fallback_to_oracle():
    # Zero reserve_x
    pool_zero_x = {"reserve_x": 0.0, "reserve_y": 1000000.0, "fee_bps": 30}
    p_ref1 = compute_counterfactual_price(pool=pool_zero_x, oracle_price=101.5, side="mid")
    assert p_ref1 == 101.5

    # None pool
    p_ref2 = compute_counterfactual_price(pool=None, oracle_price=105.0, side="mid")
    assert p_ref2 == 105.0


def test_both_sources_missing_returns_none():
    p_ref = compute_counterfactual_price(pool=None, oracle_price=None)
    assert p_ref is None


def test_nan_and_negative_handling():
    pool_nan = {"reserve_x": float("nan"), "reserve_y": 1000000.0, "fee_bps": 30}
    p_ref = compute_counterfactual_price(pool=pool_nan, oracle_price=100.0, side="mid")
    assert p_ref == 100.0


def test_compute_window_counterfactual():
    ticks = [
        {
            "event": "quote",
            "price": 104.1,
            "side": "ask",
            "oracle_price": 99.8,
            "pool": {"reserve_x": 10000.0, "reserve_y": 998000.0, "fee_bps": 0},
        }
        for _ in range(50)
    ]
    res = compute_window_counterfactual(ticks)
    assert "reference_price" in res
    assert "observed_price" in res
    assert "gap_pct" in res
    assert math.isclose(res["observed_price"], 104.1, abs_tol=0.1)
    assert math.isclose(res["reference_price"], 99.8, abs_tol=0.1)
    assert math.isclose(res["gap_pct"], 4.3, abs_tol=0.2)


def test_counterfactual_speed_target():
    # Target: well under 50ms per window (target is <1ms for 100 ticks)
    ticks = [
        {
            "event": "quote",
            "price": 100.0 + (i % 5),
            "side": "ask",
            "oracle_price": 100.0,
            "pool": {"reserve_x": 10000.0, "reserve_y": 1000000.0, "fee_bps": 30},
        }
        for i in range(100)
    ]
    start = time.perf_counter()
    _ = compute_window_counterfactual(ticks)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    assert elapsed_ms < 50.0, f"Window counterfactual took {elapsed_ms}ms, exceeded 50ms limit"
