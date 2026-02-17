#!/bin/bash
# BRAiN Frontend Production Start Script
# Run this in your local terminal (not via OpenClaw session)

echo "🧠 Starting BRAiN Frontend Production Server..."

# Kill existing processes
pkill -f "next" 2>/dev/null
sleep 2

# Navigate to frontend
cd /home/oli/dev/brain-v2/frontend/control_deck

# Build (takes ~2-3 minutes)
echo "📦 Building production bundle..."
npm run build

# Start production server on localhost only (secure)
echo "🚀 Starting production server on localhost:3001..."
npm start -- -p 3001 -H 127.0.0.1

# Server is now running at http://127.0.0.1:3001
# Use Ctrl+C to stop
