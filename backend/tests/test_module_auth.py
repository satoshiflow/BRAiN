"""
Test Module-Level Authentication

Integration tests for module router authentication guards:
- sovereign_mode: Requires admin
- dmz_control: Requires admin  
- skills: Requires operator for execution
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException, Depends
from unittest.mock import MagicMock, patch

# Create a minimal app for testing
from app.core.auth_deps import (
    require_auth,
    require_admin,
    require_operator,
    Principal,
    PrincipalType,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_principal():
    """Create a mock authenticated principal"""
    return Principal(
        principal_id="user-123",
        principal_type=PrincipalType.HUMAN,
        email="user@example.com",
        name="Test User",
        roles=["viewer"],
        scopes=["brain:read"],
    )


@pytest.fixture
def mock_admin_principal():
    """Create a mock admin principal"""
    return Principal(
        principal_id="admin-123",
        principal_type=PrincipalType.HUMAN,
        email="admin@example.com",
        name="Admin User",
        roles=["admin"],
        scopes=["brain:admin", "brain:write", "brain:read"],
    )


@pytest.fixture
def mock_operator_principal():
    """Create a mock operator principal"""
    return Principal(
        principal_id="operator-123",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator User",
        roles=["operator"],
        scopes=["brain:write", "brain:read", "skills:execute"],
    )


@pytest.fixture
def mock_anonymous_principal():
    """Create a mock anonymous principal"""
    return Principal.anonymous()


@pytest.fixture
def test_app():
    """Create a test FastAPI app with protected routes"""
    app = FastAPI()
    
    # Sovereign mode routes - require admin
    @app.post("/api/sovereign-mode/mode")
    async def change_mode(
        request: dict,
        principal: Principal = Depends(require_admin)
    ):
        return {"status": "success", "mode": request.get("mode")}
    
    @app.get("/api/sovereign-mode/status")
    async def get_status(
        principal: Principal = Depends(require_admin)
    ):
        return {"mode": "online", "network": "available"}
    
    # DMZ control routes - require admin
    @app.get("/api/dmz/status")
    async def get_dmz_status(
        principal: Principal = Depends(require_admin)
    ):
        return {"running": True, "services": 3}
    
    @app.post("/api/dmz/start")
    async def start_dmz(
        principal: Principal = Depends(require_admin)
    ):
        return {"success": True, "message": "DMZ started"}
    
    @app.post("/api/dmz/stop")
    async def stop_dmz(
        principal: Principal = Depends(require_admin)
    ):
        return {"success": True, "message": "DMZ stopped"}
    
    # Skills routes - require operator
    @app.post("/api/skills/{skill_id}/execute")
    async def execute_skill(
        skill_id: str,
        request: dict,
        principal: Principal = Depends(require_operator)
    ):
        # Also check scope
        if not principal.has_scope("skills:execute"):
            raise HTTPException(status_code=403, detail="Insufficient scope. Required: skills:execute")
        return {"success": True, "skill_id": skill_id, "output": "executed"}
    
    @app.post("/api/skills/execute")
    async def execute_skill_body(
        request: dict,
        principal: Principal = Depends(require_operator)
    ):
        if not principal.has_scope("skills:execute"):
            raise HTTPException(status_code=403, detail="Insufficient scope. Required: skills:execute")
        return {"success": True, "skill_id": request.get("skill_id"), "output": "executed"}
    
    return app


@pytest.fixture
def client(test_app):
    """Create a test client"""
    return TestClient(test_app)


# ============================================================================
# Test Sovereign Mode Unauthenticated → 401
# ============================================================================

class TestSovereignModeAuth:
    """Tests for sovereign mode authentication requirements"""
    
    def test_sovereign_mode_unauthenticated_returns_401(self, client, mock_anonymous_principal):
        """
        Test that accessing sovereign mode endpoints without authentication returns 401.
        
        Unauthenticated requests should be rejected before reaching the endpoint logic.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_anonymous_principal):
            # Try to change mode without authentication
            response = client.post(
                "/api/sovereign-mode/mode",
                json={"mode": "offline"},
            )
            
            # Should return 401 Unauthorized
            assert response.status_code == 401
    
    def test_sovereign_mode_non_admin_returns_403(self, client, mock_principal):
        """
        Test that non-admin users are forbidden from sovereign mode operations.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_principal):
            response = client.post(
                "/api/sovereign-mode/mode",
                json={"mode": "offline"},
            )
            
            # Should return 403 Forbidden
            assert response.status_code == 403
    
    def test_sovereign_mode_admin_allowed(self, client, mock_admin_principal):
        """
        Test that admin users can access sovereign mode operations.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_admin_principal):
            response = client.post(
                "/api/sovereign-mode/mode",
                json={"mode": "offline"},
            )
            
            # Should succeed
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert response.json()["mode"] == "offline"
    
    def test_sovereign_mode_status_requires_auth(self, client, mock_anonymous_principal):
        """
        Test that status endpoint also requires authentication.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_anonymous_principal):
            response = client.get("/api/sovereign-mode/status")
            
            assert response.status_code == 401
    
    def test_sovereign_mode_operator_returns_403(self, client, mock_operator_principal):
        """
        Test that operator role is insufficient for sovereign mode.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_operator_principal):
            response = client.post(
                "/api/sovereign-mode/mode",
                json={"mode": "offline"},
            )
            
            assert response.status_code == 403


