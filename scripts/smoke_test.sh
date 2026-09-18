#!/usr/bin/env bash
set -e

# scripts/smoke_test.sh — Curl-based smoke test against running CoNDA server
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
echo "=== Running CoNDA Smoke Test against $BASE_URL ==="

echo -n "1. Testing GET /health ... "
HEALTH=$(curl -s "$BASE_URL/health")
echo "$HEALTH"
echo "$HEALTH" | grep -q '"ok":true' || (echo "Health check failed!" && exit 1)

echo -n "2. Testing GET /scenarios ... "
SCENARIOS=$(curl -s "$BASE_URL/scenarios")
echo "$SCENARIOS"
echo "$SCENARIOS" | grep -q '"default"' || (echo "Scenarios check failed!" && exit 1)

echo -n "3. Testing POST /run/start ... "
START_RES=$(curl -s -X POST "$BASE_URL/run/start" -H "Content-Type: application/json" -d '{"scenario":"default"}')
echo "$START_RES"
RUN_ID=$(echo "$START_RES" | sed -n 's/.*"run_id":"\([^"]*\)".*/\1/p')
if [ -z "$RUN_ID" ]; then
    echo "Failed to get run_id!"
    exit 1
fi
echo "Started run: $RUN_ID"

echo "4. Polling GET /run/$RUN_ID/status until done..."
for i in {1..30}; do
    STATUS=$(curl -s "$BASE_URL/run/$RUN_ID/status")
    echo "   Status: $STATUS"
    if echo "$STATUS" | grep -q '"done"'; then
        echo "Run completed!"
        break
    fi
    sleep 1
done

echo -n "5. Testing GET /risk/latest ... "
LATEST_RISK=$(curl -s "$BASE_URL/risk/latest?run_id=$RUN_ID")
echo "$LATEST_RISK"
echo "$LATEST_RISK" | grep -q '"risk_score"' || (echo "Latest risk check failed!" && exit 1)

echo -n "6. Testing GET /cases ... "
CASES=$(curl -s "$BASE_URL/cases?run_id=$RUN_ID")
echo "$CASES"
echo "$CASES" | grep -q '"case_id"' || (echo "Cases check failed!" && exit 1)

CASE_ID=$(echo "$CASES" | sed -n 's/.*"case_id":"\([^"]*\)".*/\1/p')
echo "Found case: $CASE_ID"

echo -n "7. Testing POST /case/$CASE_ID/challenge (valid) ... "
CHAL_RES=$(curl -s -X POST "$BASE_URL/case/$CASE_ID/challenge" \
    -H "Content-Type: application/json" \
    -d '{
        "agent_id": "A2",
        "policy_commitment": "0xbe22589718b71828482e2aa2f73ff99beab7d33195584022223c574560e7040b",
        "policy_json": {"rule": "compliant"},
        "signature": "0xb0d754049316729983100a0af17be57febc4b41c449e7c68b0e0146b40c630f84d65f5ee11eba2b6951e48216a9496ae20247ced9eaf40c8e8bc8f38c26abcdc1c",
        "flagged_action": {"action": "quote"}
    }')
echo "$CHAL_RES"
echo "$CHAL_RES" | grep -q '"CLEARED"' || (echo "Valid challenge verification failed!" && exit 1)

echo -n "8. Testing POST /case/$CASE_ID/challenge (invalid - wrong policy) ... "
INV_RES=$(curl -s -X POST "$BASE_URL/case/$CASE_ID/challenge" \
    -H "Content-Type: application/json" \
    -d '{
        "agent_id": "A2",
        "policy_commitment": "0xbe22589718b71828482e2aa2f73ff99beab7d33195584022223c574560e7040b",
        "policy_json": {"rule": "malicious_tampered"},
        "signature": "0xb0d754049316729983100a0af17be57febc4b41c449e7c68b0e0146b40c630f84d65f5ee11eba2b6951e48216a9496ae20247ced9eaf40c8e8bc8f38c26abcdc1c",
        "flagged_action": {"action": "quote"}
    }')
echo "$INV_RES"
echo "$INV_RES" | grep -q '"ESCALATED"' || (echo "Invalid challenge verification failed!" && exit 1)

echo "=== All smoke tests PASSED successfully! ==="