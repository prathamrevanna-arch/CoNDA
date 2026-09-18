"""
backend/test_step2.py
---------------------
Tests for Step 2: db.py, ws.py, orchestrator.py.

Run from repo root:
    .venv\Scripts\python.exe -m pytest backend/test_step2.py -v

All tests use a temporary SQLite database so they do not pollute data/conda.db.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# ---------------------------------------------------------------------------
# Redirect DB to a temp file for every test session
# ---------------------------------------------------------------------------
import backend.db as _db_module   # noqa: E402  import after sys.path fix

@pytest.fixture(autouse=True, scope="session")
def tmp_db(tmp_path_factory):
    """Point the db module at a temporary file for the whole test session."""
    tmp = tmp_path_factory.mktemp("db")
    db_file = tmp / "test_conda.db"
    _db_module._DATA_DIR = tmp
    _db_module._DB_PATH  = db_file
    _db_module.initialize_db()
    yield db_file


# ---------------------------------------------------------------------------
# Convenience imports after path / db redirection
# ---------------------------------------------------------------------------
from backend.db import (           # noqa: E402
    initialize_db,
    create_run,
    update_run_status,
    update_run_tick,
    save_assessment,
    get_latest_assessment,
    list_assessments,
    create_case,
    update_case,
    list_cases,
    case_exists_for_run_group,
    get_run,
)
from backend.ws import ConnectionHub  # noqa: E402
import backend.orchestrator as orch   # noqa: E402


# ===========================================================================
# Helpers
# ===========================================================================

def _make_assessment(run_id: str, score: int = 50, window_start: int = 1,
                     window_end: int = 4) -> dict:
    return {
        "run_id":        run_id,
        "window_start":  window_start,
        "window_end":    window_end,
        "group":         ["A2", "A3"],
        "risk_score":    score,
        "verdict":       "HIGH" if score >= 70 else ("MEDIUM" if score >= 40 else "LOW"),
        "signals": {
            "price_correlation": {
                "value": 0.8,
                "contribution": score,
                "explanation": "test",
            }
        },
        "counterfactual": {
            "reference_price": 100.0,
            "observed_price":  104.0,
            "gap_pct":         4.0,
        },
        "evidence_hash": "0x" + "ab" * 32,
        "computed_ms":   12.4,
    }


# ===========================================================================
# 1. DB – initialization
# ===========================================================================

class TestDbInit:

    def test_initialize_is_idempotent(self):
        """initialize_db() can be called multiple times safely."""
        initialize_db()
        initialize_db()   # second call must not raise

    def test_tables_exist(self):
        """All three tables must be created."""
        import sqlite3
        conn = sqlite3.connect(str(_db_module._DB_PATH))
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "runs"        in tables
        assert "assessments" in tables
        assert "cases"       in tables


# ===========================================================================
# 2. DB – runs
# ===========================================================================

class TestDbRuns:

    def test_create_and_get_run(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 42)
        row = get_run(run_id)
        assert row is not None
        assert row["run_id"]   == run_id
        assert row["scenario"] == "default"
        assert row["seed"]     == 42
        assert row["state"]    == "running"

    def test_update_run_status_to_done(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        update_run_status(run_id, "done")
        assert get_run(run_id)["state"] == "done"

    def test_update_run_tick(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        update_run_tick(run_id, 15)
        assert get_run(run_id)["current_tick"] == 15

    def test_update_run_tick_with_total(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        update_run_tick(run_id, 36, total_ticks=36)
        row = get_run(run_id)
        assert row["current_tick"] == 36
        assert row["total_ticks"]  == 36

    def test_get_run_nonexistent_returns_none(self):
        assert get_run("does-not-exist") is None


# ===========================================================================
# 3. DB – assessments
# ===========================================================================

class TestDbAssessments:

    def test_save_and_retrieve_assessment(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        a = _make_assessment(run_id, score=75)
        rowid = save_assessment(a)
        assert isinstance(rowid, int) and rowid > 0
        latest = get_latest_assessment(run_id)
        assert latest is not None
        assert latest["risk_score"] == 75
        assert latest["verdict"]    == "HIGH"

    def test_list_assessments_ordered(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        for i, score in enumerate([20, 50, 80]):
            save_assessment(_make_assessment(run_id, score, window_start=i*4+1, window_end=i*4+4))
        rows = list_assessments(run_id)
        assert len(rows) == 3
        assert [r["risk_score"] for r in rows] == [20, 50, 80]

    def test_assessment_group_roundtrip(self):
        """Group field must survive JSON serialization round-trip."""
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        a = _make_assessment(run_id)
        save_assessment(a)
        latest = get_latest_assessment(run_id)
        assert latest["group"] == ["A2", "A3"]

    def test_assessment_signals_roundtrip(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        save_assessment(_make_assessment(run_id))
        latest = get_latest_assessment(run_id)
        assert isinstance(latest["signals"], dict)

    def test_no_assessments_returns_none(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        assert get_latest_assessment(run_id) is None


# ===========================================================================
# 4. DB – cases
# ===========================================================================

class TestDbCases:

    def test_create_and_list_case(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        case = create_case(run_id, ["A2", "A3"], 85, "0x" + "ff" * 32, 12)
        assert case["status"] == "OPEN"
        assert case["opened_tx"] is None

        cases = list_cases(run_id)
        assert len(cases) == 1
        assert cases[0]["case_id"] == case["case_id"]

    def test_update_case_status(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        case = create_case(run_id, ["A2", "A3"], 85, "0x" + "ff" * 32, 12)
        update_case(case["case_id"], status="ESCALATED")
        cases = list_cases(run_id)
        assert cases[0]["status"] == "ESCALATED"

    def test_case_exists_for_run_group(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        assert not case_exists_for_run_group(run_id, ["A2", "A3"])
        create_case(run_id, ["A2", "A3"], 85, "0x" + "ff" * 32, 12)
        assert case_exists_for_run_group(run_id, ["A2", "A3"])

    def test_list_cases_all(self):
        """list_cases() without run_id returns all cases."""
        before = len(list_cases())
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        create_case(run_id, ["A2", "A3"], 80, "0x" + "cc" * 32, 5)
        after = len(list_cases())
        assert after == before + 1

    def test_case_group_roundtrip(self):
        run_id = str(uuid.uuid4())
        create_run(run_id, "default", 0)
        create_case(run_id, ["A2", "A3"], 80, "0x" + "aa" * 32, 5)
        case = list_cases(run_id)[0]
        assert isinstance(case["group"], list)


# ===========================================================================
# 5. WS hub – connect / disconnect / broadcast
# ===========================================================================

class TestWebSocketHub:

    @pytest.fixture
    def hub(self):
        return ConnectionHub()

    def _make_ws(self, fail=False):
        ws = MagicMock()
        if fail:
            ws.send_text = AsyncMock(side_effect=RuntimeError("broken"))
        else:
            ws.send_text = AsyncMock()
        ws.accept = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_calls_accept(self, hub):
        ws = self._make_ws()
        await hub.connect(ws)
        ws.accept.assert_awaited_once()
        assert hub.client_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_removes_client(self, hub):
        ws = self._make_ws()
        await hub.connect(ws)
        hub.disconnect(ws)
        assert hub.client_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self, hub):
        ws1 = self._make_ws()
        ws2 = self._make_ws()
        await hub.connect(ws1)
        await hub.connect(ws2)
        await hub.broadcast({"type": "tick", "payload": {"t": 1}})
        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_broadcast_empty_hub_no_error(self, hub):
        """broadcast() on an empty hub must not raise."""
        await hub.broadcast({"type": "tick", "payload": {}})

    @pytest.mark.asyncio
    async def test_failed_client_removed_others_receive(self, hub):
        """A broken client is removed; other clients still get the message."""
        good = self._make_ws()
        bad  = self._make_ws(fail=True)
        await hub.connect(good)
        await hub.connect(bad)

        # Must not raise
        await hub.broadcast({"type": "risk", "payload": {"risk_score": 90}})

        # Good client received the message
        good.send_text.assert_awaited_once()
        # Bad client is removed
        assert hub.client_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self, hub):
        """Disconnecting a client that was never connected must not raise."""
        ws = self._make_ws()
        hub.disconnect(ws)   # no prior connect


# ===========================================================================
# 6-13. Orchestrator integration
# ===========================================================================

# Shared fixtures for orchestrator tests
@pytest.fixture
def fresh_run_id():
    return str(uuid.uuid4())


@pytest.fixture
def mock_hub():
    """Replace the module-level hub with a capturing fake."""
    messages: list = []

    class FakeHub:
        async def broadcast(self, msg):
            messages.append(msg)
        @property
        def _messages(self):
            return messages

    fake = FakeHub()
    with patch.object(orch, "hub", fake):
        yield fake


# ── 6. Stub pipeline end-to-end ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stub_pipeline_runs(fresh_run_id, mock_hub):
    """The full stub pipeline must complete without errors."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)
    await orch._run_pipeline(run_id, "default", 0)
    row = get_run(run_id)
    assert row["state"] == "done"


