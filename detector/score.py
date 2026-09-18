"""Main Scoring Pipeline and Public API for CoNDA Detector.

Exposes the frozen top-level detector APIs:
    score_run(ticks: Iterable[dict]) -> Iterator[dict]
    score_window(ticks: list[dict]) -> dict

Observes streaming market behavior, partitions ticks into rolling windows,
evaluates pairwise behavioral signals against competitive counterfactuals,
aggregates risk scores, and generates verifiable evidence hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
import time
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from detector.aggregate import aggregate_signals
from detector.counterfactual import compute_window_counterfactual
from detector.explain import explain_gap, explain_sync
from detector.load import iter_ticks, load_ticks
from detector.signals.gap import compute_counterfactual_gap
from detector.signals.sync import compute_sync_under_shock
from detector.windows import Window, extract_agents, extract_run_id, slice_windows


def _sanitize_tick(raw_tick: Any) -> Optional[Dict[str, Any]]:
    """Ensure a tick is a valid dictionary without raising an exception."""
    if isinstance(raw_tick, dict):
        return raw_tick
    return None


def _calculate_evidence_hash(signals_block: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash over canonical JSON representation of signals.

    Canonical format: sorted keys and compact separators (",", ":").
    Prepended with '0x' matching project contract.
    """
    canonical_json = json.dumps(signals_block, sort_keys=True, separators=(",", ":"))
    return "0x" + hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _score_pair_in_window(
    window: Window,
    pair: Tuple[str, str],
    cf_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Score a specific agent pair within a given window.

    Evaluates:
    - counterfactual_gap
    - sync_under_shock
    - weighted aggregation and exact contribution sum
    - factual non-accusatory explanations
    - evidence hash
    - execution latency in milliseconds
    """
    start_time = time.perf_counter()

    agent_a, agent_b = sorted([str(pair[0]).strip(), str(pair[1]).strip()])
    sorted_pair = (agent_a, agent_b)

    # 1. Compute individual behavioral signals
    gap_res = compute_counterfactual_gap(window.ticks, sorted_pair)
    sync_res = compute_sync_under_shock(window.ticks, sorted_pair)

    # 2. Aggregate signals into total risk score
    signals_dict = {
        "counterfactual_gap": gap_res,
        "sync_under_shock": sync_res,
    }
    agg_res = aggregate_signals(signals_dict)

    # 3. Generate factual explanations
    gap_exp = explain_gap(gap_res)
    sync_exp = explain_sync(sync_res)

    # 4. Construct frozen signals block
    # Only implemented signals appear in the output
    signals_block = {
        "counterfactual_gap": {
            "value": round(gap_res.value, 4),
            "contribution": agg_res.contributions.get("counterfactual_gap", 0),
            "explanation": gap_exp,
        },
        "sync_under_shock": {
            "value": round(sync_res.value, 4),
            "contribution": agg_res.contributions.get("sync_under_shock", 0),
            "explanation": sync_exp,
        },
    }

    # 5. Reuse or compute window counterfactual summary
    if cf_summary is None:
        cf_summary = compute_window_counterfactual(window.ticks)

    # 6. Generate cryptographic evidence hash
    evidence_hash = _calculate_evidence_hash(signals_block)

    # 7. Compute elapsed time for this window evaluation
    computed_ms = round((time.perf_counter() - start_time) * 1000.0, 1)

    return {
        "run_id": window.run_id,
        "window_start": window.window_start,
        "window_end": window.window_end,
        "group": [agent_a, agent_b],
        "risk_score": agg_res.risk_score,
        "verdict": agg_res.verdict,
        "signals": signals_block,
        "counterfactual": cf_summary,
        "evidence_hash": evidence_hash,
        "computed_ms": computed_ms,
    }


def score_window(
    ticks: List[Dict[str, Any]],
    group: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Score an isolated window of market ticks.

    If group is specified (e.g. ['A1', 'A2']), scores that specific pair.
    If group is None:
        - If candidate pairs exist, scores all pairs and returns the primary assessment
          (highest risk_score, or first alphabetically if tied).
        - If no candidate pair exists (<2 agents), returns a safe LOW risk assessment.

    Args:
        ticks: Sequence of tick dictionaries in the window.
        group: Optional pair of agent IDs to evaluate.

    Returns:
        Dictionary adhering strictly to the frozen CoNDA output schema.
    """
    start_time = time.perf_counter()

    # Sanitize ticks
    valid_ticks: List[Dict[str, Any]] = []
    for t in ticks:
        s = _sanitize_tick(t)
        if s is not None:
            valid_ticks.append(s)

    run_id = extract_run_id(valid_ticks) if valid_ticks else "unknown_run"
    agents = extract_agents(valid_ticks) if valid_ticks else []

    def _safe_int_t(tick_item: Optional[Dict[str, Any]], default_val: int) -> int:
        if not tick_item or "t" not in tick_item:
            return default_val
        t_val = tick_item.get("t")
        try:
            f = float(t_val)
            import math
            if math.isnan(f) or math.isinf(f):
                return default_val
            return int(f)
        except (ValueError, TypeError):
            return default_val

    w_start = _safe_int_t(valid_ticks[0] if valid_ticks else None, 0)
    w_end = _safe_int_t(valid_ticks[-1] if valid_ticks else None, len(valid_ticks))

    window = Window(
        run_id=run_id,
        window_start=w_start,
        window_end=w_end,
        ticks=valid_ticks,
        agents=agents,
        start_idx=0,
        end_idx=max(0, len(valid_ticks) - 1),
    )

    cf_summary = compute_window_counterfactual(valid_ticks)

    # Case A: Specific group requested
    if group is not None and len(group) == 2:
        return _score_pair_in_window(window, (str(group[0]), str(group[1])), cf_summary)

    # Case B: Evaluate available candidate pairs
    if len(agents) >= 2:
        candidate_assessments: List[Dict[str, Any]] = []
        for pair in itertools.combinations(sorted(agents), 2):
            assessment = _score_pair_in_window(window, pair, cf_summary)
            candidate_assessments.append(assessment)

        # Select highest risk score; break ties deterministically by pair order
        candidate_assessments.sort(key=lambda a: (-a["risk_score"], a["group"]))
        return candidate_assessments[0]

    # Case C: Insufficient agents to form a pair (<2 agents or empty window)
    empty_signals: Dict[str, Any] = {}
    evidence_hash = _calculate_evidence_hash(empty_signals)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 1)

    return {
        "run_id": run_id,
        "window_start": w_start,
        "window_end": w_end,
        "group": list(agents),
        "risk_score": 0,
        "verdict": "LOW",
        "signals": empty_signals,
        "counterfactual": cf_summary,
        "evidence_hash": evidence_hash,
        "computed_ms": elapsed_ms,
    }


