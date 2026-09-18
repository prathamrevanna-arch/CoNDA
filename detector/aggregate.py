"""Signal Aggregation and Contribution Allocation for CoNDA.

Combines independent behavioral signal values into a single integer Coordination Risk
score (0-100), allocates exact integer contributions using the Largest Remainder Method,
and assigns categorical verdicts (LOW, MEDIUM, HIGH).

Key Guarantees:
1. Exact Contribution Sum: The sum of integer signal contributions equals risk_score exactly.
2. Safe Numerical Clamping: All inputs are clamped safely to [0.0, 1.0]; NaN, infinity,
   and negative numbers are handled gracefully.
3. Weight Renormalization: If an active signal is omitted or absent, weights of the
   remaining active signals renormalize to 1.0.
4. Ground-Truth Agnostic: Pure mathematical aggregation without inspecting scenario labels.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple

from detector.config import (
    BASE_SIGNAL_WEIGHTS,
    VERDICT_HIGH_THRESHOLD,
    VERDICT_LOW_THRESHOLD,
)


@dataclass
class AggregationResult:
    """Structured result of the signal aggregation and contribution allocation."""
    risk_score: int                           # Bounded integer risk score [0, 100]
    verdict: str                              # 'LOW', 'MEDIUM', or 'HIGH'
    contributions: Dict[str, int]             # Exact integer contribution per signal
    normalized_values: Dict[str, float]       # Clamped [0.0, 1.0] signal values
    effective_weights: Dict[str, float]       # Renormalized weights used

    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregation result to a dictionary representation."""
        return {
            "risk_score": self.risk_score,
            "verdict": self.verdict,
            "contributions": self.contributions,
            "normalized_values": {k: round(v, 4) for k, v in self.normalized_values.items()},
            "effective_weights": {k: round(w, 4) for k, w in self.effective_weights.items()},
        }


def get_verdict(risk_score: int) -> str:
    """Map an integer risk score to a frozen verdict category.

    Thresholds:
    - LOW: risk_score < 40
    - MEDIUM: 40 <= risk_score < 70
    - HIGH: risk_score >= 70

    Args:
        risk_score: Integer score from 0 to 100.

    Returns:
        Verdict string: 'LOW', 'MEDIUM', or 'HIGH'.
    """
    if risk_score < VERDICT_LOW_THRESHOLD:
        return "LOW"
    elif risk_score < VERDICT_HIGH_THRESHOLD:
        return "MEDIUM"
    else:
        return "HIGH"


def _extract_numeric_value(raw_signal: Any) -> Optional[float]:
    """Safely extract and clamp a numeric signal value into [0.0, 1.0].

    Supports:
    - float or int numbers
    - Objects with a `.value` attribute (e.g. GapSignalResult, SyncSignalResult)
    - Dictionaries containing a 'value' key

    Returns:
        Clamped float in [0.0, 1.0], or None if the input cannot be parsed.
    """
    if raw_signal is None:
        return None

    extracted: Any = raw_signal

    # Check if object has a 'value' attribute
    if hasattr(raw_signal, "value"):
        extracted = getattr(raw_signal, "value")
    # Check if dictionary has a 'value' key
    elif isinstance(raw_signal, dict) and "value" in raw_signal:
        extracted = raw_signal.get("value")

    if extracted is None:
        return None

    try:
        num = float(extracted)
        if math.isnan(num):
            return 0.0
        if math.isinf(num):
            return 1.0 if num > 0 else 0.0
        # Clamp safely into [0.0, 1.0]
        return min(1.0, max(0.0, num))
    except (ValueError, TypeError):
        return 0.0


