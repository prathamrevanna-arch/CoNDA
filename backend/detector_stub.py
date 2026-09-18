"""
backend/detector_stub.py
------------------------
Development stub for Member 2's detection interface.

Public interface (matches real Member 2 detector):
    score_run(
        ticks: Iterable[dict],
        window_size: int = 4,   # real detector uses 100; stub uses _WINDOW_SIZE=4
        stride: int = 1,        # real detector uses 25;  stub ignores stride
    ) -> Iterator[dict]

This stub does NOT perform real collusion detection.  It materialises the
full tick stream, slices it into fixed-size windows (_WINDOW_SIZE=4), and
returns canned RiskAssessment dicts whose risk_score ramps deterministically
from 20 → 90 across the run.

The ``window_size`` and ``stride`` keyword arguments are accepted so that
this stub's signature is identical to the real detector, making the import
line in orchestrator.py swappable without any other changes.

Swapping to the real detector:
    Replace the import in orchestrator.py with:
        from detector.detector import score_run   # Member 2's real module
    No other changes needed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Iterable, Iterator

# Window size in ticks (number of MarketTick records per assessment).
_WINDOW_SIZE: int = 4

# Deterministic collusion group shown in every assessment.
_GROUP: list[str] = ["A2", "A3"]

# Deterministic fake signal template.
_SIGNALS: dict = {
    "price_correlation": {
        "value": 0.0,        # overwritten per window
        "contribution": 0,   # overwritten per window
        "explanation": "Stub: price correlation between A2 and A3 quote streams.",
    },
    "spread_compression": {
        "value": 0.0,
        "contribution": 0,
        "explanation": "Stub: bid-ask spread narrowing consistent with coordination.",
    },
}

# Fake computation time (ms) — deterministic.
_COMPUTED_MS: float = 12.4


def _verdict(score: int) -> str:
    """Map an integer risk score to a verdict string."""
    if score < 40:
        return "LOW"
    if score < 70:
        return "MEDIUM"
    return "HIGH"


def _evidence_hash(window_start: int, window_end: int, run_id: str) -> str:
    """Return a deterministic 0x-prefixed 64-hex-character evidence hash."""
    payload = json.dumps(
        {"run_id": run_id, "ws": window_start, "we": window_end},
        sort_keys=True,
    ).encode()
    return "0x" + hashlib.sha256(payload).hexdigest()


def score_run(
    ticks: Iterable[dict],
    window_size: int = 4,
    stride: int = 1,
) -> Iterator[dict]:
    """Yield deterministic RiskAssessment dicts for each window of *ticks*.

    The full tick iterable is consumed first (materialised into a list) so
    that the number of windows can be determined up front.  The backend must
    pass the **complete** tick stream here — not pre-sliced windows.

    Parameters
    ----------
    ticks:
        Iterable of MarketTick dicts as produced by ``run_sim()``.
    window_size:
        Accepted for API compatibility with the real Member 2 detector
        (which uses ``window_size=100``).  This stub ignores the value and
        uses its own internal ``_WINDOW_SIZE`` constant instead.
    stride:
        Accepted for API compatibility with the real Member 2 detector
        (which uses ``stride=25``).  This stub ignores the value.

    Yields
    ------
    dict
        RiskAssessment record with keys: run_id, window_start, window_end,
        group, risk_score, verdict, signals, counterfactual, evidence_hash,
        computed_ms.
    """

    tick_list = list(ticks)          # materialise so we can count windows
    total = len(tick_list)
    if total == 0:
        return

    # Determine run_id from the first tick (or fallback).
    run_id: str = tick_list[0].get("run_id", "run-unknown")

    # Number of complete (or partial) windows.
    n_windows = max(1, (total + _WINDOW_SIZE - 1) // _WINDOW_SIZE)

    # Risk scores ramp from 20 → 90 across windows.
    score_start = 20
    score_end = 90

    for i in range(n_windows):
        # Window tick slice.
        w_ticks = tick_list[i * _WINDOW_SIZE : (i + 1) * _WINDOW_SIZE]
        window_start: int = w_ticks[0]["t"]
        window_end: int = w_ticks[-1]["t"]

        # Linear interpolation: first window → score_start, last → score_end.
        if n_windows == 1:
            risk_score = score_end
        else:
            risk_score = round(
                score_start + (score_end - score_start) * i / (n_windows - 1)
            )

        # Build a fake counterfactual from available tick prices.
        prices = [t["price"] for t in w_ticks if "price" in t]
        ref_price = round(float(w_ticks[0].get("oracle_price", 100.0)), 2)
        obs_price = round(sum(prices) / len(prices), 2) if prices else ref_price
        gap_pct = round(abs(obs_price - ref_price) / ref_price * 100, 2)

        # Build signals with window-specific fake values.
        corr_value = round(0.3 + 0.07 * i, 3)
        signals = {
            "price_correlation": {
                "value": corr_value,
                "contribution": round(risk_score * 0.6),
                "explanation": _SIGNALS["price_correlation"]["explanation"],
            },
            "spread_compression": {
                "value": round(0.1 + 0.02 * i, 3),
                "contribution": round(risk_score * 0.4),
                "explanation": _SIGNALS["spread_compression"]["explanation"],
            },
        }

        yield {
            "run_id": run_id,
            "window_start": window_start,
            "window_end": window_end,
            "group": _GROUP,
            "risk_score": risk_score,
            "verdict": _verdict(risk_score),
            "signals": signals,
            "counterfactual": {
                "reference_price": ref_price,
                "observed_price": obs_price,
                "gap_pct": gap_pct,
            },
            "evidence_hash": _evidence_hash(window_start, window_end, run_id),
            "computed_ms": _COMPUTED_MS,
        }
