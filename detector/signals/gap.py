"""Counterfactual Gap Signal for CoNDA.

Measures the persistent deviation between observed quotes from an agent pair
and the competitive counterfactual reference price.

Key Principles:
1. Behavioral Signal: A deviation indicates divergence from competitive pricing,
   NOT proof of collusion.
2. Persistence Over Outliers: Single rogue quotes or brief volatility spikes do not
   dominate the metric; the signal evaluates median deviation combined with persistence.
3. Ground-Truth Agnostic: Operates strictly on observed agent IDs without referencing
   labels, agent classes, or metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from detector.counterfactual import compute_counterfactual_price, is_valid_number

# Minimum observations required from each agent in the pair to assess pairwise persistence
MIN_AGENT_OBSERVATIONS = 1

# Default deviation threshold below which price difference is treated as normal market noise (1.0%)
DEFAULT_TOLERANCE = 0.010

# Maximum deviation clipping per observation to safeguard numerical stability (100% gap)
MAX_OBSERVATION_DEV_CLIP = 1.0


@dataclass
class GapSignalResult:
    """Structured result of the counterfactual gap evaluation."""
    value: float                  # Bounded in [0.0, 1.0] for downstream scoring
    median_gap_pct: float         # Median percentage deviation (e.g., 4.3 for 4.3%)
    mean_gap_pct: float           # Mean percentage deviation
    signed_median_gap_pct: float  # Signed median deviation (+ means above ref, - means below)
    persistence_ratio: float      # Proportion of observations exceeding tolerance [0.0, 1.0]
    sample_count: int             # Total valid pairwise observations evaluated
    obs_a_count: int              # Number of valid observations from agent A
    obs_b_count: int              # Number of valid observations from agent B
    observed_median_price: float  # Median observed price for the pair
    reference_median_price: float # Median reference price for the pair
    side_evaluated: str           # Predominant side ('ask', 'bid', or 'mixed')

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics to a dictionary for explainers or loggers."""
        return {
            "value": round(self.value, 4),
            "median_gap_pct": round(self.median_gap_pct, 2),
            "mean_gap_pct": round(self.mean_gap_pct, 2),
            "signed_median_gap_pct": round(self.signed_median_gap_pct, 2),
            "persistence_ratio": round(self.persistence_ratio, 3),
            "sample_count": self.sample_count,
            "obs_a_count": self.obs_a_count,
            "obs_b_count": self.obs_b_count,
            "observed_median_price": round(self.observed_median_price, 2),
            "reference_median_price": round(self.reference_median_price, 2),
            "side_evaluated": self.side_evaluated,
        }


def _empty_gap_result(side: str = "none") -> GapSignalResult:
    """Return a neutral zero-valued result for insufficient data or edge cases."""
    return GapSignalResult(
        value=0.0,
        median_gap_pct=0.0,
        mean_gap_pct=0.0,
        signed_median_gap_pct=0.0,
        persistence_ratio=0.0,
        sample_count=0,
        obs_a_count=0,
        obs_b_count=0,
        observed_median_price=0.0,
        reference_median_price=0.0,
        side_evaluated=side,
    )


