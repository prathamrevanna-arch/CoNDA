#!/usr/bin/env bash
set -e

# scripts/run_all.sh — Clean boot for CoNDA Member 3 (Backend + Blockchain)
echo "=== Starting CoNDA Full Stack ==="

# 1. Resolve foundry directory
FOUNDRY_BIN="${FOUNDRY_BIN:-/c/Users/Pratham/.foundry/bin}"
if [ -d "$FOUNDRY_BIN" ]; then
    export PATH="$FOUNDRY_BIN:$PATH"
fi

if ! command -v anvil &> /dev/null; then
    echo "ERROR: anvil not found in PATH or $FOUNDRY_BIN"
    exit 1
fi

# 2. Boot Anvil in the background
echo "-> Starting local Anvil node on 127.0.0.1:8545..."
anvil --port 8545 --silent &
ANVIL_PID=$!

cleanup() {
    echo "Shutting down Anvil (PID: $ANVIL_PID)..."
    kill $ANVIL_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 2

# 3. Deploy CaseRegistry contract
echo "-> Deploying CaseRegistry to Anvil..."
forge script contracts/script/Deploy.s.sol:DeployScript \
    --rpc-url http://127.0.0.1:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast

# 4. Verify config.json
CONTRACT_ADDR="0x5FbDB2315678afecb367f032d93F642f64180aa3"
cat <<EOF > config.json
{
  "rpc_url": "http://127.0.0.1:8545",
  "contract_address": "$CONTRACT_ADDR",
  "private_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
  "chain_id": 31337,
  "abi_path": "abi/CaseRegistry.json"
}
EOF

# 5. Launch FastAPI via uvicorn
echo "-> Launching FastAPI uvicorn server on http://localhost:8000..."
if [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON_BIN=".venv/Scripts/python.exe"
else
    PYTHON_BIN="python"
fi

"$PYTHON_BIN" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000