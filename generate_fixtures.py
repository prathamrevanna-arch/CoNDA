"""Deterministic fixture generator for CoNDA detector evaluation."""

import json
from pathlib import Path


def generate_competitive(path: Path):
    ticks = []
    agents = ["A1", "A2", "A3", "A4"]
    # Ticks 0 to 49: competitive quoting around 100.3 (ref is 100.3)
    for i in range(50):
        ag = agents[i % 4]
        price_offset = (i % 3 - 1) * 0.05  # -0.05, 0.0, +0.05
        ticks.append({
            "run_id": "r_competitive_01",
            "t": 100 + i,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": round(100.30 + price_offset, 2),
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 100.0 + i * 2.5,
            "pool": {
                "reserve_x": 10000.0,
                "reserve_y": 1000000.0,
                "fee_bps": 30,
            },
            "oracle_price": 100.0,
            "shock": None,
        })

    # Tick 50: Public Shock
    ticks.append({
        "run_id": "r_competitive_01",
        "t": 150,
        "event": "shock",
        "shock": {"type": "oracle_jump", "magnitude": -0.05},
    })

    # Ticks 51 to 109: Staggered reaction times post shock
    # A1 reacts at t=154 (delay 4)
    # A2 reacts at t=161 (delay 11)
    # A3 reacts at t=158 (delay 8)
    # A4 reacts at t=167 (delay 17)
    reaction_times = {"A1": 154, "A3": 158, "A2": 161, "A4": 167}

    for i in range(51, 110):
        t = 100 + i
        ag = agents[i % 4]
        # If before agent's reaction time, quote at old price; once reacted, quote at new price (~95.3)
        if t >= reaction_times[ag]:
            price = round(95.28 + (i % 3 - 1) * 0.05, 2)
        else:
            price = 100.30

        ticks.append({
            "run_id": "r_competitive_01",
            "t": t,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": price,
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 220.0 + i * 1.5,
            "pool": {
                "reserve_x": 10000.0,
                "reserve_y": 950000.0,
                "fee_bps": 30,
            },
            "oracle_price": 95.0,
            "shock": None,
        })

    path.write_text("\n".join(json.dumps(t) for t in ticks) + "\n", encoding="utf-8")


def generate_cartel(path: Path):
    """Primary cartel fixture: A2/A3 quote ~5% above competitive reference.

    Design rationale:
    - A 5% persistent gap is realistic for tacit collusion (literature: 3-15%).
    - The gap signal normalises by GAP_REFERENCE_SCALE=0.05 in gap.py, so 5% => value=1.0.
    - A2/A3 react within 1 tick of each other after the shock; other pairs have 10-20 tick gaps.
    - Combined (gap=1.0, sync~0.81) => risk_score ~92, verdict HIGH.
    - A1/A4 quote at or near the competitive reference and are therefore LOW risk.
    """
    ticks = []
    agents = ["A1", "A2", "A3", "A4"]
    # Coordinated pair: A2 and A3
    # Independent agents: A1 and A4
    #
    # Reference ask price pre-shock: pool_y/pool_x blended with oracle, then +fee.
    # With reserve_x=10000, reserve_y=1000000, oracle=100.0, fee=30bps:
    #   P_pool = 100.0, L = sqrt(10000*1000000) = 100000
    #   w_pool = 100000/(100000+50000) = 0.667, P_mid = 100.0, P_ask = 100.30
    # 5% above reference ask: 100.30 * 1.05 = 105.315
    pre_shock_prices = {
        "A1": 100.30,   # competitive: at reference
        "A2": 105.31,   # cartel:  ~5.00% above reference ask of 100.30
        "A3": 105.41,   # cartel:  ~5.09% above reference ask of 100.30
        "A4": 100.30,   # competitive: at reference
    }

    # Reference ask post-shock:
    # reserve_y=950000, oracle=95.0 => P_ask ~= 95.285
    # 5% above: 95.285 * 1.05 ~= 100.05
    post_reaction_prices = {
        "A2": 100.05,   # cartel:  ~5.00% above reference ask of 95.285
        "A3": 100.15,   # cartel:  ~5.11% above reference ask of 95.285
        "A1": 95.30,    # competitive: at reference
        "A4": 95.30,    # competitive: at reference
    }

    # Ticks 0 to 49: pre-shock quoting
    for i in range(50):
        ag = agents[i % 4]
        price = pre_shock_prices[ag]

        ticks.append({
            "run_id": "r_cartel_01",
            "t": 100 + i,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": price,
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 100.0 + i * 3.0 if ag in ("A2", "A3") else 50.0,
            "pool": {
                "reserve_x": 10000.0,
                "reserve_y": 1000000.0,
                "fee_bps": 30,
            },
            "oracle_price": 100.0,
            "shock": None,
        })

    # Tick 50: Public Shock
    ticks.append({
        "run_id": "r_cartel_01",
        "t": 150,
        "event": "shock",
        "shock": {"type": "oracle_jump", "magnitude": -0.05},
    })

    # Ticks 51-109: Cartel reacts synchronously (t=152, t=153, i.e. 2-3 tick delays)
    # Independent agents react late and dispersed (A1 at t=170, A4 at t=176)
    # => pair (A2,A3): D_pair = 1 tick; baseline (other pairs): ~18 tick median
    # => sync_value = (18-1)/(18+3) = 0.81
    reaction_times = {"A2": 152, "A3": 153, "A1": 170, "A4": 176}

    key_agent_seq = {151: "A1", 152: "A2", 153: "A3", 154: "A4", 170: "A1", 176: "A4"}

    for i in range(51, 110):
        t = 100 + i
        ag = key_agent_seq.get(t, agents[i % 4])
        if t >= reaction_times[ag]:
            price = post_reaction_prices[ag]
        else:
            price = pre_shock_prices[ag]

        ticks.append({
            "run_id": "r_cartel_01",
            "t": t,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": price,
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 200.0 + i * 4.0 if ag in ("A2", "A3") else 80.0,
            "pool": {
                "reserve_x": 10000.0,
                "reserve_y": 950000.0,
                "fee_bps": 30,
            },
            "oracle_price": 95.0,
            "shock": None,
        })

    path.write_text("\n".join(json.dumps(t) for t in ticks) + "\n", encoding="utf-8")


