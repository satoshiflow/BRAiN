"""
Brain 3.0 - Neural State Architecture
=====================================

Das "Gehirn" von BRAiN 3.0

Konzepte:
- Synapse: Eine Verbindung zwischen Input und Output
- Parameter: Die "Gewichte" die bestimmen wie Synapsen funktionieren
- State: Der aktuelle Zustand des Systems

Verwendung:
    from app.neural import NeuralCore, get_neural_core
    
    core = get_neural_core(db)
    result = await core.execute(ExecutionRequest(action="skill_execute", payload={}))
"""

from .core import (
    NeuralCore,
    get_neural_core,
    NeuralSynapseORM,
    BrainStateORM,
    BrainParameterORM,
    SynapseExecutionORM,
    SynapseCreate,
    SynapseResponse,
    ParameterCreate,
    ParameterResponse,
    ExecutionRequest,
    ExecutionResponse,
)

__all__ = [
    "NeuralCore",
    "get_neural_core",
    "NeuralSynapseORM",
    "BrainStateORM", 
    "BrainParameterORM",
    "SynapseExecutionORM",
    "SynapseCreate",
    "SynapseResponse",
    "ParameterCreate",
    "ParameterResponse",
    "ExecutionRequest",
    "ExecutionResponse",
]
