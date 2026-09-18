"""Factual Explanation Generator for CoNDA Detector Signals.

Converts numerical detector signals and structured telemetry into concise, factual,
non-accusatory human-readable explanations.

Key Principles:
1. Observed Behavior Only: Explains what was measured without asserting intent or guilt.
2. Non-Accusatory: Never claims agents "colluded", "are guilty", or "formed a cartel".
3. Ground-Truth Agnostic: Derives context strictly from observable market measurements.
4. Robust & Resilient: Handles missing statistics, NaNs, infinities, and empty windows safely.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely cast a value to a finite float, returning default if invalid or non-finite."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    """Safely cast a value to an integer, returning default if invalid."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _get_attr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    """Retrieve attribute from dataclass/object or key from dictionary."""
    if obj is None:
        return default
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def explain_gap(signal_data: Any) -> str:
    """Generate a factual, non-accusatory explanation for counterfactual_gap.

    Incorporates:
    - median percentage deviation
    - direction (above vs below competitive reference)
    - observed vs reference median prices
    - persistence ratio across comparable observations

    Args:
        signal_data: GapSignalResult instance or dictionary with gap metrics.

    Returns:
        One concise, factual sentence.
    """
    if signal_data is None:
        return "No quote deviation data was available for this pair in this window."

    sample_count = _safe_int(_get_attr_or_key(signal_data, "sample_count", 0))
    if sample_count == 0:
        return "Insufficient comparable quote observations were available to evaluate price deviation."

    med_gap_pct = _safe_float(_get_attr_or_key(signal_data, "median_gap_pct", 0.0))
    signed_gap = _safe_float(_get_attr_or_key(signal_data, "signed_median_gap_pct", med_gap_pct))
    persistence_ratio = _safe_float(_get_attr_or_key(signal_data, "persistence_ratio", 0.0))
    persistence_pct = round(persistence_ratio * 100.0)

    obs_p = _safe_float(_get_attr_or_key(signal_data, "observed_median_price", 0.0))
    ref_p = _safe_float(_get_attr_or_key(signal_data, "reference_median_price", 0.0))

    # If deviation is essentially zero
    if med_gap_pct < 0.1:
        if obs_p > 0 and ref_p > 0:
            return f"Observed quotes aligned with the competitive reference ({obs_p:.1f} vs {ref_p:.1f}) across comparable observations."
        return "Observed quotes aligned closely with the competitive reference across comparable observations."

    direction = "above" if signed_gap >= 0 else "below"

    # Full details if observed and reference prices exist
    if obs_p > 0 and ref_p > 0:
        return (
            f"Observed quotes were {med_gap_pct:.1f}% {direction} the competitive reference "
            f"({obs_p:.1f} vs {ref_p:.1f}) with the deviation persisting across {persistence_pct}% "
            f"of comparable observations."
        )

    # Partial details fallback
    return (
        f"Observed quotes were {med_gap_pct:.1f}% {direction} the competitive reference "
        f"across {persistence_pct}% of comparable observations."
    )


def explain_sync(signal_data: Any) -> str:
    """Generate a factual, non-accusatory explanation for sync_under_shock.

    Incorporates:
    - pair reaction delay difference
    - baseline median timing difference
    - number of shocks considered
    - presence of baseline evidence

    Args:
        signal_data: SyncSignalResult instance or dictionary with sync metrics.

    Returns:
        One concise, factual sentence.
    """
    if signal_data is None:
        return "No shock-synchronization data was available in this window."

    shocks_present = _safe_int(_get_attr_or_key(signal_data, "shocks_present", 0))
    if shocks_present == 0:
        return "No public shock occurred in this window, so no shock-synchronization evidence was observed."

    shocks_evaluated = _safe_int(_get_attr_or_key(signal_data, "shocks_evaluated", 0))
    if shocks_evaluated == 0:
        return "Insufficient post-shock reaction data was available to evaluate pair synchronization."

    pair_diff = _safe_float(_get_attr_or_key(signal_data, "pair_delay_diff", 0.0))
    baseline_diff = _safe_float(_get_attr_or_key(signal_data, "baseline_delay_diff", 0.0))
    has_baseline = bool(_get_attr_or_key(signal_data, "has_sufficient_baseline", False))

    pair_diff_int = int(round(pair_diff))
    baseline_diff_int = int(round(baseline_diff))

    pair_tick_str = f"{pair_diff_int} tick" if pair_diff_int == 1 else f"{pair_diff_int} ticks"
    baseline_tick_str = f"{baseline_diff_int} tick" if baseline_diff_int == 1 else f"{baseline_diff_int}-tick"

    if not has_baseline:
        return (
            f"After the shock, the pair re-quoted within {pair_tick_str} of each other, "
            f"but insufficient market agents reacted to establish an all-pairs baseline."
        )

    if pair_diff >= baseline_diff:
        return (
            f"After the shock, the pair's timing difference of {pair_tick_str} was not more "
            f"synchronized than the {baseline_tick_str} median baseline among other eligible pairs."
        )

    return (
        f"After the shock, the pair re-quoted within {pair_tick_str} of each other, "
        f"compared with a {baseline_tick_str} median baseline difference among other eligible pairs."
    )


def explain_signal(signal_name: str, signal_data: Any) -> str:
    """Route a signal name and its associated data to the appropriate explanation generator.

    Args:
        signal_name: Name identifier, e.g. 'counterfactual_gap' or 'sync_under_shock'.
        signal_data: Signal result dataclass, dictionary, or numeric value.

    Returns:
        Human-readable factual explanation string.
    """
    clean_name = str(signal_name).strip().lower()

    if clean_name == "counterfactual_gap":
        return explain_gap(signal_data)
    elif clean_name == "sync_under_shock":
        return explain_sync(signal_data)

    # Generic fallback for future or unknown signals
    val = _safe_float(
        _get_attr_or_key(signal_data, "value", signal_data)
    )
    return f"Signal '{signal_name}' registered an observed value of {val:.4f} in this window."


def explain_signals(signals: Dict[str, Any]) -> Dict[str, str]:
    """Generate explanations for a dictionary of signals.

    Args:
        signals: Mapping of signal names to their results/data.

    Returns:
        Mapping of signal names to explanation strings.
    """
    if not signals:
        return {}

    explanations: Dict[str, str] = {}
    for name, data in signals.items():
        explanations[name] = explain_signal(name, data)
    return explanations