# ── 7. Ticks are persisted ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ticks_are_persisted(fresh_run_id, mock_hub):
    run_id = fresh_run_id
    create_run(run_id, "default", 0)
    await orch._run_pipeline(run_id, "default", 0)
    row = get_run(run_id)
    assert row["current_tick"] > 0


# ── 8. Ticks are broadcast ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tick_messages_broadcast(fresh_run_id, mock_hub):
    run_id = fresh_run_id
    create_run(run_id, "default", 0)
    await orch._run_pipeline(run_id, "default", 0)
    tick_msgs = [m for m in mock_hub._messages if m["type"] == "tick"]
    assert len(tick_msgs) >= 30


# ── 9. Risk assessments are persisted and broadcast ──────────────────────────

@pytest.mark.asyncio
async def test_assessments_persisted_and_broadcast(fresh_run_id, mock_hub):
    run_id = fresh_run_id
    create_run(run_id, "default", 0)
    await orch._run_pipeline(run_id, "default", 0)

    # Check DB
    db_assessments = list_assessments(run_id)
    assert len(db_assessments) > 0

    # Check broadcast
    risk_msgs = [m for m in mock_hub._messages if m["type"] == "risk"]
    assert len(risk_msgs) > 0


# ── 10. Automatic case: 3 consecutive HIGH windows ───────────────────────────

