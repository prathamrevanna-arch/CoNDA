"""
sim — CoNDA deterministic market simulator package.

Exposes the public API:
    run_sim(scenario, seed) -> Iterator[dict]

No side effects on import: no simulation, no file I/O, no stdout.
"""

from sim.engine import run_sim

__all__ = ["run_sim"]
