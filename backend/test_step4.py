"""
backend/test_step4.py
---------------------
Comprehensive tests for Step 4:
    - Solidity contract behavior (via Anvil or web3)
    - backend/chain.py (Anvil client, graceful degradation, tx hash capture)
    - backend/challenge.py (policy commitment, ECDSA signature, CLEARED, ESCALATED)
    - Integration with DB and FastAPI API
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Generator
from unittest.mock import patch, MagicMock

import pytest
from eth_account import Account
from fastapi.testclient import TestClient

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import backend.db as db
from backend.chain import ChainClient, is_chain_available, open_case, submit_challenge, resolve_case
from backend.challenge import (
    CLEARED_MESSAGE,
    AGENT_ADDRESS_MAP,
    compute_policy_commitment,
    verify_policy_commitment,
    sign_action,
    verify_action_signature,
    verify_challenge,
)
from backend.main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Session DB redirection
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="session")
def setup_test_db(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("db_step4")
    db._DATA_DIR = tmp
    db._DB_PATH = tmp / "test_step4.db"
    db.initialize_db()
    yield


# ===========================================================================
# 1. Policy Commitment Tests
# ===========================================================================

class TestPolicyCommitment:

    def test_valid_policy_commitment(self):
        policy = {"max_slippage_bps": 50, "rebalance_interval_sec": 60, "allowed_pairs": ["ETH/USDC"]}
        commitment = compute_policy_commitment(policy)
        assert commitment.startswith("0x")
        assert len(commitment) == 66
        assert verify_policy_commitment(policy, commitment) is True

    def test_invalid_policy_commitment(self):
        policy_original = {"max_slippage_bps": 50}
        commitment = compute_policy_commitment(policy_original)

        policy_tampered = {"max_slippage_bps": 100}
        assert verify_policy_commitment(policy_tampered, commitment) is False

    def test_missing_policy_commitment_returns_false(self):
        policy = {"test": 1}
        assert verify_policy_commitment(policy, None) is False
        assert verify_policy_commitment(None, "0x1234") is False


# ===========================================================================
# 2. ECDSA Signature Recovery Tests
# ===========================================================================

class TestActionSignature:

    def test_valid_signature_recovery(self):
        acct = Account.create()
        action = {"action": "swap", "token_in": "USDC", "amount_in": 1000, "tick": 24}
        sig = sign_action(action, acct.key.hex())

        valid, recovered = verify_action_signature(action, sig, acct.address)
        assert valid is True
        assert recovered.lower() == acct.address.lower()

    def test_invalid_signature_different_key(self):
        acct_agent = Account.create()
        acct_attacker = Account.create()

        action = {"action": "quote", "price": 105.0}
        sig = sign_action(action, acct_attacker.key.hex())

        valid, recovered = verify_action_signature(action, sig, acct_agent.address)
        assert valid is False
        assert recovered.lower() != acct_agent.address.lower()

    def test_corrupted_signature(self):
        valid, recovered = verify_action_signature("action", "0xdeadbeef", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
        assert valid is False
        assert recovered is None


# ===========================================================================
# 3. Full Challenge Verification Pipeline Tests
# ===========================================================================

class TestChallengeVerification:

    @pytest.fixture
    def valid_challenge_payload(self):
        # Use Anvil Account 2 (A2)
        # Address: 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
        # Key: 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a
        key = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
        policy = {"agent": "A2", "strategy": "conservative_mm", "spread_bps": 20}
        commitment = compute_policy_commitment(policy)
        action = {"t": 32, "action": "quote", "bid": 99.5, "ask": 100.5}
        sig = sign_action(action, key)

        return {
            "agent_id": "A2",
            "policy_commitment": commitment,
            "policy_json": policy,
            "signature": sig,
            "flagged_action": action,
            "trace": {"inputs": action, "output": "order_placed"},
        }

    def test_valid_challenge_results_in_cleared(self, valid_challenge_payload):
        res = verify_challenge(valid_challenge_payload)
        assert res["status"] == "CLEARED"
        assert res["policy_valid"] is True
        assert res["signature_valid"] is True
        assert res["explanation"] == CLEARED_MESSAGE
        # Critical compliance check: does NOT claim innocence of collusion
        assert "innocence" not in res["explanation"].lower()
        assert "did not participate" not in res["explanation"].lower()

    def test_tampered_policy_results_in_escalated(self, valid_challenge_payload):
        payload = dict(valid_challenge_payload)
        payload["policy_json"] = {"agent": "A2", "strategy": "aggressive_collusion"}
        res = verify_challenge(payload)
        assert res["status"] == "ESCALATED"
        assert res["policy_valid"] is False

    def test_tampered_signature_results_in_escalated(self, valid_challenge_payload):
        payload = dict(valid_challenge_payload)
        # Sign with different key (Account 3)
        other_key = "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6"
        payload["signature"] = sign_action(payload["flagged_action"], other_key)
        res = verify_challenge(payload)
        assert res["status"] == "ESCALATED"
        assert res["signature_valid"] is False

    def test_missing_signature_results_in_escalated(self, valid_challenge_payload):
        payload = dict(valid_challenge_payload)
        payload["signature"] = None
        res = verify_challenge(payload)
        assert res["status"] == "ESCALATED"

    def test_missing_policy_json_results_in_escalated(self, valid_challenge_payload):
        payload = dict(valid_challenge_payload)
        payload["policy_json"] = None
        res = verify_challenge(payload)
        assert res["status"] == "ESCALATED"

    def test_missing_policy_commitment_results_in_escalated(self, valid_challenge_payload):
        payload = dict(valid_challenge_payload)
        payload["policy_commitment"] = None
        payload["policy_hash"] = None
        res = verify_challenge(payload)
        assert res["status"] == "ESCALATED"


# ===========================================================================
# 4. Graceful Degradation (Chain Unavailable) Tests
# ===========================================================================

class TestChainUnavailable:

    @pytest.fixture
    def mock_offline_client(self):
        offline = ChainClient(rpc_url="http://127.0.0.1:59999")
        return offline

    def test_is_chain_available_false_when_unreachable(self, mock_offline_client):
        assert mock_offline_client.is_available() is False

    def test_open_case_returns_none_when_unavailable(self, mock_offline_client):
        res = mock_offline_client.open_case("0x" + "aa" * 32, 85, "A2,A3")
        assert res is None

    def test_submit_challenge_returns_none_when_unavailable(self, mock_offline_client):
        res = mock_offline_client.submit_challenge(1, "0x" + "bb" * 32)
        assert res is None

    def test_resolve_case_returns_none_when_unavailable(self, mock_offline_client):
        res = mock_offline_client.resolve_case(1, 2)
        assert res is None

    def test_local_only_case_behavior_when_anvil_unavailable(self):
        run_id = str(uuid.uuid4())
        db.create_run(run_id, "default", 0)
        case = db.create_case(
            run_id=run_id,
            group=["A2", "A3"],
            risk_score=85,
            evidence_hash="0x" + "ab" * 32,
            opened_at_tick=12,
            opened_tx=None,
        )
        assert case["status"] == "OPEN"
        assert case["opened_tx"] is None
        assert case["challenge_tx"] is None
        assert case["resolved_tx"] is None

        retrieved = db.get_case(case["case_id"])
        assert retrieved is not None
        assert retrieved["opened_tx"] is None

    def test_api_case_open_works_when_chain_unavailable(self):
        run_id = str(uuid.uuid4())
        db.create_run(run_id, "default", 0)
        with patch("backend.chain.is_chain_available", return_value=False):
            with patch("backend.chain.open_case", return_value=None):
                r = client.post(
                    "/case/open",
                    json={
                        "run_id": run_id,
                        "group": ["A2", "A3"],
                        "risk_score": 85,
                        "evidence_hash": "0x" + "cc" * 32,
                    },
                )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "OPEN"
        assert data["opened_tx"] is None

    def test_api_challenge_works_when_chain_unavailable(self):
        run_id = str(uuid.uuid4())
        db.create_run(run_id, "default", 0)
        case = db.create_case(run_id, ["A2", "A3"], 85, "0x" + "cc" * 32, 12)

        key = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
        policy = {"rule": "compliant"}
        commitment = compute_policy_commitment(policy)
        action = {"action": "quote"}
        sig = sign_action(action, key)

        with patch("backend.chain.is_chain_available", return_value=False):
            with patch("backend.chain.submit_challenge", return_value=None):
                with patch("backend.chain.resolve_case", return_value=None):
                    r = client.post(
                        f"/case/{case['case_id']}/challenge",
                        json={
                            "agent_id": "A2",
                            "policy_commitment": commitment,
                            "policy_json": policy,
                            "signature": sig,
                            "flagged_action": action,
                        },
                    )

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "CLEARED"
        assert data["challenge_tx"] is None
        assert data["resolved_tx"] is None
        assert CLEARED_MESSAGE in data["explanation"]


# ===========================================================================
# 5. Live On-Chain Anvil Integration Tests
# ===========================================================================

@pytest.fixture(scope="module")
def anvil_node() -> Generator[dict, None, None]:
    """Start a real local Anvil process and deploy CaseRegistry."""
    foundry_bin = Path(r"C:\Users\Pratham\.foundry\bin")
    anvil_exe = foundry_bin / "anvil.exe"
    forge_exe = foundry_bin / "forge.exe"

    if not anvil_exe.exists() or not forge_exe.exists():
        pytest.skip("Foundry binaries not available in C:\\Users\\Pratham\\.foundry\\bin")

    port = 8545
    proc = subprocess.Popen(
        [str(anvil_exe), "--port", str(port), "--silent"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for Anvil to listen
    time.sleep(1.5)

    contract_addr = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
    private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    rpc_url = f"http://127.0.0.1:{port}"

    # Deploy via forge script
    deploy_cmd = [
        str(forge_exe),
        "script",
        "contracts/script/Deploy.s.sol:DeployScript",
        "--rpc-url",
        rpc_url,
        "--private-key",
        private_key,
        "--broadcast",
    ]
    subprocess.run(deploy_cmd, cwd=str(_REPO), capture_output=True)

    yield {
        "rpc_url": rpc_url,
        "contract_address": contract_addr,
        "private_key": private_key,
        "chain_id": 31337,
    }

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()


class TestChainOnAnvil:

    def test_blockchain_connection_and_deployment(self, anvil_node):
        client_node = ChainClient(
            rpc_url=anvil_node["rpc_url"],
            contract_address=anvil_node["contract_address"],
            private_key=anvil_node["private_key"],
            chain_id=anvil_node["chain_id"],
        )
        assert client_node.is_available() is True

    def test_open_case_captures_real_tx_hash(self, anvil_node):
        client_node = ChainClient(
            rpc_url=anvil_node["rpc_url"],
            contract_address=anvil_node["contract_address"],
            private_key=anvil_node["private_key"],
            chain_id=anvil_node["chain_id"],
        )

        ev_hash = "0x" + "11" * 32
        tx_hash = client_node.open_case(evidence_hash=ev_hash, risk_score=88, group_ref="A2,A3")

        assert tx_hash is not None
        assert tx_hash.startswith("0x")
        assert len(tx_hash) == 66

        # Verify transaction receipt exists on Anvil
        receipt = client_node.w3.eth.get_transaction_receipt(tx_hash)
        assert receipt is not None
        assert receipt["status"] == 1

    def test_submit_challenge_and_resolve_on_chain(self, anvil_node):
        client_node = ChainClient(
            rpc_url=anvil_node["rpc_url"],
            contract_address=anvil_node["contract_address"],
            private_key=anvil_node["private_key"],
            chain_id=anvil_node["chain_id"],
        )

        # 1. Open case on-chain
        open_tx = client_node.open_case("0x" + "22" * 32, 90, "A2,A3")
        assert open_tx is not None

        # 2. Submit challenge on-chain for caseId=1
        policy_commit = "0x" + "33" * 32
        chal_tx = client_node.submit_challenge(case_id=1, policy_commitment=policy_commit)
        assert chal_tx is not None
        assert chal_tx.startswith("0x")
        receipt_chal = client_node.w3.eth.get_transaction_receipt(chal_tx)
        assert receipt_chal["status"] == 1

        # 3. Resolve case on-chain with status 2 (CLEARED)
        res_tx = client_node.resolve_case(case_id=1, status=2)
        assert res_tx is not None
        assert res_tx.startswith("0x")
        receipt_res = client_node.w3.eth.get_transaction_receipt(res_tx)
        assert receipt_res["status"] == 1

        # 4. Verify case status on-chain
        on_chain_data = client_node.get_case(1)
        assert on_chain_data is not None
        assert on_chain_data["status"] == 2  # CLEARED

    def test_full_api_challenge_on_chain(self, anvil_node):
        # Create case in DB
        run_id = str(uuid.uuid4())
        db.create_run(run_id, "default", 0)
        case = db.create_case(run_id, ["A2", "A3"], 85, "0x" + "44" * 32, 20)

        key = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
        policy = {"market_params": "standard"}
        commitment = compute_policy_commitment(policy)
        action = {"action": "trade", "volume": 100}
        sig = sign_action(action, key)

        r = client.post(
            f"/case/{case['case_id']}/challenge",
            json={
                "agent_id": "A2",
                "policy_commitment": commitment,
                "policy_json": policy,
                "signature": sig,
                "flagged_action": action,
            },
        )

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "CLEARED"
        assert data["challenge_tx"] is not None
        assert data["challenge_tx"].startswith("0x")
        assert data["resolved_tx"] is not None
        assert data["resolved_tx"].startswith("0x")