"""
backend/chain.py
----------------
Web3.py client for CoNDA's CaseRegistry smart contract.

Provides wrappers for:
    open_case(evidence_hash, risk_score, group_ref) -> tx_hash or None
    submit_challenge(case_id, policy_commitment, proof) -> tx_hash or None
    resolve_case(case_id, status) -> tx_hash or None
    is_chain_available() -> bool
    get_case(case_id) -> dict or None

Graceful degradation:
If local Anvil is not running, or the contract is unreachable, all methods
return None (or False) without raising an exception, and the backend continues
working entirely locally with null transaction hashes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional, Union

from eth_account import Account
from web3 import Web3

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "config.json"
_ABI_PATH = _REPO_ROOT / "abi" / "CaseRegistry.json"

# In-memory mapping from local case UUID -> on-chain caseId (uint256)
_LOCAL_TO_CHAIN_ID: dict[str, int] = {}


def _get_raw_tx(signed: Any) -> bytes:
    """Retrieve raw transaction bytes across different eth-account versions."""
    if hasattr(signed, "rawTransaction"):
        return signed.rawTransaction
    if hasattr(signed, "raw_transaction"):
        return signed.raw_transaction
    raise AttributeError("SignedTransaction object has neither rawTransaction nor raw_transaction")


def load_config() -> dict:
    """Load configuration from config.json with safe local defaults."""
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Could not read config.json: %s", exc)
    return {
        "rpc_url": "http://127.0.0.1:8545",
        "contract_address": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
        "private_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        "chain_id": 31337,
        "abi_path": "abi/CaseRegistry.json",
    }


def load_abi() -> list:
    """Load CaseRegistry ABI."""
    cfg = load_config()
    abi_file = _REPO_ROOT / cfg.get("abi_path", "abi/CaseRegistry.json")
    if abi_file.exists():
        try:
            with open(abi_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Could not read ABI: %s", exc)
    return []


class ChainClient:
    """Manages interaction with the CaseRegistry contract on Anvil."""

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        private_key: Optional[str] = None,
        chain_id: Optional[int] = None,
    ) -> None:
        cfg = load_config()
        self.rpc_url = rpc_url or cfg.get("rpc_url", "http://127.0.0.1:8545")
        self.contract_address = contract_address or cfg.get("contract_address", "")
        self.private_key = private_key or cfg.get("private_key", "")
        self.chain_id = int(chain_id or cfg.get("chain_id", 31337))
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.abi = load_abi()

    def is_available(self) -> bool:
        """Check if local Anvil is reachable and CaseRegistry is deployed."""
        try:
            if not self.w3.is_connected():
                return False
            if not self.contract_address:
                return False
            checksum = Web3.to_checksum_address(self.contract_address)
            code = self.w3.eth.get_code(checksum)
            return len(code) > 0
        except Exception:
            return False

    def open_case(
        self,
        evidence_hash: Union[str, bytes],
        risk_score: int,
        group_ref: str = "",
        local_case_id: Optional[str] = None,
    ) -> Optional[str]:
        """Open a case on-chain. Returns real tx hash string (0x...) or None."""
        if not self.is_available():
            logger.debug("Chain unavailable; skipping on-chain openCase")
            return None

        try:
            if isinstance(evidence_hash, str):
                h = evidence_hash[2:] if evidence_hash.startswith("0x") else evidence_hash
                ev_bytes = bytes.fromhex(h.zfill(64)[:64])
            else:
                ev_bytes = bytes(evidence_hash)[:32].rjust(32, b"\x00")

            checksum = Web3.to_checksum_address(self.contract_address)
            contract = self.w3.eth.contract(address=checksum, abi=self.abi)
            account = Account.from_key(self.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)

            tx = contract.functions.openCase(
                ev_bytes, int(risk_score), str(group_ref)
            ).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "chainId": self.chain_id,
                "gas": 300000,
                "gasPrice": self.w3.eth.gas_price,
            })

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            raw_tx = _get_raw_tx(signed)
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=10)

            # Record on-chain caseId if event is present
            try:
                events = contract.events.CaseOpened().process_receipt(receipt)
                if events:
                    on_chain_id = events[0]["args"]["caseId"]
                    if local_case_id:
                        _LOCAL_TO_CHAIN_ID[local_case_id] = on_chain_id
                    _LOCAL_TO_CHAIN_ID[str(on_chain_id)] = on_chain_id
            except Exception:
                pass

            tx_hex = tx_hash.hex()
            if not tx_hex.startswith("0x"):
                tx_hex = "0x" + tx_hex
            logger.info("On-chain openCase successful: %s", tx_hex)
            return tx_hex

        except Exception as exc:
            logger.warning("On-chain openCase failed: %s", exc)
            return None

    def submit_challenge(
        self,
        case_id: Union[int, str],
        policy_commitment: Union[str, bytes],
        proof: bytes = b"",
    ) -> Optional[str]:
        """Submit challenge on-chain. Returns real tx hash string or None."""
        if not self.is_available():
            logger.debug("Chain unavailable; skipping on-chain submitChallenge")
            return None

        try:
            checksum = Web3.to_checksum_address(self.contract_address)
            contract = self.w3.eth.contract(address=checksum, abi=self.abi)

            # Resolve target on-chain ID
            if isinstance(case_id, int):
                target_id = case_id
            elif str(case_id).isdigit():
                target_id = int(case_id)
            else:
                target_id = _LOCAL_TO_CHAIN_ID.get(str(case_id), 1)

            # Ensure on-chain case exists (caseId must be < nextCaseId)
            try:
                next_id = contract.functions.nextCaseId().call()
                if target_id >= next_id:
                    self.open_case(bytes(32), 80, "auto_init")
                    next_id = contract.functions.nextCaseId().call()
                    target_id = next_id - 1
            except Exception:
                pass

            if isinstance(policy_commitment, str):
                h = policy_commitment[2:] if policy_commitment.startswith("0x") else policy_commitment
                pc_bytes = bytes.fromhex(h.zfill(64)[:64])
            else:
                pc_bytes = bytes(policy_commitment)[:32].rjust(32, b"\x00")

            account = Account.from_key(self.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)

            tx = contract.functions.submitChallenge(
                target_id, pc_bytes, proof
            ).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "chainId": self.chain_id,
                "gas": 300000,
                "gasPrice": self.w3.eth.gas_price,
            })

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            raw_tx = _get_raw_tx(signed)
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=10)

            tx_hex = tx_hash.hex()
            if not tx_hex.startswith("0x"):
                tx_hex = "0x" + tx_hex
            logger.info("On-chain submitChallenge successful: %s", tx_hex)
            return tx_hex

        except Exception as exc:
            logger.warning("On-chain submitChallenge failed: %s", exc)
            return None

    def resolve_case(
        self,
        case_id: Union[int, str],
        status: int,
    ) -> Optional[str]:
        """Resolve case on-chain (status 2=CLEARED, 3=ESCALATED). Returns real tx hash or None."""
        if not self.is_available():
            logger.debug("Chain unavailable; skipping on-chain resolveCase")
            return None

        try:
            checksum = Web3.to_checksum_address(self.contract_address)
            contract = self.w3.eth.contract(address=checksum, abi=self.abi)

            if isinstance(case_id, int):
                target_id = case_id
            elif str(case_id).isdigit():
                target_id = int(case_id)
            else:
                target_id = _LOCAL_TO_CHAIN_ID.get(str(case_id), 1)

            # Ensure on-chain case exists
            try:
                next_id = contract.functions.nextCaseId().call()
                if target_id >= next_id:
                    self.open_case(bytes(32), 80, "auto_init")
                    next_id = contract.functions.nextCaseId().call()
                    target_id = next_id - 1
            except Exception:
                pass

            account = Account.from_key(self.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)

            tx = contract.functions.resolveCase(
                target_id, int(status)
            ).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "chainId": self.chain_id,
                "gas": 300000,
                "gasPrice": self.w3.eth.gas_price,
            })

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            raw_tx = _get_raw_tx(signed)
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=10)

            tx_hex = tx_hash.hex()
            if not tx_hex.startswith("0x"):
                tx_hex = "0x" + tx_hex
            logger.info("On-chain resolveCase successful: %s", tx_hex)
            return tx_hex

        except Exception as exc:
            logger.warning("On-chain resolveCase failed: %s", exc)
            return None

    def get_case(self, case_id: Union[int, str]) -> Optional[dict]:
        """Read case from CaseRegistry contract."""
        if not self.is_available():
            return None
        try:
            if isinstance(case_id, int):
                target_id = case_id
            elif str(case_id).isdigit():
                target_id = int(case_id)
            else:
                target_id = _LOCAL_TO_CHAIN_ID.get(str(case_id), 1)

            checksum = Web3.to_checksum_address(self.contract_address)
            contract = self.w3.eth.contract(address=checksum, abi=self.abi)
            ev_hash, risk, status, submitter = contract.functions.getCase(target_id).call()
            return {
                "case_id": target_id,
                "evidence_hash": "0x" + ev_hash.hex(),
                "risk_score": risk,
                "status": status,
                "submitter": submitter,
            }
        except Exception as exc:
            logger.warning("On-chain getCase failed: %s", exc)
            return None


# Module-level default singleton
client = ChainClient()


def is_chain_available() -> bool:
    return client.is_available()


def open_case(
    evidence_hash: Union[str, bytes],
    risk_score: int,
    group_ref: str = "",
    local_case_id: Optional[str] = None,
) -> Optional[str]:
    return client.open_case(evidence_hash, risk_score, group_ref, local_case_id)


def submit_challenge(
    case_id: Union[int, str],
    policy_commitment: Union[str, bytes],
    proof: bytes = b"",
) -> Optional[str]:
    return client.submit_challenge(case_id, policy_commitment, proof)


def resolve_case(case_id: Union[int, str], status: int) -> Optional[str]:
    return client.resolve_case(case_id, status)


def get_case(case_id: Union[int, str]) -> Optional[dict]:
    return client.get_case(case_id)