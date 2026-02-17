"""
🎯 BRAIN Mission Control Core - Main Integration Module
Complete multi-agent orchestration system

Philosophy: Myzelkapitalismus
- Cooperative multi-agent coordination
- Fair resource allocation and load balancing  
- Transparent event-driven communication
- Self-healing and adaptive task management
"""

import asyncio
import logging
from typing import Optional
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .core.task_queue import TaskQueue
from .core.orchestrator import Orchestrator
from .core.event_stream import EventStream
from .core.mission_control import MissionController
from .api.routes import (
    mission_router, task_router, agent_router, system_router,
    initialize_mission_control_api
)

logger = logging.getLogger(__name__)


class BrainMissionControlCore:
    """
    Main Mission Control Core System
    Integrates all components for production deployment
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        
        # Core components
        self.task_queue: Optional[TaskQueue] = None
        self.orchestrator: Optional[Orchestrator] = None
        self.event_stream: Optional[EventStream] = None
        self.mission_controller: Optional[MissionController] = None
        
        # Runtime state
        self._initialized = False
        self._running = False

    async def initialize(self) -> bool:
        """Initialize all mission control components"""
        if self._initialized:
            return True
            
        try:
            logger.info("Initializing BRAIN Mission Control Core...")
            
            # 1. Initialize Task Queue
            self.task_queue = TaskQueue(self.redis_url)
            await self.task_queue.initialize()
            logger.info("✅ Task Queue initialized")
            
            # 2. Initialize Event Stream
            self.event_stream = EventStream(self.redis_url)
            await self.event_stream.initialize()
            await self.event_stream.start()
            logger.info("✅ Event Stream initialized")
            
            # 3. Initialize Orchestrator
            self.orchestrator = Orchestrator(self.task_queue)
            await self.orchestrator.start()
            logger.info("✅ Orchestrator initialized")
            
            # 4. Initialize Mission Controller
            self.mission_controller = MissionController(
                self.task_queue,
                self.orchestrator, 
                self.event_stream
            )
            await self.mission_controller.start_monitoring()
            logger.info("✅ Mission Controller initialized")
            
            self._initialized = True
            logger.info("🚀 BRAIN Mission Control Core fully initialized!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Mission Control Core: {e}")
            await self.cleanup()
            return False

    async def start(self) -> bool:
        """Start all mission control services"""
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return False
                
        if self._running:
            return True
            
        try:
            self._running = True
            logger.info("🎯 Mission Control Core started and ready for missions!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Mission Control Core: {e}")
            return False

    async def stop(self) -> None:
        """Stop all mission control services"""
        if not self._running:
            return
            
        logger.info("Stopping Mission Control Core...")
        
        try:
            if self.mission_controller:
                await self.mission_controller.stop_monitoring()
                
            if self.orchestrator:
                await self.orchestrator.stop()
                
            if self.event_stream:
                await self.event_stream.stop()
                
            self._running = False
            logger.info("Mission Control Core stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Mission Control Core: {e}")

    async def cleanup(self) -> None:
        """Clean up resources"""
        await self.stop()
        self._initialized = False

    async def health_check(self) -> dict:
        """Get system health status"""
        try:
            health = {
                "status": "healthy" if self._running else "stopped",
                "initialized": self._initialized,
                "running": self._running,
                "components": {}
            }
            
            if self._initialized:
                # Check task queue
                if self.task_queue:
                    queue_stats = await self.task_queue.get_queue_stats()
                    health["components"]["task_queue"] = {
                        "status": "healthy",
                        "stats": queue_stats
                    }
                
                # Check orchestrator
                if self.orchestrator:
                    orch_stats = await self.orchestrator.get_orchestrator_stats()
                    health["components"]["orchestrator"] = {
                        "status": "healthy", 
                        "stats": orch_stats
                    }
                
                # Check event stream
                if self.event_stream:
                    stream_stats = await self.event_stream.get_stream_stats()
                    health["components"]["event_stream"] = {
                        "status": "healthy",
                        "stats": stream_stats
                    }
            
            return health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "initialized": self._initialized,
                "running": self._running
            }


# FastAPI integration
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    # Startup
    mission_control = BrainMissionControlCore()
    success = await mission_control.start()
    
    if not success:
        logger.error("Failed to start Mission Control Core")
        raise RuntimeError("Mission Control startup failed")
    
    # Initialize API with components
    await initialize_mission_control_api(
        mission_control.mission_controller,
        mission_control.task_queue,
        mission_control.orchestrator,
        mission_control.event_stream
    )
    
    # Store in app state
    app.state.mission_control = mission_control
    
    yield
    
    # Shutdown
    await mission_control.cleanup()


def create_mission_control_app(redis_url: str = "redis://localhost:6379") -> FastAPI:
    """Create FastAPI app with Mission Control integrated"""
    
    app = FastAPI(
        title="BRAIN Mission Control Core",
        description="Bio-Inspired Multi-Agent Orchestration System",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Include routers
    app.include_router(mission_router)
    app.include_router(task_router)
    app.include_router(agent_router)
    app.include_router(system_router)
    
    @app.get("/health")
    async def health_endpoint():
        """Health check endpoint"""
        try:
            mission_control = app.state.mission_control
            return await mission_control.health_check()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "service": "BRAIN Mission Control Core",
            "version": "1.0.0",
            "philosophy": "Myzelkapitalismus - Cooperative Multi-Agent Intelligence",
            "status": "ready",
            "endpoints": {
                "docs": "/docs",
                "health": "/health",
                "missions": "/api/v1/missions",
                "tasks": "/api/v1/tasks", 
                "agents": "/api/v1/agents",
                "system": "/api/v1/system",
                "websocket": "/api/v1/system/ws"
            }
        }
    
    return app


# Export main classes
__all__ = [
    'BrainMissionControlCore',
    'create_mission_control_app'
]
