r"""
backend/test_main.py
--------------------
Step 3 tests for backend/main.py (FastAPI routes).

Run from repo root:
    .venv\Scripts\python.exe -m pytest backend/test_main.py -v

Uses FastAPI TestClient (httpx-based, synchronous) for HTTP tests and
a real async event loop for the WebSocket test.
"""

from __future__ import annotations

import sys
import uuid
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# sys.path — make "backend" importable from repo root
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# ---------------------------------------------------------------------------
# Redirect DB to a temp file so tests never touch data/conda.db
# ---------------------------------------------------------------------------
import backend.db as _db_module

@pytest.fixture(autouse=True, scope="session")
def tmp_db(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("db_main")
    _db_module._DATA_DIR = tmp
    _db_module._DB_PATH  = tmp / "test_main.db"
    _db_module.initialize_db()
    yield


# ---------------------------------------------------------------------------
# TestClient — import after tmp_db redirection so the app sees the temp DB
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app, raise_server_exceptions=False)


# ===========================================================================
# 1–3: /health
# ===========================================================================

class TestHealth:

    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_reports_detector_stub(self):
        r = client.get("/health")
        assert r.json()["detector"] == "stub"

    def test_health_chain_false_without_anvil(self):
        """chain must be False — blockchain not integrated yet."""
        r = client.get("/health")
        data = r.json()
        assert data["ok"] is True
        assert data["chain"] is False

    def test_health_does_not_require_anvil(self):
        """App must start and /health must succeed with no blockchain."""
        r = client.get("/health")
        assert r.status_code == 200


# ===========================================================================
# 4: /scenarios
# ===========================================================================

class TestScenarios:

    def test_scenarios_returns_200(self):
        r = client.get("/scenarios")
        assert r.status_code == 200

    def test_scenarios_is_list(self):
        r = client.get("/scenarios")
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_scenarios_item_has_id_and_label(self):
        r = client.get("/scenarios")
        for item in r.json():
            assert "id"    in item
            assert "label" in item

    def test_scenarios_contains_default(self):
        r = client.get("/scenarios")
        ids = [s["id"] for s in r.json()]
        assert "default" in ids


# ===========================================================================
# 5–6: POST /run/start
# ===========================================================================

class TestRunStart:

    def test_run_start_returns_run_id(self):
        # Patch start_run to avoid spawning a real simulation task
        with patch("backend.main.start_run", new=AsyncMock(return_value="test-run-001")):
            r = client.post("/run/start", json={"scenario": "default"})
        assert r.status_code == 202
        assert "run_id" in r.json()
        assert r.json()["run_id"] == "test-run-001"

    def test_run_start_does_not_block(self):
        """POST /run/start must return before the simulation finishes."""
        import time
        with patch("backend.main.start_run", new=AsyncMock(return_value="quick-id")):
            t0 = time.monotonic()
            r = client.post("/run/start", json={"scenario": "default"})
            elapsed = time.monotonic() - t0
        assert r.status_code == 202
        # Should return in well under 1 second (stub has 36*50ms = 1.8s total)
        assert elapsed < 1.0

    def test_run_start_unknown_scenario_422(self):
        r = client.post("/run/start", json={"scenario": "nonexistent_xyz"})
        assert r.status_code == 422


# ===========================================================================
# 7–8: GET /run/{id}/status
# ===========================================================================

class TestRunStatus:

    def _make_run(self) -> str:
        run_id = str(uuid.uuid4())
        _db_module.create_run(run_id, "default", 0)
        return run_id

    def test_run_status_returns_state_and_tick(self):
        run_id = self._make_run()
        r = client.get(f"/run/{run_id}/status")
        assert r.status_code == 200
        data = r.json()
        assert "state" in data
        assert "tick"  in data
        assert "total" in data

    def test_run_status_initial_state_running(self):
        run_id = self._make_run()
        r = client.get(f"/run/{run_id}/status")
        assert r.json()["state"] == "running"

    def test_run_status_done_after_update(self):
        run_id = self._make_run()
        _db_module.update_run_status(run_id, "done")
        r = client.get(f"/run/{run_id}/status")
        assert r.json()["state"] == "done"

    def test_run_status_nonexistent_404(self):
        r = client.get("/run/does-not-exist-ever/status")
        assert r.status_code == 404


# ===========================================================================
# 9–10: GET /risk/latest
# ===========================================================================

