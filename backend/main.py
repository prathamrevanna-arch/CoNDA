"""
backend/main.py
---------------
FastAPI service for CoNDA — Step 3.

Routes (frozen public contract):
    GET  /health
    GET  /scenarios
    POST /run/start
    GET  /run/{run_id}/status
    WS   /ws/live
    GET  /risk/latest?run_id=
    GET  /cases
    POST /case/open
    POST /case/{case_id}/challenge
    GET  /metrics

The routes delegate to the existing Step 2 modules:
    backend.db          — SQLite persistence
    backend.ws          — WebSocket hub
    backend.orchestrator — run pipeline

Do NOT add blockchain or challenge-verification logic here;
those belong to Step 4 (backend/chain.py, backend/challenge.py).
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.db import (
    initialize_db,
    get_run,
    get_latest_assessment,
    list_cases,
    create_case,
    case_exists_for_run_group,
)
from backend.orchestrator import start_run
from backend.ws import hub

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise SQLite on startup.  No Anvil required."""
    initialize_db()
    logger.info("CoNDA FastAPI started.  DB initialised.")
    yield
    logger.info("CoNDA FastAPI shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CoNDA API",
    version="0.3.0",
    description="Collusion Detection for Autonomous Agents",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class StartRunRequest(BaseModel):
    scenario: str = Field(default="default", examples=["default"])


class StartRunResponse(BaseModel):
    run_id: str


class RunStatusResponse(BaseModel):
    state: str          # "running" | "done"
    tick: int
    total: int


class HealthResponse(BaseModel):
    ok: bool
    chain: bool
    detector: str       # "real" | "stub"


class ScenarioItem(BaseModel):
    id: str
    label: str


class OpenCaseRequest(BaseModel):
    run_id: str
    group: List[str]
    risk_score: int
    evidence_hash: str


class ChallengeRequest(BaseModel):
    """
    A valid challenge proves execution-policy compliance only —
    it does NOT prove innocence of tacit coordination.
    """
    agent_id: Optional[str] = None
    agent_address: Optional[str] = None
    policy_commitment: Optional[str] = None
    policy_hash: Optional[str] = None
    policy_json: Optional[Any] = None
    signature: Optional[str] = None
    flagged_action: Optional[Any] = None
    trace: Optional[Any] = None


# ---------------------------------------------------------------------------
# Available scenarios (stub list for Step 3)
# Member 1's real scenarios will extend this list later.
# ---------------------------------------------------------------------------

_SCENARIOS: List[dict] = [
    {"id": "default", "label": "Default 3-agent DeFi market"},
]

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health() -> dict:
    """
    Health check.

    chain=True if local Anvil is running and CaseRegistry is reachable, else False.
    detector="stub" until Member 2's real module is integrated.
    """
    from backend.chain import is_chain_available
    return {"ok": True, "chain": is_chain_available(), "detector": "stub"}


@app.get("/scenarios", response_model=List[ScenarioItem])
async def scenarios() -> list:
    """Return the list of available simulation scenarios."""
    return _SCENARIOS


@app.post("/run/start", response_model=StartRunResponse, status_code=202)
async def run_start(body: StartRunRequest) -> dict:
    """
    Start a simulation run.

    Returns the run_id immediately; the simulation runs in the background.
    The client can subscribe to /ws/live for real-time tick/risk/case frames.
    """
    # Validate scenario against known list
    known = {s["id"] for s in _SCENARIOS}
    if body.scenario not in known:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown scenario {body.scenario!r}. "
                   f"Available: {sorted(known)}",
        )

    # Delegate entirely to the existing orchestrator
    run_id = await start_run(scenario=body.scenario, seed=0)
    return {"run_id": run_id}


@app.get("/run/{run_id}/status", response_model=RunStatusResponse)
async def run_status(run_id: str) -> dict:
    """Return the current state and tick progress for a run."""
    row = get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    return {
        "state": row["state"],
        "tick":  row["current_tick"],
        "total": row["total_ticks"],
    }


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    """
    WebSocket endpoint.

    Frames emitted by the orchestrator:
        {"type": "tick",  "payload": {...}}
        {"type": "risk",  "payload": {...}}
        {"type": "case",  "payload": {...}}

    A client disconnect does NOT crash the orchestrator or other clients.
    """
    await hub.connect(websocket)
    try:
        # Drain incoming messages to keep the connection open.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        hub.disconnect(websocket)


