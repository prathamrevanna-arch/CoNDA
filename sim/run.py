"""
CLI runner for CoNDA market simulations.

Usage examples:
    python -m sim.run competitive --seed 42
    python -m sim.run --scenario cartel --seed 42 --output runs/cartel_seed42.jsonl
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import List, Optional

from sim.engine import ScenarioConfig, run_sim
from sim.logger import write_jsonl, write_run_meta


def build_meta_dict(cfg: ScenarioConfig, seed: int) -> dict:
    """Construct run_meta specification dictionary from config and seed."""
    run_id = f"r_{cfg.name}_{seed:02d}"
    return {
        "run_id": run_id,
        "scenario": cfg.name,
        "seed": seed,
        "ticks": cfg.ticks,
        "agents": [
            {"agent_id": a.agent_id, "agent_class": a.agent_class}
            for a in cfg.agents
        ],
        "shocks": [
            {"t": s.t, "type": s.type, "magnitude": s.magnitude}
            for s in cfg.shocks
        ],
    }


def run_cli(argv: Optional[List[str]] = None) -> int:
    """CLI execution entry point."""
    parser = argparse.ArgumentParser(
        prog="sim.run",
        description="Run a CoNDA market simulation scenario and write JSONL output.",
    )
    parser.add_argument(
        "scenario_pos",
        nargs="?",
        default=None,
        help="Scenario name (e.g., competitive, cartel, legit)",
    )
    parser.add_argument(
        "-s",
        "--scenario",
        dest="scenario_flag",
        default=None,
        help="Scenario name (alternative to positional argument)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Integer RNG seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output path for JSONL file (default: runs/<scenario>_seed<seed>.jsonl)",
    )
    parser.add_argument(
        "--meta-output",
        default=None,
        help="Optional path to write run_meta.json file",
    )

    args = parser.parse_args(argv)

    scenario = args.scenario_pos or args.scenario_flag
    if not scenario:
        sys.stderr.write("Error: scenario name is required.\n")
        parser.print_usage(sys.stderr)
        return 1

    try:
        cfg = ScenarioConfig.load(scenario)
    except FileNotFoundError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    output_path = args.output
    if not output_path:
        runs_dir = pathlib.Path("runs")
        output_path = str(runs_dir / f"{scenario}_seed{args.seed}.jsonl")

    try:
        # Run simulation stream and write to JSONL
        records = run_sim(scenario, args.seed)
        count = write_jsonl(records, output_path)

        # Optionally write run_meta JSON
        if args.meta_output:
            meta_dict = build_meta_dict(cfg, args.seed)
            write_run_meta(meta_dict, args.meta_output)

        print(f"Simulation completed: {count} records written to {output_path}")
        return 0
    except Exception as err:
        sys.stderr.write(f"Simulation failed: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_cli())
