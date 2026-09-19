r"""
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
    """Assessments: LOW, HIGH, HIGH → qualifying HIGH opens case, second HIGH does not duplicate."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    group = ["A2", "A3"]
    assessments_sequence = [
        _make_assessment(run_id, score=20, window_start=1,  window_end=4),   # LOW
        _make_assessment(run_id, score=80, window_start=5,  window_end=8),   # HIGH
        _make_assessment(run_id, score=90, window_start=9,  window_end=12),  # HIGH
    ]

    streaks: dict = {}
    seen_windows: set = set()
    for a in assessments_sequence:
        streaks, seen_windows = await orch._process_assessment(
            run_id, a, streaks, seen_windows
        )

    group_key = tuple(sorted(group))
    # A qualifying HIGH assessment opens 1 case; subsequent HIGH does not create duplicate
    cases = list_cases(run_id)
    assert len(cases) == 1
    assert cases[0]["risk_score"] == 80
    assert streaks.get(group_key, 0) == 2


# ── 12. Detector exception is caught; run does not crash ─────────────────────

@pytest.mark.asyncio
async def test_detector_exception_caught(fresh_run_id, mock_hub, caplog):
    """score_run() raising must not crash the run; error must be logged."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    def exploding_score_run(ticks, **kwargs):
        raise RuntimeError("detector exploded")

    with patch("backend.orchestrator.score_run", exploding_score_run):
        with caplog.at_level("ERROR"):
            await orch._run_pipeline(run_id, "default", 0)

    row = get_run(run_id)
    assert row["state"] == "done"
    assert "detector exploded" in caplog.text


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


# ===========================================================================
# 14–26. Integration-refactor: real-interface compatibility tests
# ===========================================================================

# ── T1. score_run is called with the complete tick list, not sub-windows ──────

@pytest.mark.asyncio
async def test_score_run_receives_full_tick_list(fresh_run_id, mock_hub):
    """score_run must receive the complete tick list, never a 4-tick slice."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    captured: list = []

    def capturing_score_run(ticks, **kwargs):
        captured.append(list(ticks))
        return iter([])

    with patch("backend.orchestrator.score_run", capturing_score_run):
        await orch._run_pipeline(run_id, "default", 0)

    assert len(captured) == 1, "score_run must be called exactly once"
    assert len(captured[0]) > 4, (
        f"score_run got only {len(captured[0])} ticks — expected the full stream"
    )


# ── T2. Multiple assessments per window are each persisted & broadcast ─────────

@pytest.mark.asyncio
async def test_multiple_assessments_per_window_all_processed(fresh_run_id, mock_hub):
    """If score_run yields 2 assessments (different groups) both must be saved."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    a1 = _make_assessment(run_id, score=50, window_start=1, window_end=4)
    a1["group"] = ["A1", "A2"]
    a2 = _make_assessment(run_id, score=60, window_start=1, window_end=4)
    a2["group"] = ["A2", "A3"]

    def two_assessment_score_run(ticks, **kwargs):
        return iter([a1, a2])

    with patch("backend.orchestrator.score_run", two_assessment_score_run):
        await orch._run_pipeline(run_id, "default", 0)

    db_rows = list_assessments(run_id)
    assert len(db_rows) == 2
    risk_msgs = [m for m in mock_hub._messages if m["type"] == "risk"]
    assert len(risk_msgs) == 2


# ── T3. Per-group streaks are independent ──────────────────────────────────────

@pytest.mark.asyncio
async def test_per_group_streaks_are_independent(fresh_run_id, mock_hub):
    """Group A reaching streak=3 must not open a case for Group B."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    # Group A2,A3: 3 consecutive HIGH → should open case
    # Group A1,A4: only LOW → should not open case
    def score_run_two_groups(ticks, **kwargs):
        for ws in [1, 5, 9]:
            a = _make_assessment(run_id, score=80, window_start=ws, window_end=ws+3)
            a["group"] = ["A2", "A3"]
            yield a
            b = _make_assessment(run_id, score=20, window_start=ws, window_end=ws+3)
            b["group"] = ["A1", "A4"]
            b["evidence_hash"] = "0x" + "bb" * 32
            yield b

    with patch("backend.orchestrator.score_run", score_run_two_groups):
        await orch._run_pipeline(run_id, "default", 0)

    cases = list_cases(run_id)
    # Only group ["A2","A3"] should have a case
    assert len(cases) == 1
    assert sorted(cases[0]["group"]) == ["A2", "A3"]


