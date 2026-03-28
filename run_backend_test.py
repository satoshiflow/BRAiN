#!/usr/bin/env python3
"""Start the backend with the correct environment"""
import subprocess
import os
import sys
import time
import urllib.request
import json

# Set environment
env = os.environ.copy()
env.update({
    'BRAIN_RUNTIME_MODE': 'local',
    'BRAIN_STARTUP_PROFILE': 'minimal',
    'BRAIN_EVENTSTREAM_MODE': 'degraded',
    'LOCAL_LLM_MODE': 'mock',
    'REDIS_URL': 'redis://localhost:6380/0',
    'DATABASE_URL': 'postgresql+asyncpg://brain:brain_dev_pass@localhost:5433/brain_dev',
    'BRAIN_DMZ_GATEWAY_SECRET': 'dev-secret-key-12345',
    'AXE_FUSION_ALLOW_LOCAL_REQUESTS': 'true',
    'AXE_FUSION_ALLOW_LOCAL_FALLBACK': 'true',
    'AXE_CHAT_EXECUTION_PATH': 'direct',
    'AXE_ALLOW_MOCK_FALLBACK': 'true',
    'MOCK_LLM_MODE': 'rules',
})

print("Starting backend...")
proc = subprocess.Popen(
    ['python3', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'],
    cwd='/home/oli/dev/brain-v2/backend',
    env=env,
)

print(f"Backend started with PID: {proc.pid}")
time.sleep(15)

# Test health
print("\n=== Testing health ===")
try:
    resp = urllib.request.urlopen('http://127.0.0.1:8000/api/health')
    print(resp.read().decode())
except Exception as e:
    print(f"Health failed: {e}")

# Test AXE chat
print("\n=== Testing AXE chat ===")
try:
    data = json.dumps({"messages":[{"role":"user","content":"Say hello in 3 words"}],"model":"mock-local"}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/api/axe/chat', data=data, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode())
except Exception as e:
    print(f"Error: {e}")

print("\nDone!")