"""Sync Under Shock Signal for CoNDA.

Measures whether a specific agent pair re-quotes after a public market shock
with unusually tight timing concordance relative to the all-pairs baseline.

Key Principles:
1. Public Shocks Are Common Knowledge: When a public shock hits, everyone reacting
   quickly is standard competitive behavior.
2. All-Pairs Baseline: We compare the target pair's timing difference against
   the distribution of pairwise timing differences among all other reacting agent pairs.
3. False-Positive Suppression: If all market agents react simultaneously, the pair
   is NOT flagged as unusually synchronized.
4. Ground-Truth Agnostic: Operates purely on observable tick event data without
   referencing agent classes or scenario metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
import itertools
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from detector.counterfactual import is_valid_number

# Characteristic scale in ticks used to prevent tiny differences (e.g., 0 vs 1 tick)
# in an already tight market from producing artificially inflated scores.
JITTER_SCALE_TICKS = 3.0

# Minimum number of reacting agents required to form a non-circular all-pairs baseline (>= 3 agents)
MIN_REACTING_AGENTS_FOR_BASELINE = 3

# Tolerance for detecting price changes after a shock (0.01% price difference)
PRICE_CHANGE_REL_TOLERANCE = 1e-4


@dataclass
class SyncSignalResult:
    """Structured result of the sync under shock evaluation."""
    value: float                  # Normalized score strictly bounded in [0.0, 1.0]
    pair_delay_diff: float        # Absolute reaction delay difference for target pair (|delay_A - delay_B|)
    baseline_delay_diff: float    # Median reaction delay difference among other eligible pairs
    shocks_evaluated: int         # Count of shocks where target pair had valid reactions
    shocks_present: int           # Total shocks detected in current window
    reacting_agents_count: int    # Number of agents that reacted to the shock
    agent_a_delay: float          # Reaction delay (ticks) for agent A
    agent_b_delay: float          # Reaction delay (ticks) for agent B
    has_sufficient_baseline: bool # True if >= 3 agents reacted allowing a non-circular baseline

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for explainability and evidence logging."""
        return {
            "value": round(self.value, 4),
            "pair_delay_diff": round(self.pair_delay_diff, 1),
            "baseline_delay_diff": round(self.baseline_delay_diff, 1),
            "shocks_evaluated": self.shocks_evaluated,
            "shocks_present": self.shocks_present,
            "reacting_agents_count": self.reacting_agents_count,
            "agent_a_delay": round(self.agent_a_delay, 1),
            "agent_b_delay": round(self.agent_b_delay, 1),
            "has_sufficient_baseline": self.has_sufficient_baseline,
        }


def _empty_sync_result(shocks_present: int = 0) -> SyncSignalResult:
    """Return a neutral zero-valued result for insufficient evidence."""
    return SyncSignalResult(
        value=0.0,
        pair_delay_diff=0.0,
        baseline_delay_diff=0.0,
        shocks_evaluated=0,
        shocks_present=shocks_present,
        reacting_agents_count=0,
        agent_a_delay=0.0,
        agent_b_delay=0.0,
        has_sufficient_baseline=False,
    )


