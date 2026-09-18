"""
backend/orchestrator.py
-----------------------
Async orchestrator that drives a full CoNDA run.

Architecture
------------
Phase 1 — Tick collection:
    Each tick from run_sim() is broadcast immediately as it arrives and
    appended to an in-memory list.  The detector does NOT receive individual
    ticks or backend-created windows during this phase.

Phase 2 — Detection:
    Once all ticks are collected, the full list is passed to score_run() in
    a thread-pool worker.  Member 2's detector owns all windowing logic
    (window_size=100, stride=25 for the real detector).  The stub uses
    its own internal window size.

Phase 3 — Risk processing:
    Each RiskAssessment yielded by score_run() is persisted, broadcast, and
    evaluated for the automatic-case rule using per-group streak counters.

Per-group streak tracking
-------------------------
``streaks`` is a dict[tuple[str, ...], int] keyed by sorted agent group.
Only the same group appearing in *successive* detector windows advances that
group's streak.  A low-score assessment for group G resets only G's streak.
Different groups in the same detector window are completely independent.

Window deduplication:
    ``seen_windows`` is a set of (group_key, window_start) pairs.  If the
    detector yields multiple assessments for the same group in the same
    window (rare, but possible), only the first one advances the streak.

Swapping to real Member 1 / Member 2 modules:
    Change only the two import lines labelled SWAP HERE.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import AsyncIterator

# SWAP HERE when real modules are available
from backend.sim_stub      import run_sim    # Member 1
from backend.detector_stub import score_run  # Member 2

from backend.db import (
    initialize_db,
    create_run,
    update_run_status,
    update_run_tick,
    save_assessment,
    create_case,
    case_exists_for_run_group,
)
from backend.ws import hub

logger = logging.getLogger(__name__)

# Risk thresholds for automatic case creation.
# NOTE: WINDOW_SIZE has been removed — the detector owns windowing.
CASE_THRESHOLD      = 70   # risk_score >= this is HIGH
CONSECUTIVE_WINDOWS = 3    # consecutive HIGH windows for a group → open case


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def start_run(scenario: str = "default", seed: int = 0) -> str:
    """Start a run in the background; return run_id immediately."""
    initialize_db()
    run_id = str(uuid.uuid4())
    create_run(run_id, scenario, seed)
    logger.info("Starting run %s  scenario=%s seed=%d", run_id, scenario, seed)
    asyncio.create_task(_run_pipeline(run_id, scenario, seed))
    return run_id


async def run_pipeline_direct(run_id: str, scenario: str, seed: int) -> None:
    """Run the pipeline directly (for testing without create_task)."""
    initialize_db()
    create_run(run_id, scenario, seed)
    await _run_pipeline(run_id, scenario, seed)


# ---------------------------------------------------------------------------
# Internal pipeline
# ---------------------------------------------------------------------------

async def _run_pipeline(run_id: str, scenario: str, seed: int) -> None:
    """Drive one complete CoNDA run.

    Phase 1: Iterate ticks from run_sim(), broadcast each, accumulate list.
    Phase 2: Pass full tick list to score_run() in a thread.
    Phase 3: Process each RiskAssessment with per-group streak logic.
    """
    current_tick: int = 0
    all_ticks: list = []

    try:
        # ── Phase 1: collect ticks ──────────────────────────────────────────
        async for tick in _iter_ticks(scenario, seed):
            # Stamp every tick with run_id so the detector can read it.
            tick["run_id"] = run_id
            current_tick = tick.get("t", current_tick)
            update_run_tick(run_id, current_tick)
            await hub.broadcast({"type": "tick", "payload": tick})
            all_ticks.append(tick)

        # Record total tick count now that collection is complete.
        update_run_tick(run_id, current_tick, total_ticks=len(all_ticks))

        # ── Phase 2: run detector on full stream ────────────────────────────
        # score_run() is synchronous; run it in a thread to avoid blocking
        # the event loop.  It owns all windowing internally.
        try:
            assessments: list = await asyncio.to_thread(
                lambda: list(score_run(all_ticks))
            )
        except Exception as exc:
            logger.error(
                "Detector failed for run=%s: %s", run_id, exc
            )
            assessments = []

        # ── Phase 3: process assessments ────────────────────────────────────
        # Per-group streak state.
        streaks: dict[tuple, int] = {}
        # Dedup set: (group_key, window_start) — prevents a group appearing
        # multiple times in one window from advancing the streak twice.
        seen_windows: set[tuple] = set()

        for assessment in assessments:
            assessment["run_id"] = run_id
            streaks, seen_windows = await _process_assessment(
                run_id, assessment, streaks, seen_windows
            )

    except Exception as exc:
        logger.exception("Fatal error in run %s: %s", run_id, exc)
    finally:
        update_run_tick(run_id, current_tick)
        update_run_status(run_id, "done")
        logger.info("Run %s completed at tick %d", run_id, current_tick)


# ---------------------------------------------------------------------------
# Tick iterator helper
# ---------------------------------------------------------------------------

class _StopSentinel:
    pass

_STOP = _StopSentinel()


def _next_or_sentinel(it):
    """Return next item or _STOP — avoids StopIteration inside a coroutine."""
    try:
        return next(it)
    except StopIteration:
        return _STOP


async def _iter_ticks(scenario: str, seed: int) -> AsyncIterator[dict]:
    """Yield MarketTick dicts from run_sim without blocking the event loop.

    Each next() call is dispatched to the thread-pool executor so that the
    50 ms sleep inside the stub does not stall the asyncio event loop.
    """
    loop = asyncio.get_running_loop()
    it = iter(run_sim(scenario, seed))

    while True:
        try:
            tick = await loop.run_in_executor(None, _next_or_sentinel, it)
        except Exception as exc:
            logger.error("Tick iterator raised unexpectedly: %s", exc)
            break
        if isinstance(tick, _StopSentinel):
            break
        yield tick


# ---------------------------------------------------------------------------
# Per-assessment processing (exposed for unit testing)
# ---------------------------------------------------------------------------

async def _process_assessment(
    run_id: str,
    assessment: dict,
    streaks: dict,
    seen_windows: set,
) -> tuple[dict, set]:
    """Persist, broadcast, and evaluate the case rule for one RiskAssessment.

    Parameters
    ----------
    run_id:
        The current run identifier.
    assessment:
        A single RiskAssessment dict as yielded by ``score_run()``.
    streaks:
        Mutable dict mapping ``tuple(sorted(group))`` to consecutive HIGH
        window count for that group.  Updated in place and returned.
    seen_windows:
        Set of ``(group_key, window_start)`` pairs already processed.
        Prevents the same group/window appearing twice from double-counting.

    Returns
    -------
    (streaks, seen_windows)
        Updated state to pass into the next call.
    """
    assessment["run_id"] = run_id

    # Persist and broadcast regardless of streak logic.
    save_assessment(assessment)
    await hub.broadcast({"type": "risk", "payload": assessment})

    group_key: tuple = tuple(sorted(assessment.get("group", [])))
    window_start: int = assessment.get("window_start", 0)
    dedup_key: tuple = (group_key, window_start)

    # Skip streak update if we already processed this group+window pair.
    if dedup_key in seen_windows:
        return streaks, seen_windows
    seen_windows.add(dedup_key)

    # Update per-group streak counter.
    score = assessment.get("risk_score", 0)
    if score >= CASE_THRESHOLD:
        streaks[group_key] = streaks.get(group_key, 0) + 1
    else:
        streaks[group_key] = 0

    # Case rule: 3 consecutive HIGH windows for this group → open a case.
    if (
        streaks.get(group_key, 0) >= CONSECUTIVE_WINDOWS
        and not case_exists_for_run_group(run_id, list(group_key))
    ):
        local_id = str(uuid.uuid4())
        opened_tx = None
        try:
            from backend.chain import open_case as chain_open_case
            opened_tx = chain_open_case(
                evidence_hash=assessment["evidence_hash"],
                risk_score=assessment["risk_score"],
                group_ref=",".join(group_key),
                local_case_id=local_id,
            )
        except Exception as chain_err:
            logger.warning("Blockchain open_case failed: %s", chain_err)

        case = create_case(
            run_id=run_id,
            group=list(group_key),
            risk_score=assessment["risk_score"],
            evidence_hash=assessment["evidence_hash"],
            opened_at_tick=window_start,
            opened_tx=opened_tx,
            case_id=local_id,
        )
        # Reset streak after case opened so further highs don't open another.
        streaks[group_key] = 0
        logger.info(
            "Case %s opened run=%s window_start=%d streak=%d (tx=%s)",
            case["case_id"], run_id, window_start,
            CONSECUTIVE_WINDOWS, opened_tx,
        )
        await hub.broadcast({"type": "case", "payload": case})

    return streaks, seen_windows