class TestRiskLatest:

    def _make_assessment(self, run_id: str, score: int = 75) -> dict:
        a = {
            "run_id":        run_id,
            "window_start":  1,
            "window_end":    4,
            "group":         ["A2", "A3"],
            "risk_score":    score,
            "verdict":       "HIGH",
            "signals":       {"x": {"value": 0.9, "contribution": 50, "explanation": "t"}},
            "counterfactual": {"reference_price": 100.0, "observed_price": 104.0, "gap_pct": 4.0},
            "evidence_hash": "0x" + "ab" * 32,
            "computed_ms":   12.4,
        }
        _db_module.save_assessment(a)
        return a

    def test_risk_latest_returns_assessment(self):
        run_id = str(uuid.uuid4())
        _db_module.create_run(run_id, "default", 0)
        self._make_assessment(run_id, 80)
        r = client.get(f"/risk/latest?run_id={run_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["risk_score"] == 80
        assert data["verdict"]    == "HIGH"

    def test_risk_latest_has_all_required_fields(self):
        run_id = str(uuid.uuid4())
        _db_module.create_run(run_id, "default", 0)
        self._make_assessment(run_id)
        r = client.get(f"/risk/latest?run_id={run_id}")
        data = r.json()
        for field in ("run_id", "window_start", "window_end", "group",
                      "risk_score", "verdict", "signals", "counterfactual",
                      "evidence_hash", "computed_ms"):
            assert field in data, f"Missing field: {field}"

    def test_risk_latest_nonexistent_run_404(self):
        r = client.get("/risk/latest?run_id=no-such-run")
        assert r.status_code == 404

    def test_risk_latest_run_with_no_assessments_404(self):
        run_id = str(uuid.uuid4())
        _db_module.create_run(run_id, "default", 0)
        r = client.get(f"/risk/latest?run_id={run_id}")
        assert r.status_code == 404


# ===========================================================================
# 11: GET /cases
# ===========================================================================

class TestCasesList:

    def test_cases_returns_list(self):
        r = client.get("/cases")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_cases_filtered_by_run_id(self):
        run_id = str(uuid.uuid4())
        _db_module.create_run(run_id, "default", 0)
        _db_module.create_case(run_id, ["A2", "A3"], 85, "0x" + "ff" * 32, 12)

        r = client.get(f"/cases?run_id={run_id}")
        data = r.json()
        assert len(data) >= 1
        assert all(c["run_id"] == run_id for c in data)


# ===========================================================================
# 12: POST /case/open
# ===========================================================================

class TestCaseOpen:

    def test_case_open_creates_case(self):
        run_id = str(uuid.uuid4())
        _db_module.create_run(run_id, "default", 0)
        payload = {
            "run_id":       run_id,
            "group":        ["A2", "A3"],
            "risk_score":   85,
            "evidence_hash": "0x" + "aa" * 32,
        }
        r = client.post("/case/open", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["status"]      == "OPEN"
        assert data["opened_tx"]   is None
        assert data["challenge_tx"] is None
        assert data["resolved_tx"] is None

    def test_case_open_nonexistent_run_404(self):
        payload = {
            "run_id":       "no-such-run",
            "group":        ["A2"],
            "risk_score":   80,
            "evidence_hash": "0x" + "bb" * 32,
        }
        r = client.post("/case/open", json=payload)
        assert r.status_code == 404


# ===========================================================================
# 13–17: WebSocket /ws/live
# ===========================================================================

class TestWebSocket:

    def test_ws_accepts_connection(self):
        with client.websocket_connect("/ws/live") as ws:
            # Connection accepted; send a ping to confirm it is alive
            ws.send_text("ping")

    def test_ws_receives_tick_frame_from_hub(self):
        """Hub broadcasts a tick frame; WS client receives it.

        We trigger the broadcast via a dedicated /test/broadcast route (added
        to main.py for testing only) so hub.broadcast() runs inside the
        server's event loop — the same loop that owns the WS connection.
        """
        import json as _json

        with client.websocket_connect("/ws/live") as ws:
            # Ask the server to broadcast a tick through its own hub
            r = client.post("/test/broadcast",
                            json={"type": "tick", "payload": {"t": 99}})
            assert r.status_code == 200
            data = _json.loads(ws.receive_text())
            assert data["type"]         == "tick"
            assert data["payload"]["t"] == 99

    def test_ws_receives_risk_frame_from_hub(self):
        import json as _json

        with client.websocket_connect("/ws/live") as ws:
            r = client.post("/test/broadcast",
                            json={"type": "risk", "payload": {"risk_score": 80}})
            assert r.status_code == 200
            data = _json.loads(ws.receive_text())
            assert data["type"] == "risk"

    def test_ws_receives_case_frame_from_hub(self):
        import json as _json

        with client.websocket_connect("/ws/live") as ws:
            r = client.post("/test/broadcast",
                            json={"type": "case", "payload": {"status": "OPEN"}})
            assert r.status_code == 200
            data = _json.loads(ws.receive_text())
            assert data["type"] == "case"

    def test_ws_disconnect_does_not_crash_server(self):
        """Closing the WS client must not cause the server to error."""
        with client.websocket_connect("/ws/live"):
            pass   # connect and immediately disconnect
        # Server still reachable
        r = client.get("/health")
        assert r.status_code == 200


# ===========================================================================
# 18: POST /case/{id}/challenge — must NOT falsely return CLEARED
# ===========================================================================

class TestChallenge:

    def test_challenge_not_implemented_before_step4(self):
        """Challenging a non-existent case must return 404."""
        payload = {
            "agent_id":    "A2",
            "policy_hash": "0x" + "de" * 32,
            "signature":   "0x" + "ca" * 64,
        }
        r = client.post("/case/fake-case-id/challenge", json=payload)
        assert r.status_code == 404

    def test_challenge_response_does_not_say_cleared(self):
        """An invalid challenge must not claim CLEARED."""
        run_id = str(uuid.uuid4())
        _db_module.create_run(run_id, "default", 0)
        case = _db_module.create_case(run_id, ["A2", "A3"], 85, "0x" + "aa" * 32, 12)
        payload = {
            "agent_id":    "A2",
            "policy_hash": "0x" + "de" * 32,
            "signature":   "0x" + "ca" * 64,
        }
        r = client.post(f"/case/{case['case_id']}/challenge", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") != "CLEARED"
        assert body.get("status") == "ESCALATED"


# ===========================================================================
# 19: GET /metrics — must not invent fake metrics
# ===========================================================================

class TestMetrics:

    def test_metrics_not_implemented_returns_501(self):
        r = client.get("/metrics")
        assert r.status_code == 501

    def test_metrics_response_does_not_have_fake_values(self):
        r = client.get("/metrics")
        body = r.json()
        # Must not contain invented TPR/FPR numbers
        assert "tpr" not in body
        assert "fpr" not in body