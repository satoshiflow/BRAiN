"""
Agent Operations API

Endpoints for interacting with the new constitutional agents:
- SupervisorAgent
- CoderAgent
- OpsAgent
- ArchitectAgent
- AXEAgent
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from backend.brain.agents.supervisor_agent import get_supervisor_agent
from backend.brain.agents.coder_agent import get_coder_agent
from backend.brain.agents.ops_agent import get_ops_agent
from backend.brain.agents.architect_agent import get_architect_agent
from backend.brain.agents.axe_agent import get_axe_agent
from backend.brain.agents.research_agent import get_research_agent, ResearchType
from backend.brain.agents.test_agent import get_test_agent, TestType, TestEnvironment
from backend.brain.agents.documentation_agent import get_documentation_agent, DocumentationType, DocumentationFormat
from app.modules.supervisor.schemas import (
    RiskLevel,
    SupervisionRequest,
    SupervisionResponse,
)


router = APIRouter(prefix="/api/agent-ops", tags=["agent-operations"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class SuperviseActionRequest(BaseModel):
    """Request to supervise an action"""
    requesting_agent: str = Field(..., description="Agent requesting supervision")
    action: str = Field(..., description="Action to supervise")
    context: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel
    reason: Optional[str] = None


class GenerateCodeRequest(BaseModel):
    """Request to generate code"""
    spec: str = Field(..., description="Code specification/description")
    risk_level: Optional[RiskLevel] = None


class GenerateOdooModuleRequest(BaseModel):
    """Request to generate Odoo module"""
    name: str
    purpose: str
    data_types: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    views: List[str] = Field(default_factory=list)


class DeployApplicationRequest(BaseModel):
    """Request to deploy application"""
    app_name: str
    version: str
    environment: str = Field(..., description="dev/staging/production")
    config: Optional[Dict[str, Any]] = None


class ReviewArchitectureRequest(BaseModel):
    """Request architecture review"""
    system_name: str
    architecture_spec: Dict[str, Any]
    high_risk_ai: bool = False


class ChatRequest(BaseModel):
    """Chat with AXE agent"""
    message: str
    context: Optional[Dict[str, Any]] = None
    include_history: bool = True


# ============================================================================
# SupervisorAgent Endpoints
# ============================================================================


@router.post("/supervisor/supervise", response_model=SupervisionResponse)
async def supervise_action(request: SuperviseActionRequest):
    """
    Request supervision for an agent action.

    Evaluates the action through:
    - Risk-based rules
    - Policy Engine
    - Constitutional LLM check
    - Foundation layer safety

    Returns approval/denial with reasoning.
    """
    try:
        supervisor = get_supervisor_agent()

        supervision_request = SupervisionRequest(
            requesting_agent=request.requesting_agent,
            action=request.action,
            context=request.context,
            risk_level=request.risk_level,
            reason=request.reason,
        )

        response = await supervisor.supervise_action(supervision_request)

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Supervision failed: {str(e)}"
        )


@router.get("/supervisor/metrics")
async def get_supervisor_metrics():
    """Get supervision metrics"""
    try:
        supervisor = get_supervisor_agent()
        return supervisor.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CoderAgent Endpoints
# ============================================================================


@router.post("/coder/generate-code")
async def generate_code(request: GenerateCodeRequest):
    """
    Generate code with DSGVO compliance checks.

    HIGH-risk code requires supervisor approval.
    """
    try:
        coder = get_coder_agent()

        result = await coder.generate_code(
            spec=request.spec,
            risk_level=request.risk_level,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Code generation failed: {str(e)}"
        )


@router.post("/coder/generate-odoo-module")
async def generate_odoo_module(request: GenerateOdooModuleRequest):
    """
    Generate DSGVO-compliant Odoo module.

    Automatically assesses risk based on data types.
    Personal data → HIGH risk → supervisor approval required.
    """
    try:
        coder = get_coder_agent()

        result = await coder.generate_odoo_module({
            "name": request.name,
            "purpose": request.purpose,
            "data_types": request.data_types,
            "models": request.models,
            "views": request.views,
        })

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Odoo module generation failed: {str(e)}"
        )


# ============================================================================
# OpsAgent Endpoints
# ============================================================================


@router.post("/ops/deploy")
async def deploy_application(request: DeployApplicationRequest):
    """
    Deploy application to specified environment.

    Production deployments require supervisor approval (CRITICAL risk).
    Includes automatic:
    - Pre-deployment checks
    - Backup creation
    - Health monitoring
    - Rollback on failure
    """
    try:
        ops = get_ops_agent()

        result = await ops.deploy_application(
            app_name=request.app_name,
            version=request.version,
            environment=request.environment,
            config=request.config,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Deployment failed: {str(e)}"
        )


@router.post("/ops/rollback")
async def rollback_deployment(
    app_name: str = Body(...),
    environment: str = Body(...),
    backup_id: str = Body(...),
):
    """Rollback deployment to previous version"""
    try:
        ops = get_ops_agent()

        result = await ops.rollback_deployment(
            app_name=app_name,
            environment=environment,
            backup_id=backup_id,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ops/health/{app_name}/{environment}")
async def check_application_health(app_name: str, environment: str):
    """Check application health"""
    try:
        ops = get_ops_agent()

        result = await ops.health_check(app_name, environment)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ArchitectAgent Endpoints
# ============================================================================


@router.post("/architect/review")
async def review_architecture(request: ReviewArchitectureRequest):
    """
    Comprehensive architecture review with EU compliance.

    Checks:
    - EU AI Act compliance
    - DSGVO compliance
    - Scalability
    - Security
    - Best practices

    Returns compliance score and recommendations.
    """
    try:
        architect = get_architect_agent()

        result = await architect.review_architecture(
            system_name=request.system_name,
            architecture_spec=request.architecture_spec,
            high_risk_ai=request.high_risk_ai,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Architecture review failed: {str(e)}"
        )


@router.post("/architect/compliance-check")
async def check_eu_compliance(architecture_spec: Dict[str, Any] = Body(...)):
    """Quick EU compliance check (AI Act + DSGVO)"""
    try:
        architect = get_architect_agent()

        result = await architect.check_eu_compliance(architecture_spec)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/architect/scalability-assessment")
async def assess_scalability(architecture_spec: Dict[str, Any] = Body(...)):
    """Assess system scalability"""
    try:
        architect = get_architect_agent()

        result = await architect.assess_scalability(architecture_spec)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/architect/security-audit")
async def audit_security(architecture_spec: Dict[str, Any] = Body(...)):
    """Security architecture audit"""
    try:
        architect = get_architect_agent()

        result = await architect.audit_security(architecture_spec)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AXEAgent Endpoints
# ============================================================================


@router.post("/axe/chat")
async def chat_with_axe(request: ChatRequest):
    """
    Chat with AXE conversational assistant.

    Context-aware with conversation history.
    Can query system status, analyze logs, execute safe commands.
    """
    try:
        axe = get_axe_agent()

        result = await axe.chat(
            message=request.message,
            context=request.context,
            include_history=request.include_history,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/axe/system-status")
async def get_system_status():
    """Get current system status via AXE"""
    try:
        axe = get_axe_agent()

        result = await axe.get_system_status()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/axe/history")
async def clear_axe_history():
    """Clear AXE conversation history"""
    try:
        axe = get_axe_agent()
        axe.clear_history()

        return {"message": "Conversation history cleared"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Agent Info Endpoints
# ============================================================================


@router.get("/info")
async def get_agents_info():
    """Get information about all constitutional agents"""
    return {
        "name": "Constitutional Agents",
        "version": "1.0.0",
        "agents": [
            {
                "id": "supervisor",
                "name": "SupervisorAgent",
                "role": "Constitutional Guardian",
                "capabilities": ["risk_assessment", "policy_evaluation", "human_oversight"],
            },
            {
                "id": "coder",
                "name": "CoderAgent",
                "role": "Secure Code Generation",
                "capabilities": ["code_generation", "odoo_modules", "dsgvo_compliance"],
            },
            {
                "id": "ops",
                "name": "OpsAgent",
                "role": "Operations & Deployment",
                "capabilities": ["deployment", "rollback", "health_monitoring"],
            },
            {
                "id": "architect",
                "name": "ArchitectAgent",
                "role": "Architecture & Compliance Auditor",
                "capabilities": ["architecture_review", "eu_compliance", "security_audit"],
            },
            {
                "id": "axe",
                "name": "AXEAgent",
                "role": "Conversational Assistant",
                "capabilities": ["chat", "system_monitoring", "log_analysis"],
            },
            {
                "id": "research",
                "name": "ResearchAgent",
                "role": "Information Research & Analysis",
                "capabilities": ["web_search", "document_analysis", "source_validation", "data_gathering"],
            },
            {
                "id": "test",
                "name": "TestAgent",
                "role": "Automated Testing & QA",
                "capabilities": ["test_generation", "test_execution", "coverage_analysis", "bug_detection"],
            },
            {
                "id": "documentation",
                "name": "DocumentationAgent",
                "role": "Documentation Generation",
                "capabilities": ["api_docs", "readme", "code_comments", "user_guides"],
            },
        ],
        "compliance_frameworks": ["DSGVO", "EU AI Act"],
        "endpoints": {
            "supervisor": ["/supervise", "/metrics"],
            "coder": ["/generate-code", "/generate-odoo-module"],
            "ops": ["/deploy", "/rollback", "/health"],
            "architect": ["/review", "/compliance-check", "/security-audit"],
            "axe": ["/chat", "/system-status"],
            "research": ["/research", "/validate-source"],
            "test": ["/generate-tests", "/run-tests"],
            "documentation": ["/generate-docs"],
        }
    }


# ============================================================================
# ResearchAgent Endpoints
# ============================================================================

class ResearchRequest(BaseModel):
    """Request to conduct research"""
    task: str = Field(..., description="Research task description")
    research_type: ResearchType = Field(default=ResearchType.WEB_SEARCH)
    sources: Optional[List[str]] = None
    max_results: int = Field(default=10, ge=1, le=50)
    include_personal_data: bool = Field(default=False)


@router.post("/research/research")
async def conduct_research(request: ResearchRequest):
    """
    Conduct research using ResearchAgent.

    Risk levels:
    - LOW: Document analysis (read-only)
    - MEDIUM: Web search, data gathering (validation required)
    - HIGH: Personal data gathering (DSGVO Art. 5, 6 - Human approval required)
    """
    agent = get_research_agent()
    result = await agent.run(
        task=request.task,
        research_type=request.research_type,
        sources=request.sources or [],
        max_results=request.max_results,
        include_personal_data=request.include_personal_data
    )
    return result


@router.post("/research/validate-source")
async def validate_source(source_url: str = Body(..., embed=True)):
    """Validate credibility of information source"""
    agent = get_research_agent()
    result = await agent._validate_source(source_url)
    return result


# ============================================================================
# TestAgent Endpoints
# ============================================================================

class GenerateTestsRequest(BaseModel):
    """Request to generate tests"""
    code_path: str = Field(..., description="Path to code to test")
    test_type: TestType = Field(default=TestType.UNIT_TEST)


class RunTestsRequest(BaseModel):
    """Request to run tests"""
    task: str = Field(..., description="Testing task description")
    test_type: TestType = Field(default=TestType.UNIT_TEST)
    environment: TestEnvironment = Field(default=TestEnvironment.LOCAL)
    code_path: str = Field(..., description="Path to code to test")
    test_files: List[str] = Field(default_factory=list)
    run_tests: bool = Field(default=True)


@router.post("/test/generate-tests")
async def generate_tests(request: GenerateTestsRequest):
    """
    Generate tests using TestAgent.

    Risk level: LOW (code analysis only, no execution)
    """
    agent = get_test_agent()
    result = await agent.run(
        task=f"Generate {request.test_type.value} tests for {request.code_path}",
        test_type=request.test_type,
        code_path=request.code_path,
        run_tests=False
    )
    return result


@router.post("/test/run-tests")
async def run_tests(request: RunTestsRequest):
    """
    Run tests using TestAgent.

    Risk levels:
    - LOW: Local execution
    - MEDIUM: Dev/staging execution
    - CRITICAL: Production execution (Human approval required)
    """
    agent = get_test_agent()
    result = await agent.run(
        task=request.task,
        test_type=request.test_type,
        environment=request.environment,
        code_path=request.code_path,
        test_files=request.test_files,
        run_tests=request.run_tests
    )
    return result


# ============================================================================
# DocumentationAgent Endpoints
# ============================================================================

class GenerateDocsRequest(BaseModel):
    """Request to generate documentation"""
    task: str = Field(..., description="Documentation task description")
    doc_type: DocumentationType = Field(default=DocumentationType.README)
    output_format: DocumentationFormat = Field(default=DocumentationFormat.MARKDOWN)
    code_path: Optional[str] = None
    auto_commit: bool = Field(default=False)


@router.post("/documentation/generate-docs")
async def generate_documentation(request: GenerateDocsRequest):
    """
    Generate documentation using DocumentationAgent.

    Risk levels:
    - LOW: Documentation generation (non-destructive)
    - MEDIUM: Auto-commit to repository (requires approval)
    """
    agent = get_documentation_agent()
    result = await agent.run(
        task=request.task,
        doc_type=request.doc_type,
        output_format=request.output_format,
        code_path=request.code_path or "",
        auto_commit=request.auto_commit
    )
    return result
