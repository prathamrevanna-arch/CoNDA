"""
backend/orchestrator.py
-----------------------
Async orchestrator that drives a full CoNDA run.

Swapping to real Member 1 / Member 2 modules:
    Change only the two import lines labelled SWAP HERE.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import AsyncIterator, Iterator

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

WINDOW_SIZE         = 4
CASE_THRESHOLD      = 70
CONSECUTIVE_WINDOWS = 3


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


async def _run_pipeline(run_id: str, scenario: str, seed: int) -> None:
    window: list = []
    current_tick: int = 0
    high_streak: int = 0
    case_opened: bool = False

    try:
        async for tick in _iter_ticks(scenario, seed):
            current_tick = tick.get("t", current_tick)
            update_run_tick(run_id, current_tick)
            await hub.broadcast({"type": "tick", "payload": tick})
            window.append(tick)

            if len(window) >= WINDOW_SIZE:
                completed_window = window[:]
                window = []
                high_streak, case_opened = await _process_window(
                    run_id, completed_window, current_tick,
                    high_streak, case_opened,
                )

        if window:
            await _process_window(
                run_id, window, current_tick, high_streak, case_opened
            )

    except Exception as exc:
        logger.exception("Fatal error in run %s: %s", run_id, exc)
    finally:
        update_run_tick(run_id, current_tick)
        update_run_status(run_id, "done")
        logger.info("Run %s completed at tick %d", run_id, current_tick)


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


async def _process_window(
    run_id: str,
    window: list,
    current_tick: int,
    high_streak: int,
    case_opened: bool,
) -> tuple:
    """Score one window, persist, broadcast, evaluate case rule.

    Returns updated (high_streak, case_opened).
    """
    try:
        assessments: list = await asyncio.to_thread(
            lambda: list(score_run(window))
        )
    except Exception as exc:
        logger.error(
            "Detector failed run=%s tick=%d: %s", run_id, current_tick, exc
        )
        return high_streak, case_opened

    for assessment in assessments:
        assessment["run_id"] = run_id

        save_assessment(assessment)
        await hub.broadcast({"type": "risk", "payload": assessment})

        score = assessment.get("risk_score", 0)
        if score >= CASE_THRESHOLD:
            high_streak += 1
        else:
            high_streak = 0
            case_opened = False

        if (
            high_streak >= CONSECUTIVE_WINDOWS
            and not case_opened
            and not case_exists_for_run_group(run_id, assessment["group"])
        ):
            case = create_case(
                run_id=run_id,
                group=assessment["group"],
                risk_score=assessment["risk_score"],
                evidence_hash=assessment["evidence_hash"],
                opened_at_tick=current_tick,
            )
            case_opened = True
            logger.info(
                "Case %s opened run=%s tick=%d streak=%d",
                case["case_id"], run_id, current_tick, high_streak,
            )
            await hub.broadcast({"type": "case", "payload": case})

    return high_streak, case_opened