def allocate_contributions(
    raw_contributions: Dict[str, float],
    total_target: int,
) -> Dict[str, int]:
    """Allocate exact integer contributions using the Largest Remainder Method (Hamilton-Hare).

    Guarantees:
    - sum(allocated_contributions.values()) == total_target
    - Deterministic tie-breaking using alphabetical signal name sorting.

    Args:
        raw_contributions: Map of signal names to unrounded float contributions.
        total_target: Target integer sum (the risk_score).

    Returns:
        Dictionary of signal names to integer contributions summing exactly to total_target.
    """
    if not raw_contributions:
        return {}

    if total_target <= 0:
        return {k: 0 for k in raw_contributions}

    # Step 1: Deterministic alphabetical order for predictable tie-breaking
    sorted_keys = sorted(raw_contributions.keys())

    # Step 2: Floor allocation and remainders
    floored: Dict[str, int] = {}
    remainders: List[Tuple[float, str]] = []

    for k in sorted_keys:
        raw_val = max(0.0, raw_contributions[k])
        fl = math.floor(raw_val)
        floored[k] = fl
        remainders.append((raw_val - fl, k))

    # Step 3: Determine surplus points to distribute
    allocated_sum = sum(floored.values())
    surplus = total_target - allocated_sum

    if surplus > 0:
        # Distribute 1 point to signals with largest remainder
        # In case of equal remainders, preserve deterministic key order
        remainders.sort(key=lambda item: (-item[0], item[1]))
        for i in range(min(surplus, len(remainders))):
            signal_key = remainders[i][1]
            floored[signal_key] += 1
    elif surplus < 0:
        # If total_target is smaller than floor sum (rare edge case with negative remainders)
        remainders.sort(key=lambda item: (item[0], item[1]))
        deficit = -surplus
        for i in range(min(deficit, len(remainders))):
            signal_key = remainders[i][1]
            if floored[signal_key] > 0:
                floored[signal_key] -= 1

    return floored


def aggregate_signals(
    signals: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> AggregationResult:
    """Combine behavioral signal values into a total risk score and integer contributions.

    Algorithm:
    1. Extract and sanitize numeric signal values into [0.0, 1.0].
    2. Filter out omitted or absent signals (unimplemented signals are omitted).
    3. Renormalize weights for the active signals so they sum to 1.0.
    4. Compute continuous weighted score: raw_score = sum(val_i * weight_i).
    5. Convert to bounded integer risk score: risk_score = round(raw_score * 100).
    6. Allocate integer contributions using allocate_contributions so their sum
       equals risk_score exactly.
    7. Determine qualitative verdict (LOW, MEDIUM, HIGH).

    Args:
        signals: Dict mapping signal names to signal objects, dicts, or floats.
        weights: Optional override for signal weights (defaults to BASE_SIGNAL_WEIGHTS).

    Returns:
        AggregationResult containing risk_score, verdict, and exact integer contributions.
    """
    if not signals:
        return AggregationResult(
            risk_score=0,
            verdict="LOW",
            contributions={},
            normalized_values={},
            effective_weights={},
        )

    configured_weights = weights if weights is not None else BASE_SIGNAL_WEIGHTS

    # 1. Parse and extract active signals
    active_values: Dict[str, float] = {}
    for name, raw_obj in signals.items():
        val = _extract_numeric_value(raw_obj)
        if val is not None:
            active_values[name] = val

    if not active_values:
        return AggregationResult(
            risk_score=0,
            verdict="LOW",
            contributions={},
            normalized_values={},
            effective_weights={},
        )

    # 2. Renormalize weights among present signals
    raw_weight_sum = 0.0
    active_weights: Dict[str, float] = {}
    for name in active_values:
        w = configured_weights.get(name, 1.0 / len(active_values))
        w_safe = max(0.0, float(w)) if not (math.isnan(w) or math.isinf(w)) else 0.0
        active_weights[name] = w_safe
        raw_weight_sum += w_safe

    effective_weights: Dict[str, float] = {}
    if raw_weight_sum > 0.0:
        for name, w in active_weights.items():
            effective_weights[name] = w / raw_weight_sum
    else:
        # Uniform fallback if all weights are zero
        uniform_w = 1.0 / len(active_values)
        for name in active_values:
            effective_weights[name] = uniform_w

    # 3. Compute continuous raw contributions (out of 100)
    raw_contributions: Dict[str, float] = {}
    raw_total_score = 0.0
    for name, val in active_values.items():
        w = effective_weights[name]
        c_float = val * w * 100.0
        raw_contributions[name] = c_float
        raw_total_score += c_float

    # 4. Map to integer risk score bounded strictly in [0, 100]
    risk_score = min(100, max(0, int(round(raw_total_score))))

    # 5. Allocate integer contributions guaranteed to sum to risk_score
    contributions = allocate_contributions(raw_contributions, risk_score)

    # 6. Assign verdict category
    verdict = get_verdict(risk_score)

    return AggregationResult(
        risk_score=risk_score,
        verdict=verdict,
        contributions=contributions,
        normalized_values=active_values,
        effective_weights=effective_weights,
    )
