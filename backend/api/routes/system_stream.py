"""
System Stream API - Server-Sent Events (SSE) for real-time updates
Provides health, telemetry, and system status updates via SSE
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
import json
import time
import psutil
from loguru import logger

router = APIRouter(prefix="/api/system", tags=["system-stream"])


async def health_event_generator() -> AsyncGenerator[str, None]:
    """Generate health/telemetry events for SSE"""
    logger.info("SSE client connected to health stream")

    try:
        while True:
            # Get real system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            health_data = {
                "channel": "health",
                "event_type": "health_update",
                "timestamp": time.time(),
                "data": {
                    "status": "healthy",
                    "cpu_usage": cpu_percent,
                    "memory_usage_mb": memory.used / (1024 * 1024),
                    "memory_percent": memory.percent,
                    "disk_usage_percent": disk.percent,
                }
            }

            yield f"data: {json.dumps(health_data)}\n\n"
            await asyncio.sleep(5)  # Update every 5 seconds

    except asyncio.CancelledError:
        logger.info("SSE client disconnected from health stream")
        raise


@router.get("/stream")
async def stream_health_events():
    """
    SSE endpoint for health/telemetry updates

    Streams real-time system metrics every 5 seconds:
    - CPU usage
    - Memory usage
    - Disk usage

    **Usage:**
    ```typescript
    const eventSource = new EventSource('/api/system/stream');
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Health update:', data);
    };
    ```
    """
    return StreamingResponse(
        health_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/stream/test")
async def test_sse_connection():
    """Test SSE connection with a simple counter"""
    async def test_generator():
        for i in range(10):
            yield f"data: {json.dumps({'count': i, 'timestamp': time.time()})}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        test_generator(),
        media_type="text/event-stream"
    )
