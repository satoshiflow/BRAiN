"""
Genesis Agent API Module

This package provides REST API endpoints for the Genesis Agent System.

Endpoints:
- POST /api/genesis/create: Create a new agent
- GET /api/genesis/info: Get system information
- GET /api/genesis/templates: List available templates
- GET /api/genesis/customizations: Get customization help
- GET /api/genesis/budget: Check budget availability
- POST /api/genesis/killswitch: Toggle kill switch

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from .routes import router

__all__ = ["router"]
