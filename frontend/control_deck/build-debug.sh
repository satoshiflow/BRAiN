#!/bin/bash
# Build-Debug-Wrapper für Control Deck
# Dieses Script wird im Dockerfile ausgeführt und erfasst alle Logs

set -e

echo "========================================"
echo "BRAiN Control Deck - Build Debug Start"
echo "========================================"
echo "Timestamp: $(date)"
echo "Node Version: $(node --version)"
echo "NPM Version: $(npm --version)"
echo "Working Directory: $(pwd)"
echo "========================================"

# Erstelle Log-Verzeichnis
mkdir -p /tmp/build-logs

# Führe Build aus und erfasse Logs
{
    echo "=== NPM Install Start ==="
    npm ci --legacy-peer-deps --prefer-offline --no-audit 2>&1
    
    echo "=== Build Start ==="
    npm run build 2>&1
    
    echo "=== Build Success ==="
} | tee /tmp/build-logs/build-output.log

# Kopiere Logs zu einem persistenten Ort (wenn verfügbar)
if [ -d "/app/build-logs" ]; then
    cp /tmp/build-logs/* /app/build-logs/
fi

echo "========================================"
echo "Build Debug Complete"
echo "========================================"
