#!/usr/bin/env python3
"""Simple wrapper to start the backend with correct environment"""
import os
import sys

os.environ['BRAIN_RUNTIME_MODE'] = 'local'
os.environ['BRAIN_STARTUP_PROFILE'] = 'minimal'
os.environ['BRAIN_EVENTSTREAM_MODE'] = 'degraded'
os.environ['LOCAL_LLM_MODE'] = 'openai'
os.environ['REDIS_URL'] = 'redis://localhost:6380/0'
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://brain:brain_dev_pass@localhost:5433/brain_dev'
os.environ['OPENAI_API_KEY'] = 'sk-frRVqh2kFLCj5jpVqyeWR1KDeGAKbqGB9_36dvEG2JT3BlbkFJnPquxB9dtLp-FDjDRD-lQAkJKeIuYTK2dmvs22WJsA'
os.environ['OPENAI_MODEL'] = 'gpt-4o-mini'
os.environ['OPENAI_BASE_URL'] = 'https://api.openai.com/v1'
os.environ['BRAIN_DMZ_GATEWAY_SECRET'] = 'dev-secret-key-12345'
os.environ['AXE_FUSION_ALLOW_LOCAL_REQUESTS'] = 'true'
os.environ['AXE_FUSION_ALLOW_LOCAL_FALLBACK'] = 'true'
os.environ['AXE_CHAT_BRIDGE_FALLBACK_DIRECT'] = 'true'
os.environ['AXE_CHAT_ALLOW_DIRECT_EXECUTION'] = 'true'
os.environ['AXE_CHAT_EXECUTION_PATH'] = 'direct'
os.environ['AXE_ENFORCE_PROVIDER_BINDINGS'] = 'false'

os.chdir('/home/oli/dev/brain-v2/backend')
sys.path.insert(0, '/home/oli/dev/brain-v2/backend')

import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
