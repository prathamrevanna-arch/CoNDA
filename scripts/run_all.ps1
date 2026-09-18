# scripts/run_all.ps1 — Clean boot for CoNDA Member 3 in PowerShell
Write-Host "=== Starting CoNDA Full Stack ==="

$foundryDir = "C:\Users\Pratham\.foundry\bin"
if (Test-Path $foundryDir) {
    $env:PATH = "$foundryDir;$env:PATH"
}

# 1. Boot Anvil in the background
Write-Host "-> Starting local Anvil node on 127.0.0.1:8545..."
$anvilProc = Start-Process -FilePath "$foundryDir\anvil.exe" -ArgumentList "--port 8545 --silent" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

try {
    # 2. Deploy CaseRegistry contract
    Write-Host "-> Deploying CaseRegistry to Anvil..."
    & "$foundryDir\forge.exe" script contracts/script/Deploy.s.sol:DeployScript --rpc-url http://127.0.0.1:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast

    # 3. Ensure config.json
    $config = @{
        rpc_url = "http://127.0.0.1:8545"
        contract_address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
        private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        chain_id = 31337
        abi_path = "abi/CaseRegistry.json"
    } | ConvertTo-Json
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText("config.json", $config, $utf8NoBom)

    # 4. Launch uvicorn
    Write-Host "-> Launching FastAPI uvicorn server on http://localhost:8000..."
    .venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
} finally {
    Write-Host "Shutting down Anvil (PID: $($anvilProc.Id))..."
    Stop-Process -Id $anvilProc.Id -Force -ErrorAction SilentlyContinue
}