"""
Physical Agents Gateway Module

Secure gateway for physical agents, IoT devices, and robotics systems.

Features:
- MLP/Builder Toolkit Integration
- Physical agent connectivity
- IoT/Robotics interfaces
- Secure remote control
- Standardized communication protocols
- Audit trail and compliance
"""

from .service import PhysicalGatewayService, get_physical_gateway_service
from .schemas import (
    GatewayInfo,
    PhysicalAgentInfo,
    PhysicalAgentState,
    GatewayCommand,
    CommandResponse,
    AgentCapability,
)

__all__ = [
    "PhysicalGatewayService",
    "get_physical_gateway_service",
    "GatewayInfo",
    "PhysicalAgentInfo",
    "PhysicalAgentState",
    "GatewayCommand",
    "CommandResponse",
    "AgentCapability",
]
