"""
backend/sim_stub.py
-------------------
Development stub for Member 1's simulation interface.

Public interface (FROZEN):
    run_sim(scenario: str, seed: int) -> Iterator[dict]

This stub reads deterministic JSONL fixtures from backend/fixtures/ and
yields them as Python dicts, preserving the exact synchronous Iterator[dict]
contract that the real sim will honour.

DESIGN NOTE — sync delay:
    The specification asks for ~0.05 s between ticks. The public interface is a
    synchronous generator (Iterator[dict]), so asyncio.sleep() cannot be used
    here without breaking callers that are not running an event loop.
    We therefore use time.sleep(0.05) which provides the same ~50 ms pacing
    while keeping the generator fully synchronous. When the orchestrator layer
    (Step 2) wraps this in an async context it can run it in a thread executor
    (asyncio.to_thread / run_in_executor) if non-blocking I/O is required.

Swapping to the real simulation (Step 2+):
    Replace the import in orchestrator.py with:
        from simulation.sim import run_sim   # Member 1's real module
    No other changes needed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator

# Fixture directory lives next to this file's package root.
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Scenario → fixture filename mapping.
_SCENARIO_MAP: dict[str, str] = {
    "default": "default.jsonl",
}


def run_sim(scenario: str, seed: int) -> Iterator[dict]:
    """Yield deterministic MarketTick dicts from the requested scenario fixture.

    Parameters
    ----------
    scenario:
        Scenario name.  Currently only ``"default"`` is supported.
    seed:
        Random seed accepted for API compatibility with the real simulation.
        The deterministic fixture does not use it.

    Yields
    ------
    dict
        MarketTick record with keys: run_id, t, event, agent_id, side, price,
        quantity, capital, pnl, pool, oracle_price, shock.

    Raises
    ------
    ValueError
        If *scenario* is not a recognised scenario name.
    FileNotFoundError
        If the fixture file is missing from ``backend/fixtures/``.
    """
    if scenario not in _SCENARIO_MAP:
        raise ValueError(
            f"Unknown scenario {scenario!r}. "
            f"Valid scenarios: {sorted(_SCENARIO_MAP)}"
        )

    fixture_path = _FIXTURES_DIR / _SCENARIO_MAP[scenario]

    with fixture_path.open("r", encoding="utf-8-sig") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            tick: dict = json.loads(line)
            # ~50 ms pacing — synchronous; see module docstring for rationale.
            time.sleep(0.05)
            yield tick