def _median(values: Sequence[float]) -> float:
    """Deterministic median computation."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def compute_counterfactual_gap(
    ticks: List[Dict[str, Any]],
    pair: Tuple[str, str],
    tolerance: float = DEFAULT_TOLERANCE,
    max_clip: float = MAX_OBSERVATION_DEV_CLIP,
) -> GapSignalResult:
    """Evaluate persistent deviation of an agent pair from competitive reference pricing.

    Algorithm:
    1. Filter ticks for the requested pair of agent IDs.
    2. Ensure both agents have sufficient observations; return neutral 0.0 if one or both
       are absent (cannot claim pairwise coordination without bilateral data).
    3. For each observation:
       - compute point-in-time reference price using pool reserves, oracle, and fee.
       - compute normalized relative deviation: abs(obs - ref) / ref.
       - clip individual deviations to max_clip to prevent rogue outliers from dominating.
    4. Compute robust summary statistics:
       - median normalized deviation (robust against one-off quote anomalies).
       - persistence ratio: fraction of observations where deviation > tolerance.
    5. Formulate final bounded signal:
       - value = min(1.0, max(0.0, median_gap * persistence_ratio)).

    Args:
        ticks: Sequence of tick dictionaries in the current window.
        pair: Tuple of two agent ID strings, e.g. ("A1", "A2").
        tolerance: Minimum relative deviation threshold to count as non-noise (default: 0.01).
        max_clip: Upper bound for per-quote deviation clipping (default: 1.0 = 100%).

    Returns:
        GapSignalResult dataclass containing bounded signal value and rich summary statistics.
    """
    # Guard against invalid inputs
    if not ticks or not pair or len(pair) != 2:
        return _empty_gap_result()

    agent_a, agent_b = str(pair[0]).strip(), str(pair[1]).strip()
    if not agent_a or not agent_b or agent_a == agent_b:
        return _empty_gap_result()

    target_agents = {agent_a, agent_b}

    abs_deviations: List[float] = []
    signed_deviations: List[float] = []
    observed_prices: List[float] = []
    reference_prices: List[float] = []
    sides: List[str] = []

    obs_a = 0
    obs_b = 0

    for tick in ticks:
        agent_id = tick.get("agent_id")
        if agent_id not in target_agents:
            continue

        event = tick.get("event")
        # Only evaluate quotes or trades with explicit price
        if event not in ("quote", "trade"):
            continue

        raw_price = tick.get("price")
        if not is_valid_number(raw_price):
            continue

        obs_price = float(raw_price)
        if obs_price <= 0.0:
            continue

        side = str(tick.get("side", "mid")).strip().lower()

        # Compute point-in-time reference price for this tick
        ref_price = compute_counterfactual_price(
            pool=tick.get("pool"),
            oracle_price=tick.get("oracle_price"),
            side=side,
        )

        if ref_price is None or not is_valid_number(ref_price) or ref_price <= 0.0:
            continue

        # Valid comparable observation
        if agent_id == agent_a:
            obs_a += 1
        elif agent_id == agent_b:
            obs_b += 1

        # Normalized relative deviation
        raw_abs_dev = abs(obs_price - ref_price) / ref_price
        clipped_abs_dev = min(max_clip, max(0.0, raw_abs_dev))
        signed_dev = (obs_price - ref_price) / ref_price

        abs_deviations.append(clipped_abs_dev)
        signed_deviations.append(signed_dev)
        observed_prices.append(obs_price)
        reference_prices.append(ref_price)
        sides.append(side)

    # Require evidence from both agents in the pair
    if obs_a < MIN_AGENT_OBSERVATIONS or obs_b < MIN_AGENT_OBSERVATIONS:
        return _empty_gap_result()

    total_obs = len(abs_deviations)
    if total_obs == 0:
        return _empty_gap_result()

    # Calculate median and persistence
    med_dev = _median(abs_deviations)
    mean_dev = sum(abs_deviations) / total_obs
    signed_med_dev = _median(signed_deviations)

    # Persistence ratio: fraction of observations where deviation exceeds tolerance
    persistent_count = sum(1 for d in abs_deviations if d > tolerance)
    persistence_ratio = persistent_count / total_obs

    # Signal value combines median deviation with persistence, bounded strictly in [0.0, 1.0]
    # For example, persistent 4.3% gap across 100% of ticks yields value = 0.043
    raw_signal = med_dev * persistence_ratio
    bounded_value = min(1.0, max(0.0, raw_signal))

    # Determine predominant side
    ask_count = sum(1 for s in sides if s == "ask")
    bid_count = sum(1 for s in sides if s == "bid")
    if ask_count > bid_count:
        predominant_side = "ask"
    elif bid_count > ask_count:
        predominant_side = "bid"
    else:
        predominant_side = "mixed"

    return GapSignalResult(
        value=bounded_value,
        median_gap_pct=med_dev * 100.0,
        mean_gap_pct=mean_dev * 100.0,
        signed_median_gap_pct=signed_med_dev * 100.0,
        persistence_ratio=persistence_ratio,
        sample_count=total_obs,
        obs_a_count=obs_a,
        obs_b_count=obs_b,
        observed_median_price=_median(observed_prices),
        reference_median_price=_median(reference_prices),
        side_evaluated=predominant_side,
    )
