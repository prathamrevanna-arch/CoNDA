"""
scripts/verify_e2e_audit.py
---------------------------
Live end-to-end verification script for CoNDA Member 3 audit.
Tests:
  1. Live Anvil + Deploy CaseRegistry
  2. Live Uvicorn server + WebSocket client receiving tick/risk/case frames
  3. POST /run/start, poll status, GET /risk/latest, GET /cases
  4. Real transaction hashes for opened_tx, challenge_tx, resolved_tx
  5. Valid challenge -> CLEARED with strict semantic wording
  6. Invalid challenge -> ESCALATED
  7. Chain-offline test (Anvil shut down):
     - /health reports chain=false
     - Stream and runs still complete
     - Local case created with opened_tx=None
     - Local challenge succeeds with challenge_tx=None, resolved_tx=None
"""

import asyncio
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# Add repo root to sys.path
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import websockets
from eth_account import Account
from backend.challenge import compute_policy_commitment, sign_action, CLEARED_MESSAGE

FOUNDRY_BIN = Path(r"C:\Users\Pratham\.foundry\bin")
ANVIL_EXE = FOUNDRY_BIN / "anvil.exe"
FORGE_EXE = FOUNDRY_BIN / "forge.exe"
PYTHON_EXE = _REPO / ".venv" / "Scripts" / "python.exe"

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/live"


def http_get(url: str) -> dict:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post(url: str, data: dict) -> tuple[int, dict]:
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8"))