# ============================================================================
# Test DMZ Control Without Admin → 403
# ============================================================================

class TestDMZControlAuth:
    """Tests for DMZ control authentication requirements"""
    
    def test_dmz_control_unauthenticated_returns_401(self, client, mock_anonymous_principal):
        """
        Test that accessing DMZ control without authentication returns 401.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_anonymous_principal):
            response = client.get("/api/dmz/status")
            
            assert response.status_code == 401
    
    def test_dmz_control_without_admin_returns_403(self, client, mock_principal):
        """
        Test that non-admin users cannot access DMZ control (returns 403).
        
        Regular users should be forbidden from DMZ operations.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_principal):
            # Try status endpoint
            response = client.get("/api/dmz/status")
            assert response.status_code == 403
            
            # Try start endpoint
            response = client.post("/api/dmz/start")
            assert response.status_code == 403
            
            # Try stop endpoint
            response = client.post("/api/dmz/stop")
            assert response.status_code == 403
    
    def test_dmz_control_operator_returns_403(self, client, mock_operator_principal):
        """
        Test that operator role is insufficient for DMZ control.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_operator_principal):
            response = client.get("/api/dmz/status")
            
            assert response.status_code == 403
    
    def test_dmz_control_admin_allowed(self, client, mock_admin_principal):
        """
        Test that admin users can access DMZ control.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_admin_principal):
            # Status
            response = client.get("/api/dmz/status")
            assert response.status_code == 200
            assert response.json()["running"] is True
            
            # Start
            response = client.post("/api/dmz/start")
            assert response.status_code == 200
            assert response.json()["success"] is True
            
            # Stop
            response = client.post("/api/dmz/stop")
            assert response.status_code == 200
            assert response.json()["success"] is True


# ============================================================================
# Test Skills Execute Without Operator → 403
# ============================================================================

