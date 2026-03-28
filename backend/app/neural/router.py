"""
Brain 3.0 - Neural Router
=========================

REST API Endpoints for NeuralCore - connected to database
"""

import asyncio
import uuid
from typing import Optional

import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.neural.core import NeuralCore, get_neural_core, ExecutionRequest


router = APIRouter(prefix="/neural", tags=["neural"])


def get_db():
    return AsyncSessionLocal()


class ParameterUpdate(BaseModel):
    key: str
    value: float


class StateUpdate(BaseModel):
    state_name: str
    parameters: dict


class ExecutionRequestInput(BaseModel):
    action: str
    payload: dict = {}
    context: dict = {}


async def get_neural(db: AsyncSession = Depends(get_db)) -> NeuralCore:
    """Dependency for NeuralCore service"""
    return get_neural_core(db)


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive Health Check for Neural Core.
    
    Returns:
        - status: overall health
        - db: database connectivity
        - parameters: number of parameters loaded
        - synapses: number of active synapses
        - states: number of active states
    """
    import logging
    from fastapi.responses import JSONResponse
    logger = logging.getLogger(__name__)
    
    health = {
        "status": "healthy",
        "module": "brain-3",
        "db": "unknown",
        "parameters": 0,
        "synapses": 0,
        "states": 0,
    }
    
    try:
        from sqlalchemy import text
        
        # Check DB
        await db.execute(text("SELECT 1"))
        health["db"] = "connected"
        
        # Count parameters
        result = await db.execute(text("SELECT COUNT(*) FROM brain_parameters"))
        health["parameters"] = result.scalar() or 0
        
        # Count synapses
        result = await db.execute(text("SELECT COUNT(*) FROM neural_synapses WHERE is_active = true"))
        health["synapses"] = result.scalar() or 0
        
        # Count states
        result = await db.execute(text("SELECT COUNT(*) FROM brain_states WHERE is_active = true"))
        health["states"] = result.scalar() or 0
        
        # Overall status
        if health["parameters"] == 0 or health["synapses"] == 0:
            health["status"] = "needs_init"
        else:
            health["status"] = "healthy"
            
    except Exception as e:
        logger.error(f"Neural health check failed: {e}")
        health["status"] = "unhealthy"
        health["error"] = str(e)[:100]
    
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)


@router.post("/init")
async def initialize_neural(db: AsyncSession = Depends(get_db)):
    """
    Initialize Neural Core tables and seed default data.
    
    This endpoint creates the necessary tables and populates them with:
    - Default parameters (creativity, caution, speed, etc.)
    - Default synapses (skill_execute, memory_store, etc.)
    - Default states (default, creative, fast, safe)
    """
    from sqlalchemy import text
    import uuid
    
    results = {"tables_created": [], "data_inserted": []}
    
    # Create tables
    tables = [
        """CREATE TABLE IF NOT EXISTS neural_synapses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            synapse_id VARCHAR(100) NOT NULL UNIQUE,
            source_module VARCHAR(100),
            target_module VARCHAR(100),
            capability VARCHAR(100),
            weight FLOAT DEFAULT 1.0,
            bias FLOAT DEFAULT 0.0,
            input_schema JSONB DEFAULT '{}',
            output_schema JSONB DEFAULT '{}',
            state JSONB DEFAULT '{}',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS brain_states (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            state_name VARCHAR(100) NOT NULL UNIQUE,
            parameters JSONB DEFAULT '{}',
            context JSONB DEFAULT '{}',
            is_active BOOLEAN DEFAULT true,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS brain_parameters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            parameter_key VARCHAR(100) NOT NULL UNIQUE,
            parameter_value JSONB NOT NULL,
            parameter_type VARCHAR(20) DEFAULT 'float',
            min_value FLOAT,
            max_value FLOAT,
            default_value JSONB,
            description TEXT,
            is_mutable BOOLEAN DEFAULT true,
            learning_enabled BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS synapse_executions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            synapse_id VARCHAR(100) NOT NULL,
            input_data JSONB DEFAULT '{}',
            output_data JSONB DEFAULT '{}',
            execution_time_ms FLOAT,
            success BOOLEAN DEFAULT true,
            error_message TEXT,
            parameters JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )"""
    ]
    
    for table_sql in tables:
        try:
            await db.execute(text(table_sql))
            results["tables_created"].append("ok")
        except Exception as e:
            results["tables_created"].append(f"error: {str(e)[:50]}")
    
    await db.commit()
    
    # Insert default parameters
    params = [
        ("creativity", "0.7", "float", "Kreativitäts-Level"),
        ("caution", "0.5", "float", "Vorsicht-Level"),
        ("speed", "0.8", "float", "Geschwindigkeits-Faktor"),
        ("learning_rate", "0.3", "float", "Lernrate"),
        ("execution_timeout", "30", "int", "Timeout in Sekunden"),
        ("max_retries", "3", "int", "Max retries"),
        ("default_weight", "1.0", "float", "Standard-Gewicht"),
        ("default_bias", "0.0", "float", "Standard-Bias"),
    ]
    
    for key, value, ptype, desc in params:
        try:
            await db.execute(text("""
                INSERT INTO brain_parameters (parameter_key, parameter_value, parameter_type, description, is_mutable, learning_enabled)
                VALUES (:key, :value, :type, :desc, true, true)
                ON CONFLICT (parameter_key) DO NOTHING
            """), {"key": key, "value": value, "type": ptype, "desc": desc})
            results["data_inserted"].append(f"param:{key}")
        except:
            pass
    
    # Insert default synapses
    synapses = [
        ("skill_execute", "api", "skill_engine", "execute", 1.0),
        ("skill_list", "api", "skill_engine", "list", 0.9),
        ("memory_store", "api", "memory", "store", 1.0),
        ("memory_recall", "api", "memory", "recall", 1.0),
        ("planning_decompose", "api", "planning", "decompose", 1.0),
        ("policy_evaluate", "api", "policy", "evaluate", 1.0),
        # Odoo ERP synapses
        ("odoo_list_companies", "api", "odoo_adapter", "list_companies", 1.0),
        ("odoo_get_company", "api", "odoo_adapter", "get_company", 1.0),
    ]
    
    for sid, src, tgt, cap, w in synapses:
        try:
            await db.execute(text("""
                INSERT INTO neural_synapses (synapse_id, source_module, target_module, capability, weight, is_active)
                VALUES (:sid, :src, :tgt, :cap, :w, true)
                ON CONFLICT (synapse_id) DO NOTHING
            """), {"sid": sid, "src": src, "tgt": tgt, "cap": cap, "w": w})
            results["data_inserted"].append(f"synapse:{sid}")
        except:
            pass
    
    # Insert default states
    states = [
        ("default", {"creativity": 0.7, "caution": 0.5, "speed": 0.8}, {"mode": "standard"}),
        ("creative", {"creativity": 0.95, "caution": 0.2, "speed": 0.6}, {"mode": "creative"}),
        ("fast", {"creativity": 0.4, "caution": 0.7, "speed": 0.95}, {"mode": "fast"}),
        ("safe", {"creativity": 0.3, "caution": 0.95, "speed": 0.5}, {"mode": "safe"}),
    ]
    
    for name, params, ctx in states:
        try:
            await db.execute(text("""
                INSERT INTO brain_states (state_name, parameters, context, is_active, version)
                VALUES (:name, :params, :ctx, true, 1)
                ON CONFLICT (state_name) DO NOTHING
            """), {"name": name, "params": str(params), "ctx": str(ctx)})
            results["data_inserted"].append(f"state:{name}")
        except:
            pass
    
    await db.commit()
    
    return {"status": "initialized", "result": results}


@router.get("/parameters")
async def list_parameters(neural: NeuralCore = Depends(get_neural)):
    """List all parameters from database"""
    params = await neural.get_all_parameters()
    return {"parameters": params}


@router.get("/parameters/{key}")
async def get_parameter(key: str, neural: NeuralCore = Depends(get_neural)):
    """Get a specific parameter"""
    param = await neural.get_parameter(key)
    if param is None:
        raise HTTPException(status_code=404, detail=f"Parameter {key} not found")
    return {"key": key, "value": param}


@router.post("/parameters")
async def update_parameter(update: ParameterUpdate, neural: NeuralCore = Depends(get_neural)):
    """Update a parameter"""
    success = await neural.set_parameter(update.key, update.value)
    if not success:
        raise HTTPException(status_code=400, detail=f"Parameter {update.key} is not mutable")
    return {"key": update.key, "value": update.value, "status": "updated"}


@router.get("/states")
async def list_states(neural: NeuralCore = Depends(get_neural)):
    """List all states"""
    states = await neural.list_states()
    return {"states": states}


@router.get("/states/{state_name}")
async def get_state(state_name: str, neural: NeuralCore = Depends(get_neural)):
    """Get a state"""
    state = await neural.get_state(state_name)
    if state is None:
        raise HTTPException(status_code=404, detail=f"State {state_name} not found")
    return state


@router.post("/states")
async def update_state(update: StateUpdate, neural: NeuralCore = Depends(get_neural)):
    """Update a state"""
    success = await neural.set_state(update.state_name, update.parameters)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not update state {update.state_name}")
    return {"state_name": update.state_name, "status": "updated"}


@router.post("/execute")
async def execute(request: ExecutionRequestInput, neural: NeuralCore = Depends(get_neural)):
    """Execute an action through the neural network"""
    exec_request = ExecutionRequest(
        action=request.action,
        payload=request.payload,
        context=request.context
    )
    result = await neural.execute(exec_request)
    return result


# Phase 3: SSE für Streaming Updates
EXECUTION_EVENTS: dict[str, asyncio.Queue] = {}


@router.post("/execute/stream")
async def execute_with_stream(
    request: ExecutionRequestInput,
    neural: NeuralCore = Depends(get_neural)
):
    """
    Execute an action with SSE streaming support.
    
    Returns a run_id that can be used to subscribe to updates via /execute/stream/{run_id}
    """
    run_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    EXECUTION_EVENTS[run_id] = queue
    
    async def event_generator():
        import json
        yield f"event: started\ndata: {json.dumps({'run_id': run_id, 'status': 'queued'})}\n\n"
        
        try:
            exec_request = ExecutionRequest(
                action=request.action,
                payload=request.payload,
                context=request.context
            )
            yield f"event: processing\ndata: {json.dumps({'run_id': run_id, 'status': 'executing'})}\n\n"
            
            result = await neural.execute(exec_request)
            
            yield f"event: completed\ndata: {json.dumps({'run_id': run_id, 'result': result.model_dump()})}\n\n"
            
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'run_id': run_id, 'error': str(e)})}\n\n"
        finally:
            if run_id in EXECUTION_EVENTS:
                del EXECUTION_EVENTS[run_id]
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        }
    )


@router.get("/synapses")
async def list_synapses(capability: Optional[str] = None, neural: NeuralCore = Depends(get_neural)):
    """List all synapses"""
    synapses = await neural.list_synapses(capability)
    return {"synapses": [s.model_dump() for s in synapses]}


@router.get("/synapses/{synapse_id}")
async def get_synapse(synapse_id: str, neural: NeuralCore = Depends(get_neural)):
    """Get a synapse"""
    synapse = await neural.get_synapse(synapse_id)
    if synapse is None:
        raise HTTPException(status_code=404, detail=f"Synapse {synapse_id} not found")
    return synapse.model_dump()


@router.get("/stats")
async def get_stats(hours: int = 24, neural: NeuralCore = Depends(get_neural)):
    """Get execution statistics"""
    stats = await neural.get_synapse_stats(hours)
    return {"stats": stats}


@router.post("/learn")
async def trigger_learning(hours: int = 24, neural: NeuralCore = Depends(get_neural)):
    """
    Trigger a learning cycle to analyze past executions and adjust weights.
    
    This analyzes the last {hours} hours of synapse executions and:
    - Increases weights for successful synapses
    - Decreases weights for failed synapses
    - Adjusts global parameters based on patterns
    """
    result = await neural.trigger_learning_cycle(hours)
    return {
        "status": "learning_completed",
        "hours_analyzed": hours,
        "result": result,
    }