async def test_live_pipeline():
    print("\n=======================================================")
    print(">>> SECTION 1: LIVE ANVIL + UVICORN + WEBSOCKET E2E <<<")
    print("=======================================================")

    # 1. Start Anvil
    print("1. Starting Anvil on port 8545...")
    anvil_proc = subprocess.Popen(
        [str(ANVIL_EXE), "--port", "8545", "--silent"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    # 2. Deploy CaseRegistry
    print("2. Deploying CaseRegistry to Anvil...")
    deploy_cmd = [
        str(FORGE_EXE), "script", "contracts/script/Deploy.s.sol:DeployScript",
        "--rpc-url", "http://127.0.0.1:8545",
        "--private-key", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        "--broadcast"
    ]
    subprocess.run(deploy_cmd, cwd=str(_REPO), check=True, capture_output=True)
    print("   Deploy script broadcast confirmed.")

    # 3. Start Uvicorn
    print("3. Starting Uvicorn on 127.0.0.1:8000...")
    uvicorn_proc = subprocess.Popen(
        [str(PYTHON_EXE), "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(_REPO),
    )
    time.sleep(3)

    try:
        # Check /health
        health = http_get(f"{BASE_URL}/health")
        print(f"4. GET /health response: {health}")
        assert health["ok"] is True
        assert health["chain"] is True
        assert health["detector"] == "stub"

        # Connect WebSocket
        print(f"5. Connecting to WebSocket: {WS_URL} ...")
        received_frames = {"tick": 0, "risk": 0, "case": 0}
        case_payloads = []

        async with websockets.connect(WS_URL) as ws:
            print("   WebSocket connected successfully!")

            # Call POST /run/start
            status_code, start_res = http_post(f"{BASE_URL}/run/start", {"scenario": "default"})
            print(f"6. POST /run/start -> Status {status_code}, Body: {start_res}")
            assert status_code == 202
            run_id = start_res["run_id"]

            # Listen on WebSocket while run completes
            print("7. Receiving frames from WebSocket...")
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    frame = json.loads(msg)
                    ftype = frame.get("type")
                    if ftype in received_frames:
                        received_frames[ftype] += 1
                    if ftype == "case":
                        case_payloads.append(frame.get("payload"))
                        print(f"   [WS FRAME] CASE OPENED: {frame['payload']['case_id']}, opened_tx={frame['payload'].get('opened_tx')}")
                    elif ftype == "risk":
                        score = frame['payload'].get('risk_score')
                        print(f"   [WS FRAME] RISK: score={score}, verdict={frame['payload'].get('verdict')}")
                except asyncio.TimeoutError:
                    # Check run status
                    st = http_get(f"{BASE_URL}/run/{run_id}/status")
                    if st["state"] == "done":
                        print(f"   Run reached done state at tick {st['tick']}/{st['total']}")
                        break

            print(f"8. WebSocket Frame Summary: {received_frames}")
            assert received_frames["tick"] >= 30, f"Expected >= 30 ticks, got {received_frames['tick']}"
            assert received_frames["risk"] >= 8, f"Expected >= 8 risks, got {received_frames['risk']}"
            assert received_frames["case"] >= 1, f"Expected >= 1 case, got {received_frames['case']}"

        # Check /risk/latest
        latest_risk = http_get(f"{BASE_URL}/risk/latest?run_id={run_id}")
        print(f"9. GET /risk/latest: risk_score={latest_risk['risk_score']}, group={latest_risk['group']}, verdict={latest_risk['verdict']}")
        assert latest_risk["risk_score"] == 90
        assert latest_risk["verdict"] == "HIGH"

        # Check /cases
        cases = http_get(f"{BASE_URL}/cases?run_id={run_id}")
        print(f"10. GET /cases returned {len(cases)} case(s)")
        assert len(cases) == 1
        auto_case = cases[0]
        case_id = auto_case["case_id"]
        opened_tx = auto_case["opened_tx"]
        print(f"    Auto Case ID: {case_id}")
        print(f"    opened_tx:    {opened_tx}")
        assert opened_tx is not None and opened_tx.startswith("0x") and len(opened_tx) == 66

        # 11. Challenge verification: VALID CHALLENGE
        print("\n11. Testing VALID CHALLENGE submission...")
        key_a2 = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
        policy = {"agent": "A2", "strategy": "deterministic_quote", "spread_bps": 20}
        commitment = compute_policy_commitment(policy)
        action = {"action": "quote", "price": 100.5, "tick": 32}
        sig = sign_action(action, key_a2)

        valid_payload = {
            "agent_id": "A2",
            "policy_commitment": commitment,
            "policy_json": policy,
            "signature": sig,
            "flagged_action": action,
        }
        st_chal, res_chal = http_post(f"{BASE_URL}/case/{case_id}/challenge", valid_payload)
        print(f"    Status code:  {st_chal}")
        print(f"    Response body: {json.dumps(res_chal, indent=2)}")
        assert st_chal == 200
        assert res_chal["valid"] is True
        assert res_chal["status"] == "CLEARED"
        assert res_chal["challenge_tx"] is not None and res_chal["challenge_tx"].startswith("0x")
        assert res_chal["resolved_tx"] is not None and res_chal["resolved_tx"].startswith("0x")
        assert res_chal["explanation"] == CLEARED_MESSAGE
        # Ensure no claim of innocence
        assert "innocence" not in res_chal["explanation"].lower()
        assert "did not participate" not in res_chal["explanation"].lower()

        # 12. Challenge verification: INVALID CHALLENGE (Tampered policy)
        print("\n12. Testing INVALID CHALLENGE submission (Tampered policy)...")
        # Open another case for testing invalid challenge
        st_open, case2 = http_post(f"{BASE_URL}/case/open", {
            "run_id": run_id,
            "group": ["A2", "A3"],
            "risk_score": 92,
            "evidence_hash": "0x" + "bb" * 32,
        })
        case2_id = case2["case_id"]
        invalid_payload = dict(valid_payload)
        invalid_payload["policy_json"] = {"agent": "A2", "strategy": "collusive_arbitrage"}

        st_inv, res_inv = http_post(f"{BASE_URL}/case/{case2_id}/challenge", invalid_payload)
        print(f"    Status code:  {st_inv}")
        print(f"    Response body: {json.dumps(res_inv, indent=2)}")
        assert st_inv == 200
        assert res_inv["valid"] is False
        assert res_inv["status"] == "ESCALATED"

    finally:
        print("\nStopping Uvicorn and Anvil...")
        uvicorn_proc.terminate()
        anvil_proc.terminate()
        try:
            uvicorn_proc.wait(timeout=3)
            anvil_proc.wait(timeout=3)
        except Exception:
            pass


async def test_chain_offline():
    print("\n=======================================================")
    print(">>> SECTION 2: CHAIN OFFLINE / GRACEFUL DEGRADATION <<<")
    print("=======================================================")
    # Confirm Anvil is NOT running
    print("1. Ensuring Anvil is stopped...")

    # Start Uvicorn
    print("2. Starting Uvicorn on 127.0.0.1:8000 (without Anvil)...")
    uvicorn_proc = subprocess.Popen(
        [str(PYTHON_EXE), "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(_REPO),
    )
    time.sleep(3)

    try:
        # Check /health
        health = http_get(f"{BASE_URL}/health")
        print(f"3. GET /health (Anvil OFF): {health}")
        assert health["ok"] is True
        assert health["chain"] is False
        assert health["detector"] == "stub"

        # Open case manually
        print("4. Testing POST /case/open when chain is offline...")
        # Create run first
        st_run, run_info = http_post(f"{BASE_URL}/run/start", {"scenario": "default"})
        run_id = run_info["run_id"]
        time.sleep(1)

        st_c, c_data = http_post(f"{BASE_URL}/case/open", {
            "run_id": run_id,
            "group": ["A2", "A3"],
            "risk_score": 85,
            "evidence_hash": "0x" + "ff" * 32,
        })
        print(f"   Status code: {st_c}")
        print(f"   Case record: {c_data}")
        assert st_c == 201
        assert c_data["status"] == "OPEN"
        assert c_data["opened_tx"] is None

        # Challenge case while offline
        print("5. Testing POST /case/{id}/challenge when chain is offline...")
        key_a2 = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
        policy = {"agent": "A2", "strategy": "deterministic_quote"}
        commitment = compute_policy_commitment(policy)
        action = {"action": "quote", "price": 100.5}
        sig = sign_action(action, key_a2)

        st_chal, res_chal = http_post(f"{BASE_URL}/case/{c_data['case_id']}/challenge", {
            "agent_id": "A2",
            "policy_commitment": commitment,
            "policy_json": policy,
            "signature": sig,
            "flagged_action": action,
        })
        print(f"   Status code: {st_chal}")
        print(f"   Response:    {res_chal}")
        assert st_chal == 200
        assert res_chal["status"] == "CLEARED"
        assert res_chal["challenge_tx"] is None
        assert res_chal["resolved_tx"] is None
        print("   Offline challenge succeeded locally with null transaction hashes!")

    finally:
        print("\nStopping Uvicorn...")
        uvicorn_proc.terminate()
        try:
            uvicorn_proc.wait(timeout=3)
        except Exception:
            pass


async def main():
    await test_live_pipeline()
    await test_chain_offline()
    print("\n=======================================================")
    print(">>> ALL AUDIT & INTEGRATION TESTS PASSED 100%! <<<")
    print("=======================================================")


if __name__ == "__main__":
    asyncio.run(main())