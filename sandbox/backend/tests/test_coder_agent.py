"""
Tests for CoderAgent

Tests secure code generation with supervisor integration.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from brain.agents.coder_agent import (
    CoderAgent,
    CodeGenerationError,
    SupervisionDeniedError,
    HumanApprovalRequiredError,
)
from app.modules.supervisor.schemas import RiskLevel


@pytest.fixture
def mock_llm_client():
    client = Mock()
    client.generate = AsyncMock(return_value="def hello():\n    return 'Hello World'")
    return client


@pytest.fixture
def coder_agent(mock_llm_client):
    return CoderAgent(llm_client=mock_llm_client)


# ============================================================================
# Initialization Tests
# ============================================================================


def test_coder_agent_initialization(coder_agent):
    """Test CoderAgent initializes with correct config"""
    assert coder_agent.config.name == "CoderAgent"
    assert coder_agent.config.role == "CODER"
    assert coder_agent.config.temperature == 0.3
    assert "CODE_GENERATE" in coder_agent.config.permissions


# ============================================================================
# Risk Assessment Tests
# ============================================================================


def test_assess_code_risk_high_for_personal_data(coder_agent):
    """Test personal data triggers HIGH risk"""
    spec = {
        "name": "customer_portal",
        "data_types": ["customer_email", "user_name"],
    }

    risk = coder_agent._assess_code_risk(spec)
    assert risk == RiskLevel.HIGH


def test_assess_code_risk_medium_for_database(coder_agent):
    """Test database operations trigger MEDIUM risk"""
    spec = {
        "name": "data_processor",
        "purpose": "database migration",
        "data_types": [],
    }

    risk = coder_agent._assess_code_risk(spec)
    assert risk == RiskLevel.MEDIUM


def test_assess_code_risk_low_for_utility(coder_agent):
    """Test utility functions are LOW risk"""
    spec = {
        "name": "string_utils",
        "purpose": "string manipulation",
        "data_types": [],
    }

    risk = coder_agent._assess_code_risk(spec)
    assert risk == RiskLevel.LOW


def test_contains_personal_data_detection(coder_agent):
    """Test personal data keyword detection"""
    assert coder_agent._contains_personal_data(["customer_email"]) is True
    assert coder_agent._contains_personal_data(["user_name"]) is True
    assert coder_agent._contains_personal_data(["phone_number"]) is True
    assert coder_agent._contains_personal_data(["product_id"]) is False


# ============================================================================
# Code Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_code_detects_eval(coder_agent):
    """Test validation detects forbidden eval()"""
    code = "result = eval(user_input)"

    validation = await coder_agent.validate_code(code)

    assert validation["valid"] is False
    assert any("eval()" in issue for issue in validation["issues"])


@pytest.mark.asyncio
async def test_validate_code_detects_hardcoded_password(coder_agent):
    """Test validation detects hardcoded passwords"""
    code = 'password = "admin123"'

    validation = await coder_agent.validate_code(code)

    assert validation["valid"] is False
    assert any("password" in issue.lower() for issue in validation["issues"])


@pytest.mark.asyncio
async def test_validate_code_requires_gdpr_comments(coder_agent):
    """Test validation requires DSGVO comments for personal data"""
    code = """
def process_user_data(user_email):
    return user_email.lower()
"""

    validation = await coder_agent.validate_code(code)

    assert validation["valid"] is False
    assert any("DSGVO" in issue for issue in validation["issues"])


@pytest.mark.asyncio
async def test_validate_code_passes_clean_code(coder_agent):
    """Test validation passes for clean code"""
    code = """
# DSGVO Art. 6: Processing with user consent
def process_user(user_data):
    return user_data
"""

    validation = await coder_agent.validate_code(code)

    assert validation["valid"] is True
    assert len(validation["issues"]) == 0


# ============================================================================
# Odoo Module Generation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_odoo_module_low_risk(coder_agent, mock_llm_client):
    """Test Odoo module generation for low-risk module"""
    mock_llm_client.generate = AsyncMock(return_value="""
class ProductModel(models.Model):
    _name = 'product.template'
    name = fields.Char('Product Name')
""")

    spec = {
        "name": "product_catalog",
        "purpose": "Product management",
        "data_types": ["product_name", "price"],
        "models": ["Product"],
        "views": ["product_list"],
    }

    result = await coder_agent.generate_odoo_module(spec)

    assert result["success"] is True
    assert "code" in result["meta"]
    assert "DSGVO-Compliance" in result["meta"]["code"]  # Header added


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires supervisor integration")
async def test_generate_odoo_module_high_risk_requires_approval(coder_agent):
    """Test high-risk module requires supervisor approval"""
    spec = {
        "name": "customer_portal",
        "purpose": "Customer self-service",
        "data_types": ["customer_email", "address"],
        "models": ["Customer"],
        "views": [],
    }

    # Without mocking supervisor, this should fail
    result = await coder_agent.generate_odoo_module(spec)

    # Should indicate approval needed
    assert "approval" in result.get("error", "").lower() or not result["success"]


# ============================================================================
# API Endpoint Generation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_api_endpoint_get(coder_agent, mock_llm_client):
    """Test GET endpoint generation"""
    mock_llm_client.generate = AsyncMock(return_value="""
@router.get("/products")
async def list_products():
    return {"products": []}
""")

    spec = {
        "path": "/api/products",
        "method": "GET",
        "purpose": "List products",
        "authentication_required": False,
    }

    result = await coder_agent.generate_api_endpoint(spec)

    assert result["success"] is True
    assert "code" in result["meta"]


def test_assess_api_risk_high_for_delete(coder_agent):
    """Test DELETE endpoints are HIGH risk"""
    spec = {"method": "DELETE"}

    risk = coder_agent._assess_api_risk(spec)

    assert risk == RiskLevel.HIGH


def test_assess_api_risk_medium_for_post(coder_agent):
    """Test POST endpoints are MEDIUM risk"""
    spec = {"method": "POST"}

    risk = coder_agent._assess_api_risk(spec)

    assert risk == RiskLevel.MEDIUM


def test_assess_api_risk_low_for_get(coder_agent):
    """Test GET endpoints are LOW risk"""
    spec = {"method": "GET"}

    risk = coder_agent._assess_api_risk(spec)

    assert risk == RiskLevel.LOW


# ============================================================================
# Generic Code Generation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_code_generic(coder_agent, mock_llm_client):
    """Test generic code generation"""
    result = await coder_agent.generate_code(
        spec="Create a function that calculates fibonacci numbers",
        risk_level=RiskLevel.LOW
    )

    assert result["success"] is True
    assert "code" in result["meta"]


# ============================================================================
# File Creation Tests
# ============================================================================


def test_create_file_success(coder_agent, tmp_path):
    """Test file creation succeeds"""
    file_path = tmp_path / "test.py"
    content = "def hello():\n    pass"

    result = coder_agent.create_file(str(file_path), content)

    assert result["success"] is True
    assert file_path.exists()
    assert file_path.read_text() == content


def test_create_file_creates_directories(coder_agent, tmp_path):
    """Test file creation creates parent directories"""
    file_path = tmp_path / "subdir" / "test.py"
    content = "# Test"

    result = coder_agent.create_file(str(file_path), content)

    assert result["success"] is True
    assert file_path.exists()
