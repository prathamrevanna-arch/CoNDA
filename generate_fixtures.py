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
    ticks = []
    agents = ["A1", "A2", "A3", "A4"]
    # Coordinated pair: A2 and A3
    # Independent agents: A1 and A4

    # Ticks 0 to 49
    for i in range(50):
        ag = agents[i % 4]
        if ag in ("A2", "A3"):
            # Supracompetitive cartel markup (~78% premium over 100.3 ref)
            price = 178.50 if ag == "A2" else 178.60
        else:
            # Competitive pricing
            price = round(100.30 + (i % 3 - 1) * 0.05, 2)

        ticks.append({
            "run_id": "r_cartel_01",
            "t": 100 + i,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": price,
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 500.0 + i * 10.0 if ag in ("A2", "A3") else 50.0,
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

    # Ticks 51 to 109: Cartel reacts synchronously (t=152, t=153)
    # Independent agents react late and dispersed (t=170, t=176)
    reaction_times = {"A2": 152, "A3": 153, "A1": 170, "A4": 176}

    for i in range(51, 110):
        t = 100 + i
        ag = agents[i % 4]
        if ag in ("A2", "A3"):
            if t >= reaction_times[ag]:
                # Cartel updates quote synchronously to maintain markup at new lower market (~169.0 vs 95.3 ref)
                price = 169.10 if ag == "A2" else 169.20
            else:
                price = 178.50
        else:
            if t >= reaction_times[ag]:
                price = round(95.28 + (i % 3 - 1) * 0.05, 2)
            else:
                price = 100.30

        ticks.append({
            "run_id": "r_cartel_01",
            "t": t,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": price,
            "quantity": 5.0,
            "capital": 50000.0,
            "pnl": 1000.0 + i * 8.0 if ag in ("A2", "A3") else 80.0,
            "pool": {
                "reserve_x": 10000.0,
                "reserve_y": 950000.0,
                "fee_bps": 30,
            },
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
    generate_legitimate_coordination(fixtures_dir / "run_legitimate_coordination.jsonl")
    print("Fixtures generated successfully.")
