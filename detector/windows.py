"""Tick-based Rolling Window Slicer for CoNDA Detector.

Slices sequential market tick streams into overlapping windows of fixed tick count.
Windows are based on tick records, NOT time elapsed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional


@dataclass
class Window:
    """A sliding window of consecutive market tick records."""
    run_id: str
    window_start: int
    window_end: int
    ticks: List[Dict[str, Any]]
    agents: List[str]
    start_idx: int
    end_idx: int

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
    """Slice a stream of ticks into overlapping simulation-t based windows.

    Rules:
    - Default window size is 100 unique simulation t values.
    - Default stride is 25 unique simulation t values (e.g. 0-99, 25-124, 50-149, ...).
    - Preserves ALL records sharing the same simulation t.
    - If total unique t < window_size but > 0, yields a single window of available ticks.
    - If total ticks == 0, yields nothing safely without crashing.
    - window_start and window_end use tick timestamp 't' if present, otherwise tick index.

    Args:
        ticks: An iterable of market tick dictionaries.
        window_size: Number of unique simulation t values per window (default: 100).
        stride: Step size between consecutive window starts (default: 25).

    Yields:
        Window objects containing the slice metadata and tick records.
    """
    if window_size <= 0 or stride <= 0:
        raise ValueError("window_size and stride must be positive integers.")

    tick_list: List[Dict[str, Any]] = list(ticks) if not isinstance(ticks, list) else ticks
    total_ticks = len(tick_list)

    if total_ticks == 0:
        return

    # Group records by unique simulation t, preserving chronological order
    t_groups: Dict[int, List[Dict[str, Any]]] = {}
    for idx, tick in enumerate(tick_list):
        t_val = int(float(tick.get("t", idx))) if "t" in tick and tick.get("t") is not None else idx
        if t_val not in t_groups:
            t_groups[t_val] = []
        t_groups[t_val].append(tick)

    unique_ts = sorted(t_groups.keys())
    total_unique = len(unique_ts)

    # Fallback for short runs: produce one window with all available ticks
    if total_unique < window_size:
        first_tick = tick_list[0]
        last_tick = tick_list[-1]
        w_start = int(first_tick.get("t", 0)) if "t" in first_tick else 0
        w_end = int(last_tick.get("t", total_ticks - 1)) if "t" in last_tick else total_ticks - 1
        yield Window(
            run_id=extract_run_id(tick_list),
            window_start=w_start,
            window_end=w_end,
            ticks=tick_list,
            agents=extract_agents(tick_list),
            start_idx=0,
            end_idx=total_ticks - 1,
        )
        return

    # Standard rolling window slicing over unique simulation t values
    for start_idx in range(0, total_unique, stride):
        end_idx = min(start_idx + window_size, total_unique)
        window_ts = unique_ts[start_idx:end_idx]

        if not window_ts:
            break

        slice_ticks: List[Dict[str, Any]] = []
        for t_val in window_ts:
            slice_ticks.extend(t_groups[t_val])

        w_start = window_ts[0]
        w_end = window_ts[-1]

        yield Window(
            run_id=extract_run_id(slice_ticks),
            window_start=w_start,
            window_end=w_end,
            ticks=slice_ticks,
            agents=extract_agents(slice_ticks),
            start_idx=start_idx,
            end_idx=end_idx - 1,
        )

        # If we have reached or exceeded the end of ticks, don't generate duplicate tail windows
        if end_idx >= total_unique:
            break