def score_run(
    ticks: Iterable[Dict[str, Any]],
    window_size: int = 100,
    stride: int = 25,
) -> Iterator[Dict[str, Any]]:
    """Stream-process a market run and yield assessments for all candidate pairs in rolling windows.

    Deterministic Ordering:
    - Windows yielded in chronological order.
    - Candidate pairs generated from alphabetically sorted agent IDs:
      e.g. (A1, A2), (A1, A3), (A2, A3).

    Args:
        ticks: An iterable of market tick dictionaries.
        window_size: Window length in ticks (default: 100).
        stride: Stride between window starts (default: 25).

    Yields:
        Assessment dictionaries adhering strictly to the frozen CoNDA output contract.
    """
    # Sanitize tick stream
    def _sanitized_generator() -> Iterator[Dict[str, Any]]:
        for raw in ticks:
            s = _sanitize_tick(raw)
            if s is not None:
                yield s

    # Partition into rolling windows using existing windows.py
    for window in slice_windows(_sanitized_generator(), window_size=window_size, stride=stride):
        agents = window.agents
        if len(agents) < 2:
            # Contract rule: No valid candidate pair means no pair assessment
            continue

        # Precompute window-level counterfactual once for all pairs in this window
        cf_summary = compute_window_counterfactual(window.ticks)

        # Enumerate every unique pair deterministically
        for pair in itertools.combinations(sorted(agents), 2):
            yield _score_pair_in_window(window, pair, cf_summary)


def _cli_main(args_list: Optional[List[str]] = None) -> int:
    """Command Line Interface for scoring JSONL runs."""
    parser = argparse.ArgumentParser(
        description="CoNDA Collusion Detector - Score market runs from JSONL files."
    )
    parser.add_argument("input_path", help="Path to market tick JSONL file.")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Format output as human-readable indented JSON (default: JSONL).",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=100,
        help="Window size in ticks (default: 100).",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=25,
        help="Window stride in ticks (default: 25).",
    )

    args = parser.parse_args(args_list)

    try:
        ticks = load_ticks(args.input_path)
    except Exception as exc:
        sys.stderr.write(f"Error loading input file '{args.input_path}': {exc}\n")
        return 1

    if not ticks:
        sys.stderr.write(f"No valid ticks found in '{args.input_path}'.\n")
        return 0

    count = 0
    for assessment in score_run(ticks, window_size=args.window_size, stride=args.stride):
        count += 1
        if args.pretty:
            print(json.dumps(assessment, indent=2))
        else:
            print(json.dumps(assessment))

    return 0


if __name__ == "__main__":
    sys.exit(_cli_main())
