"""
backend/challenge.py
--------------------
Verification of agent policy challenges.

A flagged agent pre-commits:
    keccak256(policy_json)

A challenge supplies:
    - policy_commitment
    - policy JSON
    - ECDSA signature over the flagged action
    - trace

Verification checks BOTH:
    1. The supplied policy JSON hashes to the committed policy commitment.
    2. The ECDSA signature recovers to the flagged agent address.

CRITICAL COMPLIANCE WORDING:
    CLEARED means ONLY:
    "The submitted action was verified as compliant with the pre-committed execution policy."
    It must NOT be represented as proof that the agent did not participate in tacit coordination.

NO ZERO-KNOWLEDGE PROOFS.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional, Union

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

logger = logging.getLogger(__name__)

# Standard known agent addresses for testing and local simulation
# Corresponding to Anvil default accounts 1, 2, 3
AGENT_ADDRESS_MAP: dict[str, str] = {
    "A1": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    "A2": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
    "A3": "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
}

CLEARED_MESSAGE = (
    "The submitted action was verified as compliant with the pre-committed execution policy."
)


def canonical_policy_bytes(policy_json: Any) -> bytes:
    """Produce deterministic UTF-8 bytes for a policy JSON object or string."""
    if isinstance(policy_json, dict) or isinstance(policy_json, list):
        text = json.dumps(policy_json, sort_keys=True, separators=(",", ":"))
        return text.encode("utf-8")
    elif isinstance(policy_json, bytes):
        return policy_json
    elif isinstance(policy_json, str):
        # If it is already a JSON string, try to parse and re-dump canonically
        try:
            parsed = json.loads(policy_json)
            text = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
            return text.encode("utf-8")
        except Exception:
            return policy_json.encode("utf-8")
    else:
        return str(policy_json).encode("utf-8")


def compute_policy_commitment(policy_json: Any) -> str:
    """Compute keccak256 hash of canonical policy JSON string. Returns 0x... hex string."""
    data = canonical_policy_bytes(policy_json)
    h = Web3.keccak(data)
    hex_str = h.hex()
    return hex_str if hex_str.startswith("0x") else "0x" + hex_str


def verify_policy_commitment(policy_json: Any, expected_commitment: Optional[str]) -> bool:
    """True if keccak256(policy_json) matches expected_commitment."""
    if not expected_commitment or policy_json is None:
        return False
    try:
        actual = compute_policy_commitment(policy_json).lower()
        expected = expected_commitment.lower()
        if not expected.startswith("0x"):
            expected = "0x" + expected
        return actual == expected
    except Exception as exc:
        logger.warning("Error verifying policy commitment: %s", exc)
        return False


def canonical_action_text(action_data: Any) -> str:
    """Produce deterministic text representation of flagged action for signing."""
    if isinstance(action_data, (dict, list)):
        return json.dumps(action_data, sort_keys=True, separators=(",", ":"))
    elif isinstance(action_data, bytes):
        return action_data.hex()
    return str(action_data) if action_data is not None else ""


def sign_action(action_data: Any, private_key: str) -> str:
    """Sign an action with a private key using standard Ethereum message prefix."""
    text = canonical_action_text(action_data)
    message = encode_defunct(text=text)
    signed = Account.sign_message(message, private_key=private_key)
    sig = signed.signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig


def verify_action_signature(
    action_data: Any, signature: Optional[str], expected_address: Optional[str]
) -> tuple[bool, Optional[str]]:
    """Recover signer address from ECDSA signature and verify against expected address.

    Returns (is_valid, recovered_address).
    """
    if not signature or not expected_address:
        return False, None
    try:
        text = canonical_action_text(action_data)
        message = encode_defunct(text=text)
        recovered = Account.recover_message(message, signature=signature)
        is_valid = recovered.lower() == expected_address.lower()
        return is_valid, recovered
    except Exception as exc:
        logger.warning("ECDSA signature recovery failed: %s", exc)
        return False, None


def resolve_agent_address(agent_id: Optional[str], agent_address: Optional[str] = None) -> Optional[str]:
    """Resolve an agent identifier or address string to a canonical Ethereum address."""
    if agent_address and agent_address.startswith("0x") and len(agent_address) == 42:
        return Web3.to_checksum_address(agent_address)
    if agent_id:
        if agent_id.startswith("0x") and len(agent_id) == 42:
            return Web3.to_checksum_address(agent_id)
        if agent_id in AGENT_ADDRESS_MAP:
            return AGENT_ADDRESS_MAP[agent_id]
    return None


def verify_challenge(data: dict, case_group: Optional[list] = None) -> dict:
    """Full challenge verification pipeline.

    Checks:
      1. Required fields: policy_commitment, policy_json, signature, and agent.
      2. Policy JSON keccak256 hash matches policy_commitment.
      3. ECDSA signature over flagged_action/trace recovers to agent address.

    Returns:
      {
          "status": "CLEARED" | "ESCALATED",
          "policy_valid": bool,
          "signature_valid": bool,
          "explanation": str,
          "recovered_address": Optional[str],
          "expected_address": Optional[str],
      }
    """
    policy_commitment = data.get("policy_commitment") or data.get("policy_hash")
    policy_json = data.get("policy_json") or data.get("policy")
    if policy_json is None and isinstance(data.get("trace"), dict):
        policy_json = data["trace"].get("policy_json") or data["trace"].get("policy")

    signature = data.get("signature")
    action = data.get("flagged_action") if data.get("flagged_action") is not None else data.get("trace")
    if action is None and data.get("action") is not None:
        action = data.get("action")

    # If action is still None, allow signing policy_commitment as fallback
    if action is None:
        action = policy_commitment

    agent_id = data.get("agent_id")
    if not agent_id and isinstance(data.get("trace"), dict):
        agent_id = data["trace"].get("agent_id")
    if not agent_id and isinstance(data.get("flagged_action"), dict):
        agent_id = data["flagged_action"].get("agent_id")

    agent_address = data.get("agent_address")
    expected_addr = resolve_agent_address(agent_id, agent_address)

    # If agent_id not directly resolved, but case_group is provided (e.g. ["A2", "A3"]),
    # check if recovered signature matches any agent in the group.
    if not expected_addr and case_group and signature:
        for candidate in case_group:
            cand_addr = resolve_agent_address(candidate)
            if cand_addr:
                sig_ok, rec = verify_action_signature(action, signature, cand_addr)
                if sig_ok:
                    expected_addr = cand_addr
                    break

    # 1. Missing data checks
    if not policy_commitment:
        return {
            "status": "ESCALATED",
            "policy_valid": False,
            "signature_valid": False,
            "explanation": "Challenge rejected: missing policy commitment.",
            "recovered_address": None,
            "expected_address": expected_addr,
        }

    if policy_json is None:
        return {
            "status": "ESCALATED",
            "policy_valid": False,
            "signature_valid": False,
            "explanation": "Challenge rejected: missing policy JSON payload.",
            "recovered_address": None,
            "expected_address": expected_addr,
        }

    if not signature:
        return {
            "status": "ESCALATED",
            "policy_valid": False,
            "signature_valid": False,
            "explanation": "Challenge rejected: missing ECDSA signature.",
            "recovered_address": None,
            "expected_address": expected_addr,
        }

    if not expected_addr:
        return {
            "status": "ESCALATED",
            "policy_valid": False,
            "signature_valid": False,
            "explanation": f"Challenge rejected: unable to resolve agent identity '{agent_id}'.",
            "recovered_address": None,
            "expected_address": None,
        }

    # 2. Verify policy commitment
    policy_valid = verify_policy_commitment(policy_json, policy_commitment)
    if not policy_valid:
        return {
            "status": "ESCALATED",
            "policy_valid": False,
            "signature_valid": False,
            "explanation": (
                "Challenge rejected: policy JSON does not match committed policy hash."
            ),
            "recovered_address": None,
            "expected_address": expected_addr,
        }

    # 3. Verify ECDSA signature over flagged action
    sig_valid, recovered_addr = verify_action_signature(action, signature, expected_addr)
    if not sig_valid:
        return {
            "status": "ESCALATED",
            "policy_valid": True,
            "signature_valid": False,
            "explanation": (
                f"Challenge rejected: signature recovered to {recovered_addr}, expected {expected_addr}."
            ),
            "recovered_address": recovered_addr,
            "expected_address": expected_addr,
        }

    # BOTH valid -> CLEARED with required compliance wording
    return {
        "status": "CLEARED",
        "policy_valid": True,
        "signature_valid": True,
        "explanation": CLEARED_MESSAGE,
        "recovered_address": recovered_addr,
        "expected_address": expected_addr,
    }