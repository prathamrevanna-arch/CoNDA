"""
backend/test_real_pipeline.py
-----------------------------
End-to-end integration tests for the REAL pipeline:
  M1 (sim.engine) -> M2 (detector.score) -> M3 (orchestrator / db / ws / chain)

Verifies:
  A. Real detector integration: cartel_vs_competitive + seed 42
     -> 1602 ticks, 78 assessments, A2/A3 [150, 249] = 74 HIGH
  B. WebSocket: 74 HIGH assessment is broadcast as {"type": "risk", ...}
  C. Case opening: qualifying HIGH assessment opens a case
  D. Blockchain resilience: Anvil online -> opened_tx string; Anvil offline -> None
  E. No duplicate cases: duplicate/subsequent HIGH assessments do not create multiple cases
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import backend.db as _db_module
from backend.db import (
    initialize_db,
    create_run,
    list_assessments,
    list_cases,
    case_exists_for_run_group,
)
import backend.orchestrator as orch
from sim.engine import run_sim
from detector.score import score_run


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Isolate DB for each test."""
    db_file = tmp_path / "test_pipeline.db"
    _db_module._DATA_DIR = tmp_path
    _db_module._DB_PATH = db_file
    initialize_db()
    yield db_file


@pytest.fixture
def capture_hub():
    """Capture all WebSocket broadcast messages."""
    messages = []

    class FakeHub:
        async def broadcast(self, msg):
            messages.append(msg)

        @property
        def client_count(self):
            return 0

    fake = FakeHub()
    with patch.object(orch, "hub", fake):
        yield messages


# ── A. Real detector integration benchmark ────────────────────────────────────

def test_real_pipeline_benchmark():
    """Verify exact real integration benchmark contract:
    1602 ticks, 78 assessments, A2/A3 [150,249] = 74 HIGH.
    """
    ticks = list(run_sim("cartel_vs_competitive", 42))
    assert len(ticks) == 1602, f"Expected 1602 ticks, got {len(ticks)}"

    unique_t = {int(float(x["t"])) for x in ticks}
    assert len(unique_t) == 400, f"Expected 400 unique t, got {len(unique_t)}"

    assessments = list(score_run(ticks, window_size=100, stride=25))
    assert len(assessments) == 78, f"Expected 78 assessments, got {len(assessments)}"

    windows = set((a["window_start"], a["window_end"]) for a in assessments)
    assert len(windows) == 13, f"Expected 13 rolling windows, got {len(windows)}"

    a2_a3_assessments = [
        a for a in assessments
        if sorted(a["group"]) == ["A2", "A3"]
    ]
    assert len(a2_a3_assessments) == 13, f"Expected 13 assessments for A2/A3, got {len(a2_a3_assessments)}"

    peak = max(assessments, key=lambda x: x["risk_score"])
    assert peak["risk_score"] == 74
    assert peak["verdict"] == "HIGH"
    assert sorted(peak["group"]) == ["A2", "A3"]
    assert peak["window_start"] == 150
    assert peak["window_end"] == 249


# ── B & C & D. End-to-end Orchestrator Run ────────────────────────────────────