def _median(values: Sequence[float]) -> float:
    """Deterministic median computation."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def _is_shock_tick(tick: Dict[str, Any]) -> bool:
    """Determine if a tick represents a public market shock event."""
    if not isinstance(tick, dict):
        return False
    if tick.get("event") == "shock":
        return True
    shock_data = tick.get("shock")
    return shock_data is not None and isinstance(shock_data, dict)


def _get_tick_time(tick: Dict[str, Any], fallback_idx: int) -> float:
    """Extract tick timestamp 't' or fallback to tick sequential index."""
    t_val = tick.get("t")
    if is_valid_number(t_val):
        return float(t_val)
    return float(fallback_idx)


def compute_sync_under_shock(
    ticks: List[Dict[str, Any]],
    pair: Tuple[str, str],
    jitter_scale: float = JITTER_SCALE_TICKS,
) -> SyncSignalResult:
    """Compute timing synchrony of an agent pair following market shocks relative to baseline.

    Algorithm:
    1. Scan window for public shock events. If none exist, return neutral 0.0.
    2. For each shock:
       a. Identify last quote price of each agent prior to the shock.
       b. Find the first meaningful post-shock re-quote for each agent (price changed or
          new quote).
       c. Compute reaction delay for each agent: delay = t_requote - t_shock.
       d. Compute pairwise reaction delay differences for all reacting agent pairs.
       e. Isolate target pair difference D_pair = |delay_A - delay_B|.
       f. Compute baseline D_baseline as median of all other pairwise differences.
       g. Evaluate synchrony score:
          score = max(0.0, D_baseline - D_pair) / (D_baseline + jitter_scale)
          - If everyone reacted synchronously, D_baseline is low, keeping score low.
          - If target pair reacted with tight concordance while others had dispersed
            reactions (high D_baseline), score increases up to 1.0.
    3. Aggregate multiple shocks using median to prevent one extreme event from dominating.

    Args:
        ticks: Sequence of tick records in the sliding window.
        pair: Tuple of two agent ID strings, e.g. ("A1", "A2").
        jitter_scale: Constant damping scale in ticks to prevent small random jitters
                      from inflating scores (default: 3.0 ticks).

    Returns:
        SyncSignalResult dataclass with bounded signal value and rich timing statistics.
    """
    if not ticks or not pair or len(pair) != 2:
        return _empty_sync_result()

    agent_a, agent_b = str(pair[0]).strip(), str(pair[1]).strip()
    if not agent_a or not agent_b or agent_a == agent_b:
        return _empty_sync_result()

    target_pair_set = {agent_a, agent_b}

    # 1. Identify all shock tick indices in the window
    shock_indices: List[int] = [i for i, t in enumerate(ticks) if _is_shock_tick(t)]
    total_shocks = len(shock_indices)
    if total_shocks == 0:
        return _empty_sync_result(shocks_present=0)

    shock_scores: List[float] = []
    shock_pair_diffs: List[float] = []
    shock_baseline_diffs: List[float] = []
    shock_delays_a: List[float] = []
    shock_delays_b: List[float] = []
    shock_reacting_counts: List[int] = []
    sufficient_baseline_flags: List[bool] = []

    # 2. Evaluate each shock event
    for shock_idx in shock_indices:
        shock_tick = ticks[shock_idx]
        t_shock = _get_tick_time(shock_tick, fallback_idx=shock_idx)

        # Map each agent's last known quote price prior to this shock
        last_price_pre_shock: Dict[str, float] = {}
        for pre_idx in range(shock_idx):
            pre_tick = ticks[pre_idx]
            ag = pre_tick.get("agent_id")
            if ag and pre_tick.get("event") == "quote":
                p = pre_tick.get("price")
                if is_valid_number(p) and float(p) > 0.0:
                    last_price_pre_shock[str(ag).strip()] = float(p)

        # Find first meaningful post-shock re-quote for every agent
        first_reaction_delay: Dict[str, float] = {}

        for post_idx in range(shock_idx + 1, len(ticks)):
            post_tick = ticks[post_idx]
            ag = post_tick.get("agent_id")
            if not ag:
                continue
            ag_str = str(ag).strip()
            if ag_str in first_reaction_delay:
                continue  # Already captured earliest re-quote for this agent

            if post_tick.get("event") != "quote":
                continue

            raw_price = post_tick.get("price")
            if not is_valid_number(raw_price) or float(raw_price) <= 0.0:
                continue
            post_price = float(raw_price)

            # Check if this represents a genuine price update after shock
            pre_price = last_price_pre_shock.get(ag_str)
            if pre_price is not None:
                # If identical to pre-shock quote within tolerance, it's not a new reaction
                price_delta = abs(post_price - pre_price)
                if price_delta <= (pre_price * PRICE_CHANGE_REL_TOLERANCE):
                    continue

            t_post = _get_tick_time(post_tick, fallback_idx=post_idx)
            delay = max(0.0, t_post - t_shock)
            first_reaction_delay[ag_str] = delay

        reacting_agents = list(first_reaction_delay.keys())
        num_reacting = len(reacting_agents)

        # Both agents in the target pair must have reacted to evaluate pairwise synchrony
        if agent_a not in first_reaction_delay or agent_b not in first_reaction_delay:
            continue

        delay_a = first_reaction_delay[agent_a]
        delay_b = first_reaction_delay[agent_b]
        pair_diff = abs(delay_a - delay_b)

        # Construct pairwise differences for all OTHER eligible pairs
        other_pair_diffs: List[float] = []
        for ag1, ag2 in itertools.combinations(reacting_agents, 2):
            if {ag1, ag2} == target_pair_set:
                continue
            d1 = first_reaction_delay[ag1]
            d2 = first_reaction_delay[ag2]
            other_pair_diffs.append(abs(d1 - d2))

        has_baseline = (num_reacting >= MIN_REACTING_AGENTS_FOR_BASELINE) and (len(other_pair_diffs) > 0)

        if has_baseline:
            baseline_diff = _median(other_pair_diffs)
            # Compare target pair synchrony against all-pairs baseline:
            # If pair reacted much more closely than the baseline typical gap:
            diff_advantage = max(0.0, baseline_diff - pair_diff)
            score = diff_advantage / (baseline_diff + max(1.0, jitter_scale))
            bounded_score = min(1.0, max(0.0, score))
        else:
            # Conservative low/neutral score when insufficient agents exist to form a baseline
            baseline_diff = 0.0
            bounded_score = 0.0

        shock_scores.append(bounded_score)
        shock_pair_diffs.append(pair_diff)
        shock_baseline_diffs.append(baseline_diff)
        shock_delays_a.append(delay_a)
        shock_delays_b.append(delay_b)
        shock_reacting_counts.append(num_reacting)
        sufficient_baseline_flags.append(has_baseline)

    if not shock_scores:
        # None of the shocks had bilateral reactions from target pair
        return _empty_sync_result(shocks_present=total_shocks)

    # Robust aggregation across multiple shocks using median
    aggregated_value = _median(shock_scores)
    med_pair_diff = _median(shock_pair_diffs)
    med_baseline_diff = _median(shock_baseline_diffs)
    med_delay_a = _median(shock_delays_a)
    med_delay_b = _median(shock_delays_b)
    max_reacting = max(shock_reacting_counts)
    any_sufficient_baseline = any(sufficient_baseline_flags)

    return SyncSignalResult(
        value=min(1.0, max(0.0, aggregated_value)),
        pair_delay_diff=med_pair_diff,
        baseline_delay_diff=med_baseline_diff,
        shocks_evaluated=len(shock_scores),
        shocks_present=total_shocks,
        reacting_agents_count=max_reacting,
        agent_a_delay=med_delay_a,
        agent_b_delay=med_delay_b,
        has_sufficient_baseline=any_sufficient_baseline,
    )
