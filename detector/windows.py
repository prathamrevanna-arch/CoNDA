"""Simulation-t-based Rolling Window Slicer for CoNDA Detector.

Slices sequential market tick streams into overlapping windows defined by
UNIQUE SIMULATION t VALUES, not raw tick record counts.

Each simulation timestep t may produce multiple MarketTick records
(e.g. one quote per agent + a trade). All records sharing the same t are
always kept together; no tick is ever split across a window boundary.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List


@dataclass
class Window:
    """A sliding window of market tick records spanning a range of simulation t values."""
    run_id: str
    window_start: int
    window_end: int
    ticks: List[Dict[str, Any]]
    agents: List[str]
    start_idx: int   # index into the unique-t list (first t in window)
    end_idx: int     # index into the unique-t list (last  t in window)

    def to_dict(self) -> Dict[str, Any]:
        """Convert window metadata to a dictionary representation."""
        return {
            "run_id": self.run_id,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "ticks": self.ticks,
            "agents": self.agents,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
        }


def extract_agents(ticks: Iterable[Dict[str, Any]]) -> List[str]:
    """Extract a sorted, unique list of agent IDs present in the given ticks."""
    agents = set()
    for tick in ticks:
        agent_id = tick.get("agent_id")
        if agent_id is not None and str(agent_id).strip():
            agents.add(str(agent_id).strip())
    return sorted(agents)


def extract_run_id(ticks: Iterable[Dict[str, Any]], fallback: str = "unknown_run") -> str:
    """Extract the run_id from the first tick that contains one."""
    for tick in ticks:
        run_id = tick.get("run_id")
        if run_id:
            return str(run_id)
    return fallback


def slice_windows(
    ticks: Iterable[Dict[str, Any]],
    window_size: int = 100,
    stride: int = 25,
) -> Iterator[Window]:
    """Slice a tick stream into overlapping windows defined by unique simulation t values.

    Semantics (IMPORTANT):
    - window_size = number of UNIQUE simulation t values per window (default: 100).
    - stride      = number of unique t values to advance per step     (default: 25).
    - ALL MarketTick records that share the same simulation t are
      included together — no record is ever split across a boundary.
    - window_start = first  simulation t selected in the window.
    - window_end   = last   simulation t selected in the window.

    Expected window count:
      For N unique t values, window_size W, stride S:
        windows = ceil((N - W) / S) + 1   if N >= W
        windows = 1                         if 0 < N < W  (short-run fallback)
        windows = 0                         if N == 0

    Example — 400 unique t values (0..399), W=100, S=25:
      starts at t-indices 0, 25, 50, ..., 300  -> 13 windows.

    Args:
        ticks: An iterable of market tick dictionaries (may contain multiple
               records per simulation t).
        window_size: Unique simulation t values per window (default: 100).
        stride: Unique simulation t values to advance between windows (default: 25).

    Yields:
        Window objects containing slice metadata and all tick records for the
        selected simulation t range.
    """
    if window_size <= 0 or stride <= 0:
        raise ValueError("window_size and stride must be positive integers.")

    # Materialise stream (needed for random-access grouping)
    tick_list: List[Dict[str, Any]] = list(ticks) if not isinstance(ticks, list) else ticks

    if not tick_list:
        return

    # Group ticks by their simulation t, preserving stream order within each group.
    t_groups: "OrderedDict[int, List[Dict[str, Any]]]" = OrderedDict()
    for tick in tick_list:
        raw_t = tick.get("t")
        try:
            t_val = int(float(raw_t))       # handles numpy float64, int, str
        except (TypeError, ValueError):
            t_val = 0
        if t_val not in t_groups:
            t_groups[t_val] = []
        t_groups[t_val].append(tick)

    unique_ts: List[int] = list(t_groups.keys())
    total_unique = len(unique_ts)
    run_id = extract_run_id(tick_list)

    # Short-run fallback: fewer unique t values than window_size
    if total_unique < window_size:
        yield Window(
            run_id=run_id,
            window_start=unique_ts[0],
            window_end=unique_ts[-1],
            ticks=tick_list,
            agents=extract_agents(tick_list),
            start_idx=0,
            end_idx=total_unique - 1,
        )
        return

    # Standard rolling window over the ordered unique-t list
    t_start_pos = 0
    while t_start_pos < total_unique:
        t_end_pos = min(t_start_pos + window_size, total_unique)
        window_ts = unique_ts[t_start_pos:t_end_pos]

        # Flatten all tick records for the selected t range (original order preserved)
        window_ticks: List[Dict[str, Any]] = []
        for t_val in window_ts:
            window_ticks.extend(t_groups[t_val])

        yield Window(
            run_id=run_id,
            window_start=window_ts[0],
            window_end=window_ts[-1],
            ticks=window_ticks,
            agents=extract_agents(window_ticks),
            start_idx=t_start_pos,
            end_idx=t_end_pos - 1,
        )

        # If we have reached or exceeded the end of unique t values, do not generate tail windows
        if t_end_pos >= total_unique:
            break

        t_start_pos += stride
