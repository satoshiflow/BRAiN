# Sprint 5: Business Factory - Design Document

**Version:** 1.0
**Date:** 2025-12-25
**Status:** 🔧 Design Phase
**Compliance:** Auditor-, Investor-, und Compliance-tauglich

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Data Schemas](#data-schemas)
4. [Module Specifications](#module-specifications)
5. [API Endpoints](#api-endpoints)
6. [Audit Events](#audit-events)
7. [Template System](#template-system)
8. [Execution Flow](#execution-flow)
9. [Error Handling & Rollback](#error-handling--rollback)
10. [Security & Compliance](#security--compliance)
11. [Implementation Phases](#implementation-phases)

---

## Executive Summary

### Goal
Automate complete business setup from a single briefing JSON:
- Generate business website (landing page, company info)
- Deploy Odoo ERP with configured modules
- Set up integrations between components
- Generate compliance evidence pack
- Full audit trail for investor/regulatory review

### Key Principles
1. **No Free LLM Generation** - All outputs based on validated templates
2. **Plan Before Execute** - Always generate and review plan first
3. **Preflight Required** - No execution without prerequisite checks
4. **Full Audit Trail** - Every action logged with evidence
5. **Rollback Capable** - All operations can be reversed
6. **Investor-Grade** - Evidence pack suitable for due diligence

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Business Factory                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   Briefing   │───▶│   Planner    │───▶│ Risk Assessor│    │
│  │   (Input)    │    │  (Generate   │    │ (Validate)   │    │
│  └──────────────┘    │   Plan)      │    └──────────────┘    │
│                      └──────┬───────┘                         │
│                             │                                  │
│                             ▼                                  │
│                      ┌──────────────┐                         │
│                      │ Template     │                         │
│                      │ Registry     │                         │
│                      └──────┬───────┘                         │
│                             │                                  │
│                             ▼                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │  Preflight   │───▶│  Executor    │───▶│  Evidence    │    │
│  │  Checker     │    │  Engine      │    │  Generator   │    │
│  └──────────────┘    └──────┬───────┘    └──────────────┘    │
│                             │                                  │
│                             ▼                                  │
│                      ┌──────────────┐                         │
│                      │  Rollback    │                         │
│                      │  Manager     │                         │
│                      └──────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Integration Points:
├── AXE Agent: Conversational interface for briefing input
├── Integrations Module: Odoo API client with OAuth/retry/circuit breaker
├── WebDev Agents: Website generation (component_generator, deployment)
├── Audit System: sovereign_mode audit logging
└── DMZ Control: Secure external API access
```

---

## Data Schemas

### 1. BusinessBriefing (Input)

```python
class BusinessType(str, Enum):
    """Supported business types"""
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    CONSULTING = "consulting"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    SERVICE = "service"

class BusinessBriefing(BaseModel):
    """
    User input for business setup.
    This is the single source of truth for the entire factory process.
    """
    # Basic Info
    business_name: str = Field(..., description="Legal business name")
    business_type: BusinessType = Field(..., description="Type of business")
    industry: str = Field(..., description="Industry sector (e.g., 'IT Services')")
    country: str = Field(default="DE", description="Primary country (ISO code)")

    # Contact
    contact_email: str = Field(..., description="Primary contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")

    # Website Requirements
    website_config: WebsiteConfig = Field(...)

    # ERP Requirements
    erp_config: ERPConfig = Field(...)

    # Integration Requirements
    integrations: List[IntegrationRequirement] = Field(default_factory=list)

    # Execution Options
    auto_execute: bool = Field(default=False, description="Execute plan immediately")
    dry_run: bool = Field(default=False, description="Generate plan only, no execution")

    # Metadata
    created_by: str = Field(default="system")
    priority: int = Field(default=10, ge=1, le=100)
    deadline: Optional[datetime] = Field(None)

class WebsiteConfig(BaseModel):
    """Website setup configuration"""
    domain: str = Field(..., description="Desired domain (e.g., 'example.com')")
    template: str = Field(default="modern_landing", description="Website template ID")
    pages: List[str] = Field(
        default_factory=lambda: ["home", "about", "contact"],
        description="Pages to generate"
    )
    features: List[str] = Field(
        default_factory=list,
        description="Features to enable (e.g., 'blog', 'shop', 'booking')"
    )
    primary_color: str = Field(default="#2563eb", description="Brand primary color")
    logo_url: Optional[str] = Field(None, description="Logo URL")

class ERPConfig(BaseModel):
    """Odoo ERP configuration"""
    modules: List[str] = Field(
        default_factory=lambda: ["crm", "sales", "accounting"],
        description="Odoo modules to install"
    )
    users: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Initial users [{name, email, role}]"
    )
    currency: str = Field(default="EUR", description="Default currency")
    fiscal_year_start: str = Field(default="01-01", description="Fiscal year start (MM-DD)")
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom field definitions"
    )

class IntegrationRequirement(BaseModel):
    """Integration between components"""
    name: str = Field(..., description="Integration name")
    source: str = Field(..., description="Source system (e.g., 'website')")
    target: str = Field(..., description="Target system (e.g., 'odoo')")
    type: str = Field(..., description="Integration type (e.g., 'contact_form')")
    config: Dict[str, Any] = Field(default_factory=dict)
```

### 2. BusinessPlan (Output)

```python
class PlanStatus(str, Enum):
    """Plan lifecycle status"""
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class StepStatus(str, Enum):
    """Individual step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"

class ExecutionStep(BaseModel):
    """Single execution step in the plan"""
    step_id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Human-readable step name")
    description: str = Field(..., description="What this step does")

    # Execution
    executor: str = Field(..., description="Which executor handles this (e.g., 'webgen', 'odoo', 'integration')")
    template_id: Optional[str] = Field(None, description="Template to use (if applicable)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters")

    # Dependencies
    depends_on: List[str] = Field(default_factory=list, description="Step IDs that must complete first")

    # Status
    status: StepStatus = Field(default=StepStatus.PENDING)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    duration_seconds: Optional[float] = Field(None)

    # Results
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    evidence_path: Optional[str] = Field(None, description="Path to evidence file")

    # Rollback
    rollback_possible: bool = Field(default=True)
    rollback_steps: List[Dict[str, Any]] = Field(default_factory=list)

class RiskAssessment(BaseModel):
    """Risk analysis for the plan"""
    overall_risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    risks: List[Risk] = Field(default_factory=list)

    # Resource estimates
    estimated_duration_minutes: int = Field(..., description="Total estimated time")
    estimated_cost_euros: float = Field(default=0.0, description="Estimated cost")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)

class Risk(BaseModel):
    """Individual risk item"""
    risk_id: str
    description: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    probability: str  # LOW, MEDIUM, HIGH
    mitigation: str
    related_steps: List[str] = Field(default_factory=list)

class BusinessPlan(BaseModel):
    """Complete execution plan for business setup"""
    # Identity
    plan_id: str = Field(..., description="Unique plan identifier")
    briefing_id: str = Field(..., description="Original briefing ID")
    version: int = Field(default=1, description="Plan version number")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="business_factory")
    status: PlanStatus = Field(default=PlanStatus.DRAFT)

    # Content
    steps: List[ExecutionStep] = Field(default_factory=list, description="Ordered execution steps")
    risk_assessment: RiskAssessment = Field(...)

    # Execution tracking
    execution_started_at: Optional[datetime] = Field(None)
    execution_completed_at: Optional[datetime] = Field(None)
    current_step_index: int = Field(default=0)

    # Results
    evidence_pack_path: Optional[str] = Field(None)
    final_urls: Dict[str, str] = Field(default_factory=dict, description="Generated URLs (website, odoo, etc.)")

    # Statistics
    steps_total: int = Field(default=0)
    steps_completed: int = Field(default=0)
    steps_failed: int = Field(default=0)
    steps_skipped: int = Field(default=0)

    def get_next_step(self) -> Optional[ExecutionStep]:
        """Get next pending step respecting dependencies"""
        # Implementation will check dependencies
        pass

    def update_step_status(self, step_id: str, status: StepStatus, **kwargs):
        """Update step status and metadata"""
        pass
```

---

## Module Specifications

### D1: BusinessPlan Engine

**Location:** `backend/app/modules/business_factory/`

**Files:**
- `schemas.py` - All Pydantic models
- `planner.py` - BusinessPlanner class
- `risk_assessor.py` - RiskAssessor class

**BusinessPlanner Responsibilities:**
1. Parse BusinessBriefing
2. Determine required steps based on business_type and configs
3. Generate ExecutionStep sequence with dependencies
4. Call RiskAssessor for risk analysis
5. Return validated BusinessPlan

**Key Logic:**
```python
class BusinessPlanner:
    async def generate_plan(self, briefing: BusinessBriefing) -> BusinessPlan:
        """
        Generate execution plan from briefing.

        Logic:
        1. Validate briefing
        2. Determine business_type-specific template
        3. Generate steps:
           - Website generation steps
           - Odoo deployment steps
           - Integration configuration steps
           - Testing/validation steps
        4. Build dependency graph
        5. Risk assessment
        6. Return complete plan
        """
```

**RiskAssessor Responsibilities:**
1. Analyze each step for potential issues
2. Calculate resource requirements
3. Estimate time and cost
4. Identify critical dependencies
5. Generate mitigation strategies

---

### D2: Template Registry

**Location:** `backend/app/modules/template_registry/`

**Files:**
- `loader.py` - Template loading
- `validator.py` - Template validation
- `versioning.py` - Template version management
- `templates/` - Template storage directory

**Template Structure:**
```json
{
  "template_id": "modern_landing_v1",
  "version": "1.0.0",
  "type": "website",
  "name": "Modern Landing Page",
  "description": "Responsive landing page with hero, features, contact",
  "variables": [
    {"name": "business_name", "type": "string", "required": true},
    {"name": "primary_color", "type": "color", "default": "#2563eb"}
  ],
  "files": [
    {
      "path": "index.html",
      "template": "templates/modern_landing/index.html.jinja2",
      "output_path": "public/index.html"
    }
  ],
  "dependencies": ["nodejs>=18", "nginx"],
  "validation_schema": {...}
}
```

**TemplateRegistry Methods:**
- `get_template(template_id: str) -> Template`
- `list_templates(type: Optional[str]) -> List[Template]`
- `validate_template(template: Template) -> ValidationResult`
- `render_template(template_id: str, variables: Dict) -> RenderedTemplate`

---

### D3: Execution Engine

**Location:** `backend/app/modules/factory_executor/`

**Files:**
- `preflight.py` - PreflightChecker class
- `executor.py` - FactoryExecutor class
- `rollback_manager.py` - RollbackManager class
- `executors/` - Specific executor implementations
  - `webgen_executor.py`
  - `odoo_executor.py`
  - `integration_executor.py`

**PreflightChecker:**
```python
class PreflightChecker:
    async def check_prerequisites(self, plan: BusinessPlan) -> PreflightResult:
        """
        Validate all prerequisites before execution.

        Checks:
        - Domain availability (for website)
        - Odoo instance availability
        - Required templates exist
        - Network connectivity
        - Disk space
        - Dependencies installed
        """
```

**FactoryExecutor:**
```python
class FactoryExecutor:
    def __init__(self):
        self.executors = {
            "webgen": WebGenExecutor(),
            "odoo": OdooExecutor(),
            "integration": IntegrationExecutor(),
        }
        self.rollback_manager = RollbackManager()
        self.audit_service = get_sovereign_mode_service()

    async def execute_plan(self, plan: BusinessPlan) -> ExecutionResult:
        """
        Execute complete business plan.

        Flow:
        1. Preflight check
        2. For each step (respecting dependencies):
           a. Emit audit event: factory.step_started
           b. Execute step with appropriate executor
           c. Store evidence
           d. Update step status
           e. Emit audit event: factory.step_completed/failed
           f. On failure: trigger rollback if configured
        3. Generate evidence pack
        4. Return ExecutionResult
        """
```

**RollbackManager:**
```python
class RollbackManager:
    async def rollback_plan(self, plan: BusinessPlan, from_step: int) -> RollbackResult:
        """
        Rollback executed steps in reverse order.

        Actions:
        - Delete generated files
        - Uninstall Odoo modules
        - Remove DNS records
        - Restore backups
        - Emit audit events
        """
```

---

### D4: Factory Router

**Location:** `backend/app/modules/factory/router.py`

**Endpoints:**

```python
@router.post("/api/factory/plan")
async def create_plan(briefing: BusinessBriefing) -> BusinessPlan:
    """
    Generate execution plan from briefing.
    Does NOT execute - just creates the plan.
    """

@router.post("/api/factory/execute")
async def execute_plan(plan_id: str, confirm: bool = False) -> ExecutionResult:
    """
    Execute a validated plan.
    Requires confirm=true to prevent accidental execution.
    """

@router.get("/api/factory/{plan_id}")
async def get_plan(plan_id: str) -> BusinessPlan:
    """Get plan by ID with current status"""

@router.get("/api/factory/{plan_id}/status")
async def get_plan_status(plan_id: str) -> PlanStatusResponse:
    """Get real-time execution status"""

@router.get("/api/factory/{plan_id}/evidence")
async def get_evidence_pack(plan_id: str) -> FileResponse:
    """Download complete evidence pack (ZIP)"""

@router.post("/api/factory/{plan_id}/rollback")
async def rollback_plan(plan_id: str, to_step: Optional[int] = None) -> RollbackResult:
    """Rollback executed plan to specific step (or completely)"""

@router.get("/api/factory/templates")
async def list_templates(type: Optional[str] = None) -> List[TemplateInfo]:
    """List available templates"""

@router.get("/api/factory/info")
async def factory_info() -> FactoryInfo:
    """Factory system information"""
```

---

## Audit Events

### Event Types (Added to AuditEventType)

```python
# Factory events
FACTORY_PLAN_GENERATED = "factory.plan_generated"
FACTORY_EXECUTION_STARTED = "factory.execution_started"
FACTORY_STEP_STARTED = "factory.step_started"
FACTORY_STEP_COMPLETED = "factory.step_completed"
FACTORY_STEP_FAILED = "factory.step_failed"
FACTORY_EXECUTION_COMPLETED = "factory.execution_completed"
FACTORY_EXECUTION_FAILED = "factory.execution_failed"
FACTORY_ROLLBACK_STARTED = "factory.rollback_started"
FACTORY_ROLLBACK_COMPLETED = "factory.rollback_completed"
```

### Event Emission Example

```python
# In executor
await self.audit_service._audit(
    event_type="factory.step_started",
    success=True,
    severity=AuditSeverity.INFO,
    reason=f"Starting step: {step.name}",
    metadata={
        "plan_id": plan.plan_id,
        "step_id": step.step_id,
        "executor": step.executor,
        "template_id": step.template_id,
    }
)
```

---

## Template System

### Template Types

1. **Website Templates**
   - modern_landing_v1
   - ecommerce_store_v1
   - corporate_site_v1
   - saas_landing_v1

2. **Odoo Module Configurations**
   - ecommerce_full (sales, inventory, shipping, payment)
   - saas_core (crm, projects, timesheets, invoicing)
   - consulting_suite (projects, timesheets, expenses, invoicing)

3. **Integration Templates**
   - website_to_odoo_contact_form
   - odoo_to_website_product_sync
   - payment_gateway_integration

### Template Variables

Templates use Jinja2 syntax with strict variable validation:
```jinja2
<!DOCTYPE html>
<html>
<head>
    <title>{{ business_name }} - {{ tagline }}</title>
    <meta name="description" content="{{ description }}">
    <style>
        :root {
            --primary-color: {{ primary_color }};
        }
    </style>
</head>
...
```

---

## Execution Flow

### Happy Path

```
User → POST /api/factory/plan (briefing)
  ↓
Planner generates steps
  ↓
RiskAssessor evaluates
  ↓
Return BusinessPlan (status=DRAFT)
  ↓
User reviews plan
  ↓
User → POST /api/factory/execute (plan_id, confirm=true)
  ↓
PreflightChecker validates
  ↓
FactoryExecutor starts
  ├─ Step 1: Generate website from template
  │    └─ Evidence: generated files + screenshots
  ├─ Step 2: Deploy website to hosting
  │    └─ Evidence: deployment logs + URL health check
  ├─ Step 3: Install Odoo modules
  │    └─ Evidence: module list + configuration exports
  ├─ Step 4: Configure integrations
  │    └─ Evidence: integration test results
  └─ Step 5: Final validation
       └─ Evidence: end-to-end test results
  ↓
Generate Evidence Pack (ZIP)
  ↓
Return ExecutionResult with URLs + evidence_pack_path
```

### Failure Scenario

```
Step 3 fails (Odoo connection error)
  ↓
FactoryExecutor catches exception
  ↓
Emit audit event: factory.step_failed
  ↓
If plan.auto_rollback == true:
  ↓
  RollbackManager.rollback_plan(from_step=2)
    ├─ Rollback Step 2 (delete deployed website)
    └─ Rollback Step 1 (delete generated files)
  ↓
  Emit audit event: factory.rollback_completed
  ↓
Return ExecutionResult (status=FAILED, rollback=SUCCESS)
```

---

## Error Handling & Rollback

### Rollback Strategies

Each executor implements rollback logic:

```python
class WebGenExecutor:
    async def execute(self, step: ExecutionStep) -> StepResult:
        # Execution logic
        result = await self._generate_website(step.parameters)

        # Record rollback info
        step.rollback_steps = [
            {"action": "delete_directory", "path": result.output_path},
            {"action": "remove_dns", "domain": step.parameters["domain"]},
        ]

        return result

    async def rollback(self, step: ExecutionStep) -> RollbackResult:
        # Execute rollback steps in reverse
        for rollback_step in reversed(step.rollback_steps):
            if rollback_step["action"] == "delete_directory":
                await self._delete_directory(rollback_step["path"])
            elif rollback_step["action"] == "remove_dns":
                await self._remove_dns_record(rollback_step["domain"])
```

### Rollback Limitations

Some actions cannot be fully rolled back:
- DNS propagation (takes time)
- External API calls to third parties
- Emails sent to users

For these, rollback generates **compensating transactions** and logs actions taken.

---

## Security & Compliance

### 1. Input Validation
- All briefing fields validated with Pydantic
- Domain names validated (RFC compliance)
- Email addresses validated
- No arbitrary code execution

### 2. Template Safety
- Templates stored in read-only directory
- Jinja2 sandboxed environment
- Only whitelisted variables allowed
- No {% include %} or {% import %} allowed

### 3. Audit Trail
- Every action logged
- Timestamps with microsecond precision
- All errors captured
- Evidence files immutable

### 4. Evidence Pack Contents
```
evidence_pack_{plan_id}.zip
├── plan.json                    # Complete BusinessPlan
├── audit_events.jsonl           # All audit events
├── steps/
│   ├── step_1_webgen/
│   │   ├── generated_files/
│   │   ├── screenshots/
│   │   └── logs.txt
│   ├── step_2_deploy/
│   └── step_3_odoo/
├── risk_assessment.pdf          # Risk analysis report
└── verification_checksums.txt   # SHA256 of all files
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (D1, D2)
- [x] Define all schemas
- [ ] Implement BusinessPlanner
- [ ] Implement RiskAssessor
- [ ] Create Template Registry
- [ ] Add 2 basic templates (modern_landing, basic_odoo)

### Phase 2: Execution Engine (D3)
- [ ] Implement PreflightChecker
- [ ] Implement FactoryExecutor base
- [ ] Implement WebGenExecutor
- [ ] Implement OdooExecutor (using integrations module)
- [ ] Implement RollbackManager

### Phase 3: API & Audit (D4, D5)
- [ ] Create Factory Router
- [ ] Add audit event types
- [ ] Integrate with sovereign_mode audit
- [ ] Implement evidence pack generation

### Phase 4: Frontend (D6)
- [ ] Create /factory page in control_deck
- [ ] Briefing form component
- [ ] Plan viewer component
- [ ] Execution progress tracker
- [ ] Evidence pack download

### Phase 5: Testing & Documentation (D7)
- [ ] Create demo briefing
- [ ] End-to-end test
- [ ] Write documentation
- [ ] Create tutorial video

---

## Demo Use Case

**Briefing:**
```json
{
  "business_name": "Acme Consulting GmbH",
  "business_type": "consulting",
  "industry": "IT Consulting",
  "country": "DE",
  "contact_email": "info@acme-consulting.example",
  "website_config": {
    "domain": "acme-consulting.example",
    "template": "corporate_site_v1",
    "pages": ["home", "services", "team", "contact"],
    "primary_color": "#1e40af",
    "features": ["blog", "contact_form"]
  },
  "erp_config": {
    "modules": ["crm", "projects", "timesheets", "invoicing"],
    "users": [
      {"name": "Admin User", "email": "admin@acme.example", "role": "admin"}
    ],
    "currency": "EUR"
  },
  "integrations": [
    {
      "name": "Contact Form to Odoo CRM",
      "source": "website",
      "target": "odoo",
      "type": "contact_form",
      "config": {"create_lead": true}
    }
  ],
  "dry_run": false
}
```

**Expected Result:**
1. Website deployed at https://acme-consulting.example
2. Odoo instance with CRM, Projects, Timesheets, Invoicing
3. Contact form submissions create Odoo leads
4. Evidence pack with all deployment logs

---

## Success Criteria

✅ **Must Have:**
- [ ] Briefing → Plan generation works
- [ ] Plan can be reviewed before execution
- [ ] Website generated from template
- [ ] Odoo modules installed
- [ ] Integration configured
- [ ] Evidence pack downloadable
- [ ] Full audit trail
- [ ] Rollback tested and working

✅ **Should Have:**
- [ ] 3+ website templates
- [ ] 3+ Odoo configurations
- [ ] Risk assessment accurate
- [ ] UI polished and intuitive
- [ ] Documentation complete

✅ **Nice to Have:**
- [ ] Email notifications on completion
- [ ] Webhook support for external monitoring
- [ ] Template marketplace
- [ ] Custom template upload

---

**End of Design Document**

Next Steps: Review this design, then proceed to Phase 1 implementation.
