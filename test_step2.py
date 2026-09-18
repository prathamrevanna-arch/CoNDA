"""
Comprehensive tests for Member 1 Step 2 integration:
- Agent registration
- Scenarios execution (competitive, cartel, legit)
- Schema conformity & determinism
- Cartel vs Competitive price assertion
- Legitimate scenario behavior
- Edge cases & Oracle timing
"""

import json
import math
import sys
import numpy as np

from sim import run_sim
from sim.amm import ConstantProductAMM, InvalidReservesError, ZeroLiquidityError, InvalidTradeError
from sim.engine import SCENARIO_DIR, ScenarioConfig, register_agent


def test_registration_and_execution():
    print("Testing registration and scenario execution...")
    for scenario_name in ["competitive", "cartel", "legit"]:
        records = list(run_sim(scenario_name, seed=42))
        assert len(records) > 0, f"No records returned for {scenario_name}"
        assert records[0]["event"] == "meta", f"First record must be meta for {scenario_name}"
        assert records[0]["t"] == 0
        assert records[0]["oracle_price"] == 100.0

        # Check tick termination
        cfg = ScenarioConfig.load(scenario_name)
        max_t = max(r["t"] for r in records)
        assert max_t == cfg.ticks - 1, f"Expected max_t {cfg.ticks - 1}, got {max_t}"
        
        # Check record fields
        required_keys = {"run_id", "t", "event", "agent_id", "side", "price", "quantity", "capital", "pnl", "pool", "oracle_price", "shock"}
        for r in records:
            assert required_keys.issubset(r.keys()), f"Missing keys in record: {r}"
            assert set(r["pool"].keys()) == {"reserve_x", "reserve_y", "fee_bps"}
        
        print(f"  PASS: {scenario_name} yielded {len(records)} records across {cfg.ticks} ticks")


def test_determinism():
    print("Testing determinism...")
    for scenario_name in ["competitive", "cartel", "legit"]:
        run1 = list(run_sim(scenario_name, seed=12345))
        run2 = list(run_sim(scenario_name, seed=12345))
        run_diff_seed = list(run_sim(scenario_name, seed=99999))

        # Check identical serialization
        json1 = json.dumps(run1, sort_keys=True)
        json2 = json.dumps(run2, sort_keys=True)
        assert json1 == json2, f"Determinism failure for {scenario_name} with same seed"
        assert len(run1) == len(run2)

        # Check different seed produces different output
        json_diff = json.dumps(run_diff_seed, sort_keys=True)
        assert json1 != json_diff, f"Seed change did not change output for {scenario_name}"
        print(f"  PASS: {scenario_name} is perfectly deterministic and seed-sensitive")


def test_price_assertion():
    print("Testing cartel vs competitive price assertion...")
    seed = 42
    records_comp = list(run_sim("competitive", seed=seed))
    records_cartel = list(run_sim("cartel", seed=seed))

    # Calculate mid-price at each tick for pool (reserve_y / reserve_x)
    # Filter tick records (exclude meta and shock if pool mid-price is tracked per tick)
    mid_prices_comp = [r["pool"]["reserve_y"] / r["pool"]["reserve_x"] for r in records_comp if r["event"] not in ("meta", "shock")]
    mid_prices_cartel = [r["pool"]["reserve_y"] / r["pool"]["reserve_x"] for r in records_cartel if r["event"] not in ("meta", "shock")]

    mean_comp = float(np.mean(mid_prices_comp))
    mean_cartel = float(np.mean(mid_prices_cartel))

    print(f"  Competitive mean mid-price: {mean_comp:.6f}")
    print(f"  Cartel mean mid-price:      {mean_cartel:.6f}")
    print(f"  Difference (Cartel - Comp): {mean_cartel - mean_comp:.6f}")

    assert mean_cartel > mean_comp, f"Cartel mean mid-price ({mean_cartel}) must be higher than competitive ({mean_comp})"
    print("  PASS: Cartel scenario produces a measurably higher mean mid-price than competitive")
    return mean_comp, mean_cartel


def test_legitimate_control():
    print("Testing legitimate scenario behavior...")
    seed = 42
    records_legit = list(run_sim("legit", seed=seed))
    records_comp = list(run_sim("competitive", seed=seed))
    records_cartel = list(run_sim("cartel", seed=seed))

    mid_prices_legit = [r["pool"]["reserve_y"] / r["pool"]["reserve_x"] for r in records_legit if r["event"] not in ("meta", "shock")]
    mid_prices_comp = [r["pool"]["reserve_y"] / r["pool"]["reserve_x"] for r in records_comp if r["event"] not in ("meta", "shock")]
    mid_prices_cartel = [r["pool"]["reserve_y"] / r["pool"]["reserve_x"] for r in records_cartel if r["event"] not in ("meta", "shock")]

    oracle_prices_legit = [r["oracle_price"] for r in records_legit if r["event"] not in ("meta", "shock")]

    # Deviation of mid-price from oracle price
    dev_legit = np.mean([abs(m - o) / o for m, o in zip(mid_prices_legit, oracle_prices_legit)])
    mean_legit = float(np.mean(mid_prices_legit))
    mean_comp = float(np.mean(mid_prices_comp))
    mean_cartel = float(np.mean(mid_prices_cartel))

    print(f"  Legitimate mean mid-price: {mean_legit:.6f}")
    print(f"  Legit mean absolute relative deviation from oracle: {dev_legit:.6f}")
    print(f"  Cartel mean mid-price elevation above oracle: {mean_cartel - np.mean(oracle_prices_legit):.6f}")

    # Legit agent should track oracle closely without sustained artificial markup
    assert dev_legit < 0.05, f"Legit agents should track oracle closely, got avg dev {dev_legit}"
    print("  PASS: Legitimate control does not exhibit sustained price manipulation")