# ── T4. Streak advances only for the same group in successive windows ──────────

@pytest.mark.asyncio
async def test_streak_advances_only_for_same_group(fresh_run_id, mock_hub):
    """Alternating groups in different windows advance their respective streaks independently."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    streaks: dict = {}
    seen_windows: set = set()

    # Window 1: group A2,A3 HIGH
    a1 = _make_assessment(run_id, score=80, window_start=1, window_end=4)
    streaks, seen_windows = await orch._process_assessment(run_id, a1, streaks, seen_windows)

    # Window 2: group A1,A4 HIGH (different group)
    a2 = _make_assessment(run_id, score=80, window_start=5, window_end=8)
    a2["group"] = ["A1", "A4"]
    streaks, seen_windows = await orch._process_assessment(run_id, a2, streaks, seen_windows)

    # Window 3: group A2,A3 HIGH again
    a3 = _make_assessment(run_id, score=80, window_start=9, window_end=12)
    streaks, seen_windows = await orch._process_assessment(run_id, a3, streaks, seen_windows)

    assert streaks.get(("A2", "A3"), 0) == 2   # only windows 1 and 3 for this group
    assert streaks.get(("A1", "A4"), 0) == 1


# ── T5. Different groups same window don't share streak ────────────────────────

@pytest.mark.asyncio
async def test_different_groups_same_window_independent_streak(fresh_run_id, mock_hub):
    """Two assessments with same window_start but different groups counted independently."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    streaks: dict = {}
    seen_windows: set = set()

    a1 = _make_assessment(run_id, score=80, window_start=1, window_end=4)
    a1["group"] = ["A1", "A2"]
    a2 = _make_assessment(run_id, score=20, window_start=1, window_end=4)
    a2["group"] = ["A3", "A4"]
    a2["evidence_hash"] = "0x" + "cc" * 32

    for a in [a1, a2]:
        streaks, seen_windows = await orch._process_assessment(run_id, a, streaks, seen_windows)

    assert streaks.get(("A1", "A2"), 0) == 1
    assert streaks.get(("A3", "A4"), 0) == 0


# ── T6. Case opened per group, not globally ────────────────────────────────────

@pytest.mark.asyncio
async def test_case_opened_per_group(fresh_run_id, mock_hub):
    """Each distinct group that triggers the case rule gets its own case."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    def score_run_two_groups_three_highs(ticks, **kwargs):
        for ws in [1, 5, 9]:
            a = _make_assessment(run_id, score=80, window_start=ws, window_end=ws+3)
            a["group"] = ["A2", "A3"]
            yield a
            b = _make_assessment(run_id, score=80, window_start=ws, window_end=ws+3)
            b["group"] = ["A1", "A4"]
            b["evidence_hash"] = "0x" + "dd" * 32
            yield b

    with patch("backend.orchestrator.score_run", score_run_two_groups_three_highs):
        await orch._run_pipeline(run_id, "default", 0)

    cases = list_cases(run_id)
    groups_in_cases = {tuple(sorted(c["group"])) for c in cases}
    assert ("A2", "A3") in groups_in_cases
    assert ("A1", "A4") in groups_in_cases
    assert len(cases) == 2


# ── T7. Case not re-opened if already open for same group ─────────────────────

@pytest.mark.asyncio
async def test_case_not_reopened_for_same_group(fresh_run_id, mock_hub):
    """After a case is opened for a group, further HIGH windows must not open another."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    def six_highs(ticks, **kwargs):
        for ws in [1, 5, 9, 13, 17, 21]:
            yield _make_assessment(run_id, score=85, window_start=ws, window_end=ws+3)

    with patch("backend.orchestrator.score_run", six_highs):
        await orch._run_pipeline(run_id, "default", 0)

    cases = list_cases(run_id)
    assert len(cases) == 1


# ── T8. Low score for group A resets only group A streak ──────────────────────

