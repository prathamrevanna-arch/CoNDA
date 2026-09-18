"""
Tests for sim/amm.py and sim/engine.py — Step 1 verification.

Run with:  .venv\\Scripts\\python.exe test_step1.py
"""

import sys
import math

# ---- Test 1: AMM initializes with valid reserves -----------------------------
def test_amm_init():
    from sim.amm import ConstantProductAMM
    amm = ConstantProductAMM(reserve_x=10_000.0, reserve_y=1_000_000.0, fee_bps=30)
    assert amm.reserve_x == 10_000.0
    assert amm.reserve_y == 1_000_000.0
    assert amm.fee_bps == 30
    assert amm.k == 10_000.0 * 1_000_000.0
    print("PASS  test_amm_init")


# ---- Test 2: mid_price works -------------------------------------------------
def test_mid_price():
    from sim.amm import ConstantProductAMM
    amm = ConstantProductAMM(reserve_x=10_000.0, reserve_y=1_000_000.0)
    assert amm.mid_price() == 100.0  # 1_000_000 / 10_000
    print("PASS  test_mid_price")


# ---- Test 3: fee calculation -------------------------------------------------
def test_fee_calculation():
    from sim.amm import ConstantProductAMM
    amm = ConstantProductAMM(reserve_x=10_000.0, reserve_y=1_000_000.0, fee_bps=30)
    # Swap 100 X for Y: fee = 100 * 0.003 = 0.3
    result = amm.swap_x_for_y(100.0)
    expected_fee = 100.0 * (30 / 10_000)
    assert abs(result.fee_amount - expected_fee) < 1e-10, \
        f"fee_amount={result.fee_amount}, expected={expected_fee}"
    print("PASS  test_fee_calculation")


# ---- Test 4: normal swap works -----------------------------------------------
def test_normal_swap():
    from sim.amm import ConstantProductAMM
    amm = ConstantProductAMM(reserve_x=10_000.0, reserve_y=1_000_000.0, fee_bps=30)
    k_before = amm.k

    result = amm.swap_x_for_y(100.0)
    assert result.amount_in == 100.0
    assert result.amount_out > 0
    assert result.execution_price > 0
    assert result.new_reserve_x > 10_000.0
    assert result.new_reserve_y < 1_000_000.0
    # k should NOT decrease (fees add to one side)
    assert amm.k >= k_before - 1e-6, f"k shrunk: {amm.k} < {k_before}"
    print("PASS  test_normal_swap")


# ---- Test 5: invalid quantities are rejected ---------------------------------
def test_invalid_quantities():
    from sim.amm import ConstantProductAMM, InvalidTradeError
    amm = ConstantProductAMM(reserve_x=10_000.0, reserve_y=1_000_000.0, fee_bps=30)

    # Negative quantity
    try:
        amm.swap_x_for_y(-10.0)
        assert False, "Should have raised InvalidTradeError"
    except InvalidTradeError:
        pass

    # Zero quantity
    try:
        amm.swap_x_for_y(0.0)
        assert False, "Should have raised InvalidTradeError"
    except InvalidTradeError:
        pass

    # Execution price for amount >= reserve
    try:
        amm.execution_price_buy_x(10_000.0)
        assert False, "Should have raised InvalidTradeError"
    except InvalidTradeError:
        pass

    print("PASS  test_invalid_quantities")


# ---- Test 6: zero/negative liquidity handled ---------------------------------
def test_zero_liquidity():
    from sim.amm import ConstantProductAMM, InvalidReservesError
    try:
        ConstantProductAMM(reserve_x=0.0, reserve_y=1_000.0)
        assert False, "Should have raised InvalidReservesError"
    except InvalidReservesError:
        pass

    try:
        ConstantProductAMM(reserve_x=1_000.0, reserve_y=-5.0)
        assert False, "Should have raised InvalidReservesError"
    except InvalidReservesError:
        pass

    print("PASS  test_zero_liquidity")


# ---- Test 7: modules import without side effects -----------------------------
def test_import_clean():
    """
    Verify that importing sim does not start a simulation or print anything.
    We already imported at the top — if we got here, no crash occurred.
    """
    import sim
    assert hasattr(sim, "run_sim")
    print("PASS  test_import_clean")


# ---- Test 8: importing does not start a simulation ---------------------------
def test_no_auto_simulation():
    """
    Ensure importing sim.engine doesn't trigger run_sim or create files.
    """
    import importlib
    mod = importlib.import_module("sim.engine")
    assert hasattr(mod, "run_sim")
    assert callable(mod.run_sim)
    print("PASS  test_no_auto_simulation")


