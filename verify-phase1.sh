#!/bin/bash
# Phase 1 Verification Script
# Validates: PostgreSQL pgvector, Ollama models, Mage.ai accessibility

set -e

echo "============================================"
echo "Phase 1: Verification Checks"
echo "============================================"
echo ""

PASSED=0
FAILED=0

# Check 1: Mage.ai container running
echo "✓ Check 1: Mage.ai Container Running"
if docker ps | grep -q "brain-mage"; then
    echo "  ✅ PASS: Mage.ai container is running"
    ((PASSED++))
else
    echo "  ❌ FAIL: Mage.ai container not found"
    ((FAILED++))
fi
echo ""

# Check 2: Mage.ai NOT publicly accessible
echo "✓ Check 2: Mage.ai NOT Public (port 6789 blocked)"
if ! curl -s --max-time 5 http://46.224.37.114:6789/api/status > /dev/null 2>&1; then
    echo "  ✅ PASS: Mage.ai is NOT publicly accessible (correct)"
    ((PASSED++))
else
    echo "  ❌ FAIL: Mage.ai is publicly accessible (security risk!)"
    ((FAILED++))
fi
echo ""

# Check 3: Mage.ai accessible internally
echo "✓ Check 3: Mage.ai Accessible Internally (localhost)"
if curl -s --max-time 10 http://localhost:6789/api/status | grep -q "status"; then
    echo "  ✅ PASS: Mage.ai responds on localhost:6789"
    ((PASSED++))
else
    echo "  ⚠️  WARNING: Mage.ai not responding yet (may need more time)"
    echo "  Try again in 30 seconds: curl http://localhost:6789/api/status"
    ((FAILED++))
fi
echo ""

# Check 4: PostgreSQL pgvector extension
echo "✓ Check 4: PostgreSQL pgvector Extension"
if docker exec brain-postgres psql -U brain -d brain -c "SELECT * FROM pg_extension WHERE extname='vector';" | grep -q "vector"; then
    echo "  ✅ PASS: pgvector extension is installed"
    ((PASSED++))
else
    echo "  ❌ FAIL: pgvector extension not found"
    echo "  Check logs: docker logs brain-postgres | grep pgvector"
    ((FAILED++))
fi
echo ""

# Check 5: Ollama container running
echo "✓ Check 5: Ollama Container Running"
if docker ps | grep -q "brain-ollama"; then
    echo "  ✅ PASS: Ollama container is running"
    ((PASSED++))
else
    echo "  ❌ FAIL: Ollama container not found"
    ((FAILED++))
fi
echo ""

# Check 6: Ollama models pulled
echo "✓ Check 6: Ollama Models Available"
if docker exec brain-ollama ollama list | grep -q "llama3.2"; then
    echo "  ✅ PASS: llama3.2 model found"
    ((PASSED++))
else
    echo "  ❌ FAIL: llama3.2 model not found"
    echo "  Pull manually: docker exec brain-ollama ollama pull llama3.2:latest"
    ((FAILED++))
fi

if docker exec brain-ollama ollama list | grep -q "nomic-embed-text"; then
    echo "  ✅ PASS: nomic-embed-text model found"
    ((PASSED++))
else
    echo "  ⚠️  WARNING: nomic-embed-text not found (optional)"
    echo "  Pull manually: docker exec brain-ollama ollama pull nomic-embed-text"
fi
echo ""

# Check 7: Mage.ai can reach Ollama
echo "✓ Check 7: Mage.ai → Ollama Connectivity"
if docker exec brain-mage curl -s --max-time 5 http://ollama:11434/api/tags > /dev/null 2>&1; then
    echo "  ✅ PASS: Mage.ai can reach Ollama"
    ((PASSED++))
else
    echo "  ❌ FAIL: Mage.ai cannot reach Ollama"
    echo "  Check network: docker network inspect brain_internal"
    ((FAILED++))
fi
echo ""

# Check 8: Mage.ai can reach PostgreSQL
echo "✓ Check 8: Mage.ai → PostgreSQL Connectivity"
if docker exec brain-mage nc -zv postgres 5432 2>&1 | grep -q "open"; then
    echo "  ✅ PASS: Mage.ai can reach PostgreSQL"
    ((PASSED++))
else
    echo "  ❌ FAIL: Mage.ai cannot reach PostgreSQL"
    ((FAILED++))
fi
echo ""

# Summary
echo "============================================"
echo "📊 Verification Summary"
echo "============================================"
echo "✅ PASSED: $PASSED/8"
echo "❌ FAILED: $FAILED/8"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 Phase 1: ALL CHECKS PASSED!"
    echo ""
    echo "Next Steps:"
    echo "1. Access Mage.ai via SSH tunnel:"
    echo "   ssh -L 6789:localhost:6789 root@brain.falklabs.de"
    echo "   Then open: http://localhost:6789"
    echo ""
    echo "2. Test Ollama from Mage.ai:"
    echo "   docker exec brain-mage curl http://ollama:11434/api/tags"
    echo ""
    echo "3. Check Mage.ai logs:"
    echo "   docker logs -f brain-mage"
    echo ""
    exit 0
else
    echo "⚠️  Phase 1: Some checks failed"
    echo "Review errors above and run setup again if needed"
    echo ""
    exit 1
fi
