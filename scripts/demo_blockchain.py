"""
scripts/demo_blockchain.py
--------------------------
Demonstration script that executes the complete on-chain Case lifecycle:
    1. openCase           -> captures & prints opened_tx
    2. submitChallenge    -> captures & prints challenge_tx
    3. resolveCase        -> captures & prints resolved_tx
    4. getCase            -> reads and prints final state from contract

Prints three REAL transaction hashes.
"""

import json
import sys
from pathlib import Path

# Add repo root to sys.path
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from backend.chain import ChainClient
from backend.challenge import compute_policy_commitment, sign_action


def main():
    print("=== CoNDA On-Chain Case Lifecycle Demo ===")

    client = ChainClient()
    if not client.is_available():
        print("ERROR: Anvil or CaseRegistry contract is not available.")
        print("Please start Anvil and deploy CaseRegistry first:")
        print("    anvil --port 8545")
        print("    forge script contracts/script/Deploy.s.sol:DeployScript --rpc-url http://127.0.0.1:8545 --broadcast")
        sys.exit(1)

    print(f"Connected to Anvil at: {client.rpc_url}")
    print(f"CaseRegistry address: {client.contract_address}")
    print(f"Chain ID:             {client.chain_id}")
    print("-" * 50)

    # 1. Open Case
    print("\n[Step 1] Opening case on-chain...")
    evidence_hash = "0x" + "aa" * 32
    risk_score = 88
    group_ref = "A2,A3"
    opened_tx = client.open_case(evidence_hash=evidence_hash, risk_score=risk_score, group_ref=group_ref)
    print(f"  -> opened_tx:    {opened_tx}")
    assert opened_tx is not None and opened_tx.startswith("0x"), "Failed to capture opened_tx"

    # Wait for on-chain state to confirm
    receipt = client.w3.eth.get_transaction_receipt(opened_tx)
    assert receipt["status"] == 1, "openCase transaction reverted"
    print(f"  -> Confirmed in block #{receipt['blockNumber']}")

    # 2. Submit Challenge
    print("\n[Step 2] Submitting challenge on-chain...")
    policy = {"agent": "A2", "rule": "deterministic_spread", "spread_bps": 25}
    policy_commitment = compute_policy_commitment(policy)
    challenge_tx = client.submit_challenge(case_id=1, policy_commitment=policy_commitment, proof=b"execution_trace_v1")
    print(f"  -> challenge_tx: {challenge_tx}")
    assert challenge_tx is not None and challenge_tx.startswith("0x"), "Failed to capture challenge_tx"

    receipt = client.w3.eth.get_transaction_receipt(challenge_tx)
    assert receipt["status"] == 1, "submitChallenge transaction reverted"
    print(f"  -> Confirmed in block #{receipt['blockNumber']}")

    # 3. Resolve Case (status = 2 -> CLEARED)
    print("\n[Step 3] Resolving case on-chain (status 2 = CLEARED)...")
    resolved_tx = client.resolve_case(case_id=1, status=2)
    print(f"  -> resolved_tx:  {resolved_tx}")
    assert resolved_tx is not None and resolved_tx.startswith("0x"), "Failed to capture resolved_tx"

    receipt = client.w3.eth.get_transaction_receipt(resolved_tx)
    assert receipt["status"] == 1, "resolveCase transaction reverted"
    print(f"  -> Confirmed in block #{receipt['blockNumber']}")

    # 4. Read Final State from CaseRegistry
    print("\n[Step 4] Querying final on-chain state via getCase(1)...")
    case_data = client.get_case(1)
    status_map = {0: "OPEN", 1: "CHALLENGED", 2: "CLEARED", 3: "ESCALATED"}
    print(f"  -> On-chain status: {status_map.get(case_data['status'], 'UNKNOWN')} ({case_data['status']})")
    print(f"  -> Risk Score:      {case_data['risk_score']}")
    print(f"  -> Submitter:       {case_data['submitter']}")
    print(f"  -> Evidence Hash:   {case_data['evidence_hash']}")

    print("\n" + "=" * 50)
    print("SUCCESS! Three REAL on-chain transaction hashes captured:")
    print(f"  1. opened_tx:    {opened_tx}")
    print(f"  2. challenge_tx: {challenge_tx}")
    print(f"  3. resolved_tx:  {resolved_tx}")
    print("=" * 50)


if __name__ == "__main__":
    main()