@app.get("/risk/latest")
async def risk_latest(run_id: str) -> Any:
    """
    Return the most recent RiskAssessment for a run.

    Preserves the frozen RiskAssessment shape:
        run_id, window_start, window_end, group, risk_score,
        verdict, signals, counterfactual, evidence_hash, computed_ms
    """
    row = get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")

    assessment = get_latest_assessment(run_id)
    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail=f"No assessments yet for run {run_id!r}",
        )
    return assessment


@app.get("/cases")
async def cases_list(run_id: Optional[str] = None) -> list:
    """Return all cases, optionally filtered by run_id."""
    return list_cases(run_id)


@app.post("/case/open", status_code=201)
async def case_open(body: OpenCaseRequest) -> dict:
    """
    Open a case for a run/group.
    Attempts on-chain openCase; if Anvil is unavailable, opened_tx remains None.
    """
    row = get_run(body.run_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Run {body.run_id!r} not found"
        )

    opened_at_tick = row["current_tick"]

    local_id = str(uuid.uuid4())
    opened_tx = None
    try:
        from backend.chain import open_case as chain_open_case
        opened_tx = chain_open_case(
            evidence_hash=body.evidence_hash,
            risk_score=body.risk_score,
            group_ref=",".join(body.group),
            local_case_id=local_id,
        )
    except Exception as exc:
        logger.warning("Blockchain open_case failed during /case/open: %s", exc)

    case = create_case(
        run_id=body.run_id,
        group=body.group,
        risk_score=body.risk_score,
        evidence_hash=body.evidence_hash,
        opened_at_tick=opened_at_tick,
        opened_tx=opened_tx,
        case_id=local_id,
    )

    # Broadcast through the existing hub
    await hub.broadcast({"type": "case", "payload": case})
    return case


@app.post("/case/{case_id}/challenge")
async def case_challenge(case_id: str, body: ChallengeRequest) -> JSONResponse:
    """
    Challenge a flagged case.
    Verifies policy commitment and ECDSA signature.
    If valid -> resolves CLEARED.
    If invalid -> resolves ESCALATED.

    CRITICAL COMPLIANCE NOTE:
    CLEARED means ONLY that the submitted action was verified as compliant with
    the pre-committed execution policy. It does NOT prove absence of tacit coordination.
    """
    from backend.db import get_case as db_get_case, update_case as db_update_case
    from backend.challenge import verify_challenge
    from backend.chain import submit_challenge as chain_submit_challenge, resolve_case as chain_resolve_case

    case = db_get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")

    data = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    v_result = verify_challenge(data, case_group=case.get("group"))
    verdict = v_result["status"]  # "CLEARED" or "ESCALATED"
    explanation = v_result["explanation"]

    challenge_tx = None
    resolved_tx = None

    try:
        pc = body.policy_commitment or body.policy_hash or "0x" + "00" * 32
        challenge_tx = chain_submit_challenge(case_id=case_id, policy_commitment=pc)
        status_code = 2 if verdict == "CLEARED" else 3
        resolved_tx = chain_resolve_case(case_id=case_id, status=status_code)
    except Exception as exc:
        logger.warning("Blockchain challenge/resolve failed: %s", exc)

    db_update_case(
        case_id,
        status=verdict,
        challenge_tx=challenge_tx,
        resolved_tx=resolved_tx,
    )

    updated_case = db_get_case(case_id)
    if updated_case:
        await hub.broadcast({"type": "case", "payload": updated_case})

    return JSONResponse(
        status_code=200,
        content={
            "valid": verdict == "CLEARED",
            "tx_hash": resolved_tx or challenge_tx,
            "status": verdict,
            "case_id": case_id,
            "explanation": explanation,
            "challenge_tx": challenge_tx,
            "resolved_tx": resolved_tx,
        },
    )


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """
    Detector evaluation metrics.

    Not yet implemented — metrics aggregation belongs to a later stage.
    Do not invent TPR/FPR values here.
    """
    return JSONResponse(
        status_code=501,
        content={
            "detail": (
                "Metrics endpoint not yet implemented. "
                "Detector evaluation metrics are planned for a later stage."
            )
        },
    )


# ---------------------------------------------------------------------------
# Test-only helper route
# ---------------------------------------------------------------------------
# This route is intentionally left in for the test suite.  It lets tests
# trigger a hub.broadcast() from *inside* the server's event loop so that
# WS clients in the same Starlette TestClient portal can receive frames
# without any cross-event-loop synchronisation issues.

@app.post("/test/broadcast", include_in_schema=False)
async def test_broadcast(body: dict) -> dict:
    """Broadcast *body* through the hub (test helper; not part of the public API)."""
    await hub.broadcast(body)
    return {"ok": True}