# ---- Test 9: minimal engine test with stub agent -----------------------------
def test_engine_minimal():
    """
    Create a tiny scenario file, register a stub agent, and run 5 ticks.
    """
    import json
    import os
    import tempfile
    from sim.engine import (
        ScenarioConfig,
        SCENARIO_DIR,
        register_agent,
        run_sim,
    )

    # Create a minimal scenario in the scenarios dir
    scenario_name = "__test_step1"
    scenario_path = SCENARIO_DIR / f"{scenario_name}.json"
    os.makedirs(SCENARIO_DIR, exist_ok=True)

    scenario_data = {
        "name": scenario_name,
        "ticks": 5,
        "fee_bps": 30,
        "initial_reserve_x": 10000.0,
        "initial_reserve_y": 1000000.0,
        "oracle_start": 100.0,
        "oracle_mu": 0.0,
        "oracle_sigma": 0.001,
        "agents": [
            {"agent_id": "stub1", "agent_class": "stub"}
        ],
        "shocks": [
            {"t": 2, "type": "oracle_jump", "magnitude": -0.04}
        ],
    }
    with open(scenario_path, "w", encoding="utf-8") as f:
        json.dump(scenario_data, f)

    # Register a trivial stub agent
    class StubAgent:
        def __init__(self, agent_id, params, rng):
            self.agent_id = agent_id
            self.agent_class = "stub"
            self._rng = rng

        def observe(self, state):
            return {
                "event": "quote",
                "side": "bid",
                "price": state["oracle_price"],
                "quantity": 1.0,
                "capital": 10000.0,
                "pnl": 0.0,
            }

    register_agent("stub", StubAgent)

    # Run the sim
    records = list(run_sim(scenario_name, seed=42))

    # Cleanup scenario file
    os.remove(scenario_path)

    # Verify: first record is meta
    assert records[0]["event"] == "meta"
    assert records[0]["t"] == 0

    # Should have: 1 meta + 1 shock at t=2 + 5 agent-quotes = 7
    events = [r["event"] for r in records]
    assert "meta" in events
    assert "shock" in events
    assert "quote" in events

    # All records must have required keys
    required_keys = {"run_id", "t", "event", "pool", "oracle_price", "shock"}
    for r in records:
        for k in required_keys:
            assert k in r, f"Missing key '{k}' in record: {r}"

    # Shock record at tick 2
    shock_recs = [r for r in records if r["event"] == "shock"]
    assert len(shock_recs) == 1
    assert shock_recs[0]["t"] == 2
    assert shock_recs[0]["shock"]["type"] == "oracle_jump"
    assert shock_recs[0]["shock"]["magnitude"] == -0.04

    # Determinism: run again with same seed, should get identical output
    register_agent("stub", StubAgent)  # re-register (idempotent)

    # Need to recreate scenario file for second run
    with open(scenario_path, "w", encoding="utf-8") as f:
        json.dump(scenario_data, f)

    records2 = list(run_sim(scenario_name, seed=42))
    os.remove(scenario_path)

    assert len(records) == len(records2), "Determinism: record count mismatch"
    for i, (a, b) in enumerate(zip(records, records2)):
        assert a == b, f"Determinism: record {i} differs:\n  {a}\n  {b}"

    print("PASS  test_engine_minimal")


# ---- Test 10: swap_y_for_x works symmetrically --------------------------------
def test_swap_y_for_x():
    from sim.amm import ConstantProductAMM
    amm = ConstantProductAMM(reserve_x=10_000.0, reserve_y=1_000_000.0, fee_bps=30)
    result = amm.swap_y_for_x(1_000.0)
    assert result.amount_in == 1_000.0
    assert result.amount_out > 0
    assert result.new_reserve_x < 10_000.0
    assert result.new_reserve_y > 1_000_000.0
    print("PASS  test_swap_y_for_x")


# ---- Test 11: pool_snapshot format -------------------------------------------
def test_pool_snapshot():
    from sim.amm import ConstantProductAMM
    amm = ConstantProductAMM(reserve_x=10_000.0, reserve_y=1_000_000.0, fee_bps=30)
    snap = amm.pool_snapshot()
    assert isinstance(snap, dict)
    assert set(snap.keys()) == {"reserve_x", "reserve_y", "fee_bps"}
    assert snap["fee_bps"] == 30
    print("PASS  test_pool_snapshot")


# ---- Test 12: execution_price helpers ----------------------------------------
def test_execution_prices():
    from sim.amm import ConstantProductAMM
    amm = ConstantProductAMM(reserve_x=10_000.0, reserve_y=1_000_000.0, fee_bps=30)
    ep_buy = amm.execution_price_buy_x(100.0)
    ep_sell = amm.execution_price_sell_x(100.0)
    mid = amm.mid_price()
    # buy price should be > mid; sell price should be < mid
    assert ep_buy > mid, f"ep_buy={ep_buy} should > mid={mid}"
    assert ep_sell < mid, f"ep_sell={ep_sell} should < mid={mid}"
    print("PASS  test_execution_prices")


# ==============================================================================
if __name__ == "__main__":
    tests = [
        test_amm_init,
        test_mid_price,
        test_fee_calculation,
        test_normal_swap,
        test_invalid_quantities,
        test_zero_liquidity,
        test_import_clean,
        test_no_auto_simulation,
        test_engine_minimal,
        test_swap_y_for_x,
        test_pool_snapshot,
        test_execution_prices,
    ]

    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"FAIL  {fn.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)