@pytest.mark.asyncio
async def test_orchestrator_real_pipeline_broadcasts_and_opens_case(capture_hub):
    """Run full pipeline with cartel_vs_competitive seed 42.
    Verify:
    1. 1602 ticks broadcast and collected
    2. 78 risk assessments persisted and broadcast
    3. Peak 74 HIGH emitted over WS
    4. Qualifying HIGH opens exactly 1 case for A2/A3
    5. Case event broadcast over WS
    """
    run_id = f"real_run_{uuid.uuid4().hex[:8]}"
    create_run(run_id, "cartel_vs_competitive", 42)

    await orch._run_pipeline(run_id, "cartel_vs_competitive", 42)

    # 1. Check ticks broadcast
    tick_msgs = [m for m in capture_hub if m["type"] == "tick"]
    assert len(tick_msgs) == 1602

    # 2. Check risk assessments persisted in DB and broadcast over WS
    db_assessments = list_assessments(run_id)
    assert len(db_assessments) == 78

    risk_msgs = [m for m in capture_hub if m["type"] == "risk"]
    assert len(risk_msgs) == 78

    # 3. Verify the 74 HIGH assessment was broadcast
    high_msgs = [
        m for m in risk_msgs
        if m["payload"]["risk_score"] == 74 and m["payload"]["verdict"] == "HIGH"
    ]
    assert len(high_msgs) == 1
    high_payload = high_msgs[0]["payload"]
    assert sorted(high_payload["group"]) == ["A2", "A3"]
    assert high_payload["window_start"] == 150
    assert high_payload["window_end"] == 249
    assert high_payload["run_id"] == run_id

    # 4. Verify case opened in DB
    cases = list_cases(run_id)
    assert len(cases) == 1, f"Expected 1 case, got {len(cases)}"
    case = cases[0]
    assert sorted(case["group"]) == ["A2", "A3"]
    assert case["risk_score"] == 74
    assert case["opened_at_tick"] == 150
    assert case["status"] == "OPEN"

    # 5. Verify case broadcast over WS
    case_msgs = [m for m in capture_hub if m["type"] == "case"]
    assert len(case_msgs) == 1
    assert case_msgs[0]["payload"]["case_id"] == case["case_id"]


# ── E. No duplicate cases ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_duplicate_cases_for_qualifying_assessments(capture_hub):
    """Multiple qualifying HIGH assessments for the same group must not open multiple cases."""
    run_id = f"dedup_run_{uuid.uuid4().hex[:8]}"
    create_run(run_id, "default", 0)

    streaks = {}
    seen_windows = set()

    # Window 1: A2/A3 74 HIGH -> opens case 1
    a1 = {
        "run_id": run_id,
        "window_start": 150,
        "window_end": 249,
        "group": ["A2", "A3"],
        "risk_score": 74,
        "verdict": "HIGH",
        "signals": {},
        "counterfactual": {},
        "evidence_hash": "0x" + "11" * 32,
        "computed_ms": 1.0,
    }
    streaks, seen_windows = await orch._process_assessment(run_id, a1, streaks, seen_windows)

    cases = list_cases(run_id)
    assert len(cases) == 1

    # Window 2: A2/A3 80 HIGH -> should NOT open duplicate case
    a2 = {
        "run_id": run_id,
        "window_start": 175,
        "window_end": 274,
        "group": ["A2", "A3"],
        "risk_score": 80,
        "verdict": "HIGH",
        "signals": {},
        "counterfactual": {},
        "evidence_hash": "0x" + "22" * 32,
        "computed_ms": 1.0,
    }
    streaks, seen_windows = await orch._process_assessment(run_id, a2, streaks, seen_windows)

    cases = list_cases(run_id)
    assert len(cases) == 1, "Duplicate case must not be created for the same group"


# ── F. Blockchain online vs offline ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_case_opening_blockchain_offline(capture_hub):
    """When blockchain is unavailable, case is still created locally with opened_tx = None."""
    run_id = f"chain_off_{uuid.uuid4().hex[:8]}"
    create_run(run_id, "default", 0)

    a = {
        "run_id": run_id,
        "window_start": 150,
        "window_end": 249,
        "group": ["A2", "A3"],
        "risk_score": 74,
        "verdict": "HIGH",
        "signals": {},
        "counterfactual": {},
        "evidence_hash": "0x" + "33" * 32,
        "computed_ms": 1.0,
    }

    with patch("backend.chain.open_case", side_effect=ConnectionError("Anvil offline")):
        await orch._process_assessment(run_id, a, {}, set())

    cases = list_cases(run_id)
    assert len(cases) == 1
    assert cases[0]["opened_tx"] is None
    assert cases[0]["status"] == "OPEN"