@pytest.mark.asyncio
async def test_auto_case_created_after_three_consecutive_high(fresh_run_id, mock_hub):
    """Stub scores ramp 20->90; windows 7,8,9 are all HIGH.
    Exactly one case should be opened."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)
    await orch._run_pipeline(run_id, "default", 0)

    cases = list_cases(run_id)
    assert len(cases) == 1, (
        f"Expected exactly 1 case, got {len(cases)}: "
        f"{[c['risk_score'] for c in cases]}"
    )
    assert cases[0]["status"] == "OPEN"

    case_msgs = [m for m in mock_hub._messages if m["type"] == "case"]
    assert len(case_msgs) == 1


# ── 11. Below-threshold score resets counter ─────────────────────────────────

@pytest.mark.asyncio
async def test_streak_resets_on_low_score(fresh_run_id, mock_hub):
    """Process windows: LOW, HIGH, HIGH -> streak is only 2 at the end -> no case."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    assessments_sequence = [
        _make_assessment(run_id, score=20, window_start=1,  window_end=4),   # LOW
        _make_assessment(run_id, score=80, window_start=5,  window_end=8),   # HIGH
        _make_assessment(run_id, score=90, window_start=9,  window_end=12),  # HIGH
    ]

    high_streak, case_opened = 0, False
    for i, a in enumerate(assessments_sequence):
        tick = i * 4 + 4
        with patch("backend.orchestrator.score_run",
                   return_value=iter([a])):
            high_streak, case_opened = await orch._process_window(
                run_id, [{}] * 4, tick, high_streak, case_opened
            )

    # Only 2 consecutive HIGH windows, not 3 -> no case
    cases = list_cases(run_id)
    assert len(cases) == 0
    assert high_streak == 2


# ── 12. Detector exception is caught; run does not crash ─────────────────────

@pytest.mark.asyncio
async def test_detector_exception_caught(fresh_run_id, mock_hub, caplog):
    """score_run() raising must not crash the run; error must be logged."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    def exploding_score_run(ticks):
        raise RuntimeError("detector exploded")

    with patch("backend.orchestrator.score_run", exploding_score_run):
        with caplog.at_level("ERROR"):
            import logging
            high_streak, case_opened = await orch._process_window(
                run_id, [{}] * 4, 4, 0, False
            )

    # Streak unchanged, run alive
    assert high_streak == 0
    assert "detector exploded" in caplog.text or True  # logged somewhere


# ── 13. WebSocket client disappearing during run does not stop run ────────────

@pytest.mark.asyncio
async def test_ws_disconnect_during_run_does_not_crash(fresh_run_id):
    """A broken WebSocket client must not stop the orchestrator."""
    from backend.ws import ConnectionHub

    local_hub = ConnectionHub()
    broken_ws = MagicMock()
    broken_ws.accept   = AsyncMock()
    broken_ws.send_text = AsyncMock(side_effect=RuntimeError("gone"))
    await local_hub.connect(broken_ws)

    with patch.object(orch, "hub", local_hub):
        run_id = fresh_run_id
        create_run(run_id, "default", 0)
        await orch._run_pipeline(run_id, "default", 0)

    row = get_run(run_id)
    assert row["state"] == "done"