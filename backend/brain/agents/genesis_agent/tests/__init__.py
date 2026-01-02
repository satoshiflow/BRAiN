"""
Tests for Genesis Agent System

This package contains comprehensive tests for the Genesis Agent including:
- DNA schema validation
- Template hash verification
- Customization whitelist enforcement
- Agent creation workflow
- Idempotency
- Event emission
- Budget enforcement
- Kill switch functionality

Run tests:
    pytest backend/brain/agents/genesis_agent/tests/ -v

With coverage:
    pytest backend/brain/agents/genesis_agent/tests/ \
        --cov=backend.brain.agents.genesis_agent \
        --cov-report=html

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""
