"""Detector Configuration and Hand-Tuned Weights for CoNDA.

Contains explicit named constants for windowing, signal weights, and verdict thresholds.
No weights are machine-learned or trained against fixture labels.
"""

from typing import Dict

# Rolling window parameters based on tick counts (not timestamps)
DEFAULT_WINDOW_SIZE: int = 100
DEFAULT_WINDOW_STRIDE: int = 25

# Hand-tuned signal weights for base MVP
# Rationale:
# - counterfactual_gap (0.60): Direct structural evidence of supracompetitive pricing
#   in the AMM pool. Persistent price markup carries slightly higher evidentiary weight.
# - sync_under_shock (0.40): Strong dynamic behavioral confirmation. Measures whether
#   the pair re-quotes with anomalous coordination relative to the all-pairs baseline.
# The weights sum to exactly 1.0.
BASE_SIGNAL_WEIGHTS: Dict[str, float] = {
    "counterfactual_gap": 0.60,
    "sync_under_shock": 0.40,
}

# Verdict risk score thresholds
# - LOW: < 40
# - MEDIUM: 40 <= score < 70
# - HIGH: >= 70
VERDICT_LOW_THRESHOLD: int = 40
VERDICT_HIGH_THRESHOLD: int = 70

# Gap signal normalization reference scale.
#
# RATIONALE:
# The raw gap value formula is: raw = median_abs_fraction * persistence_ratio
# Without normalization, a realistic 5% price gap produces raw = 0.05 * 1.0 = 0.05.
# With weights gap=0.60, sync=0.40, that only contributes 3/100 points — the signal
# is numerically invisible against a realistic sync score of ~0.81 (32/100 points).
# A weights-only fix is mathematically impossible: keeping competitive LOW requires
# sync_weight <= 0.58, but cartel HIGH requires sync_weight >= 0.86 — a contradiction.
#
# The fix: apply tanh normalization anchored at this scale.
#   gap_value = tanh(raw / GAP_REFERENCE_SCALE)
#
# tanh is smooth (no hard cliff), monotonically increasing, and bounded in [0, 1).
# Critically, it DOES NOT saturate at the reference scale — values above 5% are still
# continuously distinguishable, unlike a simple linear/clip which makes 5% and 78%
# identical. Key points on the curve:
#   2.5% persistent gap  -> tanh(0.5) = 0.462  (half-strength, graded)
#   5.0% persistent gap  -> tanh(1.0) = 0.762  (reference, NOT saturated)
#  10.0% persistent gap  -> tanh(2.0) = 0.964  (near-max, still graded)
#  78.0% persistent gap  -> tanh(15.6)~ 1.000  (extreme cartel, asymptote)
GAP_REFERENCE_SCALE: float = 0.05  # 5% = reference-strength gap signal anchor