def generate_cartel_extreme(path: Path):
    """Extreme cartel fixture: A2/A3 quote ~78% above competitive reference.

    Purpose: sanity-check / easy-case fixture that any reasonable detector should catch.
    This preserves the original pre-normalisation fixture prices for regression testing.
    DO NOT use this as the primary demo fixture — the 78% gap is unrealistically large.
    Realistic tacit-collusion gaps are 3-15%; see run_cartel.jsonl for that scenario.
    """
    ticks = []
    agents = ["A1", "A2", "A3", "A4"]

    pre_shock_prices = {
        "A1": 100.30,
        "A2": 178.50,   # ~78% above reference — extreme / sanity-check case
        "A3": 178.60,   # ~78% above reference
        "A4": 100.30,
    }
    post_reaction_prices = {
        "A2": 169.10,   # ~77.5% above post-shock reference of ~95.285
        "A3": 169.20,   # ~77.6% above post-shock reference
        "A1": 95.30,
        "A4": 95.30,
    }

    for i in range(50):
        ag = agents[i % 4]
        ticks.append({
            "run_id": "r_cartel_extreme_01",
            "t": 100 + i,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": pre_shock_prices[ag],
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 500.0 + i * 10.0 if ag in ("A2", "A3") else 50.0,
            "pool": {"reserve_x": 10000.0, "reserve_y": 1000000.0, "fee_bps": 30},
            "oracle_price": 100.0,
            "shock": None,
        })

    ticks.append({
        "run_id": "r_cartel_extreme_01",
        "t": 150,
        "event": "shock",
        "shock": {"type": "oracle_jump", "magnitude": -0.05},
    })

    reaction_times = {"A2": 152, "A3": 153, "A1": 170, "A4": 176}
    key_agent_seq = {151: "A1", 152: "A2", 153: "A3", 154: "A4", 170: "A1", 176: "A4"}

    for i in range(51, 110):
        t = 100 + i
        ag = key_agent_seq.get(t, agents[i % 4])
        price = post_reaction_prices[ag] if t >= reaction_times[ag] else pre_shock_prices[ag]
        ticks.append({
            "run_id": "r_cartel_extreme_01",
            "t": t,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": price,
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 1000.0 + i * 8.0 if ag in ("A2", "A3") else 80.0,
            "pool": {"reserve_x": 10000.0, "reserve_y": 950000.0, "fee_bps": 30},
            "oracle_price": 95.0,
            "shock": None,
        })

    path.write_text("\n".join(json.dumps(t) for t in ticks) + "\n", encoding="utf-8")



def generate_legitimate_coordination(path: Path):
    ticks = []
    agents = ["A1", "A2", "A3", "A4"]

    # Ticks 0 to 49: All agents quote competitively
    for i in range(50):
        ag = agents[i % 4]
        price = round(100.30 + (i % 3 - 1) * 0.04, 2)
        ticks.append({
            "run_id": "r_legit_01",
            "t": 100 + i,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": price,
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 100.0 + i * 2.0,
            "pool": {
                "reserve_x": 10000.0,
                "reserve_y": 1000000.0,
                "fee_bps": 30,
            },
            "oracle_price": 100.0,
            "shock": None,
        })

    # Tick 50: Public Shock
    ticks.append({
        "run_id": "r_legit_01",
        "t": 150,
        "event": "shock",
        "shock": {"type": "oracle_jump", "magnitude": -0.05},
    })

    # Ticks 51 to 109: Every agent in the market reacts almost immediately (within 1-2 ticks)
    # A1 at 152, A2 at 152, A3 at 153, A4 at 153
    reaction_times = {"A1": 152, "A2": 152, "A3": 153, "A4": 153}

    for i in range(51, 110):
        t = 100 + i
        ag = agents[i % 4]
        if t >= reaction_times[ag]:
            price = round(95.28 + (i % 3 - 1) * 0.04, 2)
        else:
            price = 100.30

        ticks.append({
            "run_id": "r_legit_01",
            "t": t,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": price,
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 200.0 + i * 1.8,
            "pool": {
                "reserve_x": 10000.0,
                "reserve_y": 950000.0,
                "fee_bps": 30,
            },
            "oracle_price": 95.0,
            "shock": None,
        })

    path.write_text("\n".join(json.dumps(t) for t in ticks) + "\n", encoding="utf-8")


if __name__ == "__main__":
    fixtures_dir = Path("fixtures")
    fixtures_dir.mkdir(exist_ok=True)
    generate_competitive(fixtures_dir / "run_competitive.jsonl")
    generate_cartel(fixtures_dir / "run_cartel.jsonl")
    generate_cartel_extreme(fixtures_dir / "run_cartel_extreme.jsonl")
    generate_legitimate_coordination(fixtures_dir / "run_legitimate_coordination.jsonl")
    print("Fixtures generated successfully.")

