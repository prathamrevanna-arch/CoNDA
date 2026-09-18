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