def test_oracle_timing():
    print("Testing oracle timing at tick 0...")
    # At t=0, with oracle_start=100.0, the first agent action at t=0 must see oracle_price == 100.0 exactly
    records = list(run_sim("competitive", seed=42))
    t0_records = [r for r in records if r["t"] == 0]
    for r in t0_records:
        assert r["oracle_price"] == 100.0, f"Expected oracle_price 100.0 at t=0, got {r['oracle_price']}"
    print("  PASS: Tick 0 correctly starts at configured oracle_start")


def test_edge_cases():
    print("Testing edge cases...")
    # 1. Invalid initial reserves
    try:
        ConstantProductAMM(reserve_x=0.0, reserve_y=100.0)
        assert False, "Should reject zero reserve_x"
    except InvalidReservesError:
        pass

    try:
        ConstantProductAMM(reserve_x=-10.0, reserve_y=100.0)
        assert False, "Should reject negative reserve_x"
    except InvalidReservesError:
        pass

    # 2. Single agent scenario
    scenario_name = "__test_single_agent"
    path = SCENARIO_DIR / f"{scenario_name}.json"
    data = {
        "name": scenario_name,
        "ticks": 10,
        "fee_bps": 30,
        "initial_reserve_x": 1000.0,
        "initial_reserve_y": 100000.0,
        "oracle_start": 100.0,
        "oracle_mu": 0.0,
        "oracle_sigma": 0.001,
        "agents": [
            {
                "agent_id": "solo_1",
                "agent_class": "competitive",
                "params": {"trade_threshold": 0.002, "base_qty_y": 150.0}
            }
        ],
        "shocks": []
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    records = list(run_sim(scenario_name, seed=42))
    path.unlink(missing_ok=True)
    assert len(records) == 1 + 10  # 1 meta + 10 tick records
    print("  PASS: Single agent scenario works correctly")

    # 3. Shock at tick 0
    scenario_name = "__test_shock_t0"
    path = SCENARIO_DIR / f"{scenario_name}.json"
    data = {
        "name": scenario_name,
        "ticks": 10,
        "fee_bps": 30,
        "initial_reserve_x": 1000.0,
        "initial_reserve_y": 100000.0,
        "oracle_start": 100.0,
        "oracle_mu": 0.0,
        "oracle_sigma": 0.0,
        "agents": [
            {
                "agent_id": "agent_1",
                "agent_class": "competitive",
                "params": {}
            }
        ],
        "shocks": [
            {"t": 0, "type": "oracle_jump", "magnitude": 0.10}
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    records = list(run_sim(scenario_name, seed=42))
    path.unlink(missing_ok=True)
    # Check shock record at t=0
    shock_rec = next(r for r in records if r["event"] == "shock" and r["t"] == 0)
    assert shock_rec["oracle_price"] == 110.0, f"Expected shocked price 110.0 at t=0, got {shock_rec['oracle_price']}"
    t0_agent_rec = next(r for r in records if r["event"] != "meta" and r["event"] != "shock" and r["t"] == 0)
    assert t0_agent_rec["oracle_price"] == 110.0
    print("  PASS: Shock at tick 0 executes and updates oracle before agent actions")

    # 4. Shock at last tick
    scenario_name = "__test_shock_last"
    path = SCENARIO_DIR / f"{scenario_name}.json"
    data = {
        "name": scenario_name,
        "ticks": 5,
        "fee_bps": 30,
        "initial_reserve_x": 1000.0,
        "initial_reserve_y": 100000.0,
        "oracle_start": 100.0,
        "oracle_mu": 0.0,
        "oracle_sigma": 0.0,
        "agents": [
            {"agent_id": "agent_1", "agent_class": "competitive", "params": {}}
        ],
        "shocks": [
            {"t": 4, "type": "oracle_jump", "magnitude": -0.20}
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    records = list(run_sim(scenario_name, seed=42))
    path.unlink(missing_ok=True)
    shock_rec = next(r for r in records if r["event"] == "shock" and r["t"] == 4)
    assert shock_rec["oracle_price"] == 80.0
    print("  PASS: Shock at last tick works correctly")


if __name__ == "__main__":
    test_registration_and_execution()
    test_determinism()
    test_oracle_timing()
    comp_mean, cartel_mean = test_price_assertion()
    test_legitimate_control()
    test_edge_cases()
    print("\nALL STEP 2 TESTS PASSED SUCCESSFULLY!")