@pytest.mark.asyncio
async def test_low_score_resets_only_own_group(fresh_run_id, mock_hub):
    """A LOW assessment for group A resets only A's streak, not group B's."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    streaks: dict = {}
    seen_windows: set = set()

    # Both groups reach streak=2
    for ws in [1, 5]:
        a = _make_assessment(run_id, score=80, window_start=ws, window_end=ws+3)
        a["group"] = ["A2", "A3"]
        streaks, seen_windows = await orch._process_assessment(run_id, a, streaks, seen_windows)
        b = _make_assessment(run_id, score=80, window_start=ws, window_end=ws+3)
        b["group"] = ["A1", "A4"]
        b["evidence_hash"] = "0x" + "ee" * 32
        streaks, seen_windows = await orch._process_assessment(run_id, b, streaks, seen_windows)

    # LOW for group A2,A3 only
    reset = _make_assessment(run_id, score=30, window_start=9, window_end=12)
    reset["group"] = ["A2", "A3"]
    streaks, seen_windows = await orch._process_assessment(run_id, reset, streaks, seen_windows)

    assert streaks.get(("A2", "A3"), 0) == 0   # A2,A3 reset
    assert streaks.get(("A1", "A4"), 0) == 2   # A1,A4 untouched


# ── T9. All ticks are broadcast before assessments ────────────────────────────

@pytest.mark.asyncio
async def test_all_ticks_broadcast_before_risk_frames(fresh_run_id, mock_hub):
    """Phase 1 (ticks) completes entirely before Phase 3 (risk) starts."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    a = _make_assessment(run_id, score=50, window_start=1, window_end=4)

    def one_assessment(ticks, **kwargs):
        return iter([a])

    with patch("backend.orchestrator.score_run", one_assessment):
        await orch._run_pipeline(run_id, "default", 0)

    msgs = mock_hub._messages
    tick_indices = [i for i, m in enumerate(msgs) if m["type"] == "tick"]
    risk_indices = [i for i, m in enumerate(msgs) if m["type"] == "risk"]
    if tick_indices and risk_indices:
        assert max(tick_indices) < min(risk_indices), (
            "All tick frames must be broadcast before any risk frames"
        )


# ── T10. total_ticks is updated after collection ──────────────────────────────

@pytest.mark.asyncio
async def test_total_ticks_updated(fresh_run_id, mock_hub):
    """After _run_pipeline completes, total_ticks must equal ticks emitted."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    with patch("backend.orchestrator.score_run", return_value=iter([])):
        await orch._run_pipeline(run_id, "default", 0)

    row = get_run(run_id)
    assert row["total_ticks"] > 0


# ── T11. Detector exception: run completes; ticks already broadcast ────────────

@pytest.mark.asyncio
async def test_detector_exception_ticks_still_broadcast(fresh_run_id, mock_hub, caplog):
    """Even when score_run raises, ticks must be broadcast before failure."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    def exploding(ticks, **kwargs):
        raise RuntimeError("boom in detector")

    with patch("backend.orchestrator.score_run", exploding):
        with caplog.at_level("ERROR"):
            await orch._run_pipeline(run_id, "default", 0)

    row = get_run(run_id)
    assert row["state"] == "done"
    tick_msgs = [m for m in mock_hub._messages if m["type"] == "tick"]
    assert len(tick_msgs) > 0


# ── T12. score_run called exactly once with the full list ─────────────────────

@pytest.mark.asyncio
async def test_score_run_called_exactly_once(fresh_run_id, mock_hub):
    """score_run must be called exactly once per pipeline run."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    call_count = {"n": 0}

    def counting_score_run(ticks, **kwargs):
        call_count["n"] += 1
        return iter([])

    with patch("backend.orchestrator.score_run", counting_score_run):
        await orch._run_pipeline(run_id, "default", 0)

    assert call_count["n"] == 1


# ── T13. Window dedup: same group+window_start doesn't double-count streak ─────

@pytest.mark.asyncio
async def test_window_dedup_prevents_double_streak(fresh_run_id, mock_hub):
    """Two assessments with same group and window_start must count as one."""
    run_id = fresh_run_id
    create_run(run_id, "default", 0)

    streaks: dict = {}
    seen_windows: set = set()

    a1 = _make_assessment(run_id, score=80, window_start=1, window_end=4)
    a2 = _make_assessment(run_id, score=80, window_start=1, window_end=4)  # duplicate window

    for a in [a1, a2]:
        streaks, seen_windows = await orch._process_assessment(
            run_id, a, streaks, seen_windows
        )

    # Must only count as 1, not 2
    assert streaks.get(("A2", "A3"), 0) == 1