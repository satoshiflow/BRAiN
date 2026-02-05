#!/bin/bash
# Test script for new /api/credits/add endpoint

API_BASE="http://localhost:8000"

echo "🧪 Testing /api/credits/add endpoint"
echo "======================================"
echo ""

# Test 1: Create agent with initial credits
echo "1️⃣ Creating test agent with initial credits..."
curl -X POST "$API_BASE/api/credits/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test_agent_add",
    "skill_level": 0.5,
    "actor_id": "test_script"
  }' 2>/dev/null | jq '.'

echo ""
echo "2️⃣ Checking initial balance..."
curl "$API_BASE/api/credits/balance/test_agent_add" 2>/dev/null | jq '.'

echo ""
echo "3️⃣ Adding 100 credits using new /add endpoint..."
curl -X POST "$API_BASE/api/credits/add" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test_agent_add",
    "amount": 100.0,
    "reason": "Monthly budget top-up",
    "actor_id": "admin"
  }' 2>/dev/null | jq '.'

echo ""
echo "4️⃣ Checking balance after add..."
curl "$API_BASE/api/credits/balance/test_agent_add" 2>/dev/null | jq '.'

echo ""
echo "5️⃣ Adding another 50 credits..."
curl -X POST "$API_BASE/api/credits/add" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test_agent_add",
    "amount": 50.0,
    "reason": "Performance bonus",
    "actor_id": "admin"
  }' 2>/dev/null | jq '.'

echo ""
echo "6️⃣ Final balance check..."
curl "$API_BASE/api/credits/balance/test_agent_add" 2>/dev/null | jq '.'

echo ""
echo "7️⃣ Transaction history..."
curl "$API_BASE/api/credits/history/test_agent_add?limit=10" 2>/dev/null | jq '.'

echo ""
echo "✅ Test complete!"