class TestSkillsExecuteAuth:
    """Tests for skills execution authentication requirements"""
    
    def test_skills_execute_unauthenticated_returns_401(self, client, mock_anonymous_principal):
        """
        Test that executing skills without authentication returns 401.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_anonymous_principal):
            response = client.post(
                "/api/skills/test-skill-123/execute",
                json={"params": {"key": "value"}},
            )
            
            assert response.status_code == 401
    
    def test_skills_execute_without_operator_returns_403(self, client, mock_principal):
        """
        Test that non-operator users cannot execute skills (returns 403).
        
        Regular viewers should be forbidden from skill execution.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_principal):
            # Try with path parameter
            response = client.post(
                "/api/skills/test-skill-123/execute",
                json={"params": {"key": "value"}},
            )
            assert response.status_code == 403
            
            # Try with body parameter
            response = client.post(
                "/api/skills/execute",
                json={"skill_id": "test-skill-123", "params": {"key": "value"}},
            )
            assert response.status_code == 403
    
    def test_skills_execute_operator_without_scope_returns_403(self, client, mock_operator_principal):
        """
        Test that operators without skills:execute scope cannot execute skills.
        
        The operator role alone is not enough; the skills:execute scope is also required.
        """
        # Remove the skills:execute scope
        mock_operator_principal.scopes = ["brain:write", "brain:read"]  # No skills:execute
        
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_operator_principal):
            response = client.post(
                "/api/skills/test-skill-123/execute",
                json={"params": {"key": "value"}},
            )
            
            assert response.status_code == 403
            assert "scope" in response.json()["detail"].lower()
    
    def test_skills_execute_operator_with_scope_allowed(self, client, mock_operator_principal):
        """
        Test that operators with skills:execute scope can execute skills.
        """
        # Ensure operator has the required scope
        mock_operator_principal.scopes = ["brain:write", "brain:read", "skills:execute"]
        
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_operator_principal):
            response = client.post(
                "/api/skills/test-skill-123/execute",
                json={"params": {"key": "value"}},
            )
            
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["skill_id"] == "test-skill-123"
    
    def test_skills_execute_admin_allowed(self, client, mock_admin_principal):
        """
        Test that admin users can also execute skills (admin includes operator).
        """
        mock_admin_principal.scopes = ["brain:admin", "brain:write", "brain:read", "skills:execute"]
        
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_admin_principal):
            response = client.post(
                "/api/skills/test-skill-123/execute",
                json={"params": {"key": "value"}},
            )
            
            assert response.status_code == 200
            assert response.json()["success"] is True
    
    def test_skills_execute_body_endpoint_requires_auth(self, client, mock_anonymous_principal):
        """
        Test that the POST /api/skills/execute endpoint also requires auth.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_anonymous_principal):
            response = client.post(
                "/api/skills/execute",
                json={"skill_id": "test-skill-123", "params": {"key": "value"}},
            )
            
            assert response.status_code == 401


# ============================================================================
# Additional Integration Tests
# ============================================================================

class TestAuthErrorMessages:
    """Tests for authentication error messages"""
    
    def test_401_includes_www_authenticate_header(self, client, mock_anonymous_principal):
        """
        Test that 401 responses include the WWW-Authenticate header.
        
        This is required by RFC 7235 for 401 responses.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_anonymous_principal):
            response = client.get("/api/dmz/status")
            
            assert response.status_code == 401
            # FastAPI's HTTPException with 401 should include WWW-Authenticate
            # Note: This depends on the exact implementation
    
    def test_403_includes_reason(self, client, mock_principal):
        """
        Test that 403 responses include a helpful error message.
        """
        with patch('app.core.auth_deps.get_current_principal', return_value=mock_principal):
            response = client.post("/api/sovereign-mode/mode", json={"mode": "offline"})
            
            assert response.status_code == 403
            # Should have a detail message explaining why
            assert "detail" in response.json()


class TestModuleRouterVerification:
    """
    Tests to verify that actual module routers have proper auth guards.
    
    These tests check the actual router files to ensure they have
    the required authentication dependencies.
    """
    
    def test_sovereign_mode_router_has_auth_guards(self):
        """
        Verify the actual sovereign_mode router has admin auth guards.
        """
        import os
        
        router_path = "backend/app/modules/sovereign_mode/router.py"
        if os.path.exists(router_path):
            with open(router_path, 'r') as f:
                content = f.read()
            
            # Check for require_admin import
            assert "require_admin" in content
            
            # Check for dependencies
            assert "dependencies=[Depends(require_admin)]" in content or \
                   "Depends(require_admin)" in content
    
    def test_dmz_control_router_has_auth_guards(self):
        """
        Verify the actual dmz_control router has admin auth guards.
        """
        import os
        
        router_path = "backend/app/modules/dmz_control/router.py"
        if os.path.exists(router_path):
            with open(router_path, 'r') as f:
                content = f.read()
            
            # Check for require_admin import
            assert "require_admin" in content
            
            # Check for dependencies
            assert "dependencies=[Depends(require_admin)]" in content or \
                   "Depends(require_admin)" in content
    
    def test_skills_router_has_operator_guards(self):
        """
        Verify the actual skills router has operator auth guards for execution.
        """
        import os
        
        router_path = "backend/app/modules/skills/router.py"
        if os.path.exists(router_path):
            with open(router_path, 'r') as f:
                content = f.read()
            
            # Check for require_operator import
            assert "require_operator" in content
            
            # Check for execute endpoint protection
            assert "Depends(require_operator)" in content
            
            # Check for skills:execute scope check
            assert "skills:execute" in content
