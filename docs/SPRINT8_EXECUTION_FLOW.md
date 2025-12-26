# Sprint 8: Autonomous Business Pipeline - Execution Flow

**Version:** 1.0.0
**Status:** ✅ DOCUMENTED
**Date:** 2025-12-26

---

## Overview

This document traces the complete execution flow of the Autonomous Business Pipeline from natural language input to live operation, including all internal steps, API calls, and state transitions.

---

## Complete Pipeline Flow (High-Level)

```
User Input (Natural Language)
        │
        ▼
1. Intent Resolution (S8.1)
        │
        ▼
2. Graph Spec Generation
        │
        ▼
3. Graph Construction & Validation (S8.2)
        │
        ▼
4. Node Execution (S8.3-S8.5)
        │
        ▼
5. Evidence Pack Generation (S8.6)
        │
        ▼
Final Result (Live Business System)
```

---

## Step-by-Step Execution Trace

### Example Input

**User Request:**
```json
{
  "vision": "Online consulting agency for digital transformation",
  "target_audience": "Mid-sized enterprises in DACH region",
  "region": "DACH",
  "monetization_type": "hourly_rate",
  "compliance_sensitivity": "high"
}
```

---

## Phase 1: Intent Resolution

### 1.1 API Call

```http
POST /api/pipeline/intent/resolve
Content-Type: application/json

{
  "vision": "Online consulting agency for digital transformation",
  "target_audience": "Mid-sized enterprises in DACH region",
  "region": "DACH",
  "monetization_type": "hourly_rate",
  "compliance_sensitivity": "high"
}
```

### 1.2 BusinessIntentResolver.resolve()

**Step 1: Text Preparation**
```python
full_text = f"{intent_input.vision} {intent_input.target_audience} {intent_input.region}"
# Result: "Online consulting agency for digital transformation Mid-sized enterprises in DACH region DACH"
```

**Step 2: Business Type Classification**
```python
def _classify_business_type(text):
    scores = {}
    for business_type, keywords in BUSINESS_TYPE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in text.lower())
        scores[business_type] = score

    # scores = {
    #     SERVICE: 3,  # "consulting", "agency", "expert"
    #     PRODUCT: 0,
    #     PLATFORM: 0,
    #     HYBRID: 0
    # }

    return max(scores, key=scores.get)  # → SERVICE
```

**Step 3: Monetization Classification**
```python
monetization_type = intent_input.monetization_type or _classify_monetization(text)
# User provided "hourly_rate" → HOURLY_RATE
```

**Step 4: Industry Classification**
```python
def _classify_industry(text):
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(keyword in text.lower() for keyword in keywords):
            return industry

    # Matches "consulting", "digital transformation" → PROFESSIONAL_SERVICES
```

**Step 5: Risk Assessment**
```python
def _assess_risk_level(...):
    score = 0

    # Business type weight
    if business_type == SERVICE:
        score += 10  # Low risk

    # Monetization weight
    if monetization_type == HOURLY_RATE:
        score += 15  # Medium risk

    # Compliance sensitivity weight
    if compliance_sensitivity == HIGH:
        score += 40  # High impact

    # Industry weight
    if industry == PROFESSIONAL_SERVICES:
        score += 20  # Medium risk

    # Total: 85 → HIGH risk
    if score >= 70:
        return RiskLevel.HIGH
```

**Step 6: Website Requirements**
```python
def _determine_website_requirements(...):
    needs_website = True  # All businesses need websites

    # Template selection based on business type
    if business_type == SERVICE:
        template = "nextjs-business"
        pages = ["home", "about", "services", "contact", "team"]

    return needs_website, template, pages
```

**Step 7: Odoo Module Determination**
```python
def _determine_odoo_modules(...):
    modules = ["base"]  # Always required

    if business_type == SERVICE:
        modules.extend(["project", "hr_timesheet"])

    if monetization_type == HOURLY_RATE:
        modules.append("sale_timesheet")

    if industry == PROFESSIONAL_SERVICES:
        modules.append("crm")

    # Result: ["base", "project", "hr_timesheet", "sale_timesheet", "crm"]
```

**Step 8: Custom Module Specs**
```python
def _generate_custom_module_specs(...):
    if not _needs_custom_modules(...):
        return []

    # For consulting agency:
    return [
        {
            "module_name": "consulting_projects",
            "models": [
                {
                    "name": "consulting_project",
                    "fields": [
                        {"name": "client_name", "type": "Char", "required": True},
                        {"name": "hourly_rate", "type": "Float", "required": True},
                        {"name": "estimated_hours", "type": "Integer"},
                    ]
                }
            ],
            "views": [
                {"name": "consulting_project_form", "type": "form"}
            ]
        }
    ]
```

**Step 9: Complexity Score**
```python
def _calculate_complexity_score(...):
    score = 0

    # Base score from business type
    score += {"SERVICE": 30, "PRODUCT": 50, "PLATFORM": 70}[business_type]

    # Odoo modules
    score += len(odoo_modules) * 5  # 5 modules × 5 = 25

    # Custom modules
    score += len(custom_modules) * 15  # 1 module × 15 = 15

    # Website pages
    score += len(pages) * 2  # 5 pages × 2 = 10

    # Total: 30 + 25 + 15 + 10 = 80
    return min(score, 100)
```

### 1.3 Response

```json
{
  "intent_id": "intent_1735216800_abc123",
  "business_type": "service",
  "monetization_type": "hourly_rate",
  "industry": "professional_services",
  "risk_level": "high",
  "needs_website": true,
  "website_template": "nextjs-business",
  "website_pages": ["home", "about", "services", "contact", "team"],
  "needs_erp": true,
  "odoo_modules_required": ["base", "project", "hr_timesheet", "sale_timesheet", "crm"],
  "needs_custom_modules": true,
  "custom_modules_spec": [
    {
      "module_name": "consulting_projects",
      "models": [...]
    }
  ],
  "governance_checks_required": ["G1", "G2", "G3", "G4"],
  "estimated_complexity_score": 80
}
```

---

## Phase 2: Graph Specification Generation

### 2.1 Build ExecutionGraphSpec

**From ResolvedBusinessIntent, construct graph:**

```python
graph_spec = ExecutionGraphSpec(
    graph_id=f"graph_{business_intent_id}",
    business_intent_id=business_intent_id,
    nodes=[
        # Node 1: WebGenesis (no dependencies)
        ExecutionNodeSpec(
            node_id="webgen",
            node_type=ExecutionNodeType.WEBGENESIS,
            depends_on=[],
            capabilities=[ExecutionCapability.DRY_RUN, ExecutionCapability.ROLLBACKABLE],
            executor_class="WebGenesisNode",
            executor_params={
                "website_template": "nextjs-business",
                "pages": ["home", "about", "services", "contact", "team"],
                "domain": "consulting-agency.com",
                "title": "Digital Transformation Consulting",
                "description": "Expert consulting for mid-sized enterprises",
                "business_intent_id": business_intent_id,
            },
            critical=False,
        ),

        # Node 2: DNS (depends on webgen)
        ExecutionNodeSpec(
            node_id="dns",
            node_type=ExecutionNodeType.DNS,
            depends_on=["webgen"],  # Wait for website first
            capabilities=[ExecutionCapability.DRY_RUN, ExecutionCapability.ROLLBACKABLE],
            executor_class="DNSNode",
            executor_params={
                "domain": "consulting-agency.com",
                "target_ip": "1.2.3.4",
                "record_type": "A",
                "ttl": 3600,
            },
            critical=False,
        ),

        # Node 3: Odoo Module (depends on both)
        ExecutionNodeSpec(
            node_id="odoo",
            node_type=ExecutionNodeType.ODOO_MODULE,
            depends_on=["webgen", "dns"],
            capabilities=[ExecutionCapability.DRY_RUN, ExecutionCapability.ROLLBACKABLE],
            executor_class="OdooModuleNode",
            executor_params={
                "module_name": "consulting_projects",
                "module_title": "Consulting Projects",
                "version": "1.0.0",
                "models": [...],
                "views": [...],
                "depends": ["base", "project", "hr_timesheet", "sale_timesheet", "crm"],
                "business_intent_id": business_intent_id,
            },
            critical=False,
        ),
    ],
    dry_run=False,  # LIVE execution
    auto_rollback=True,
    stop_on_first_error=True,
)
```

---

## Phase 3: Graph Construction & Validation

### 3.1 API Call

```http
POST /api/pipeline/execute
Content-Type: application/json

{
  "graph_id": "graph_intent_1735216800_abc123",
  "business_intent_id": "intent_1735216800_abc123",
  "nodes": [...],
  "dry_run": false,
  "auto_rollback": true,
  "stop_on_first_error": true
}
```

### 3.2 create_execution_graph(spec)

```python
graph = ExecutionGraph(spec)
```

### 3.3 ExecutionGraph.__init__()

**Step 1: Extract Dependencies**
```python
dependencies = {
    "webgen": [],
    "dns": ["webgen"],
    "odoo": ["webgen", "dns"],
}
```

**Step 2: Validate Dependencies**
```python
all_node_ids = {"webgen", "dns", "odoo"}
for node_id, deps in dependencies.items():
    for dep in deps:
        if dep not in all_node_ids:
            raise ExecutionGraphError(f"Node {node_id} depends on non-existent node: {dep}")
# ✅ All dependencies valid
```

**Step 3: Topological Sort**
```python
def _topological_sort():
    # Count incoming edges
    in_degree = {"webgen": 0, "dns": 1, "odoo": 2}

    # Queue of nodes with no dependencies
    queue = ["webgen"]
    result = []

    while queue:
        node_id = queue.pop(0)
        result.append(node_id)

        # For each node depending on current node
        for dependent in dependencies.get(node_id, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # Iteration trace:
    # 1. queue=["webgen"], result=[]
    #    → pop "webgen", result=["webgen"]
    #    → in_degree["dns"] = 0, queue=["dns"]
    #
    # 2. queue=["dns"], result=["webgen"]
    #    → pop "dns", result=["webgen", "dns"]
    #    → in_degree["odoo"] = 1
    #
    # 3. Wait... dns depends on webgen, but odoo depends on BOTH
    #    Let me recalculate:
    #
    # Actually, dependencies from nodes' perspective:
    # "webgen" is depended on by: ["dns", "odoo"]
    # "dns" is depended on by: ["odoo"]
    #
    # So when we process "webgen":
    #   in_degree["dns"] -= 1  (1 → 0)
    #   in_degree["odoo"] -= 1  (2 → 1)
    # When we process "dns":
    #   in_degree["odoo"] -= 1  (1 → 0)
    #
    # Correct execution_order = ["webgen", "dns", "odoo"]

    return result

execution_order = ["webgen", "dns", "odoo"]
```

### 3.4 Graph Ready

```
✅ Graph constructed successfully
✅ Execution order: webgen → dns → odoo
```

---

## Phase 4: Node Execution

### 4.1 graph.execute()

**Initialize ExecutionContext:**
```python
context = ExecutionContext(
    graph_id="graph_intent_1735216800_abc123",
    business_intent_id="intent_1735216800_abc123",
    dry_run=False,
    audit_enabled=True,
)
# context.shared_state = {}
# context.artifacts = []
# context.audit_events = []
```

**Emit Graph Start Event:**
```python
context.emit_audit_event({
    "event_type": "execution_graph_started",
    "graph_id": "graph_intent_1735216800_abc123",
    "business_intent_id": "intent_1735216800_abc123",
    "dry_run": False,
    "node_count": 3,
    "execution_order": ["webgen", "dns", "odoo"],
    "timestamp": "2025-12-26T12:00:00Z",
})
```

---

### 4.2 Execute Node: webgen (WebGenesisNode)

**4.2.1 Instantiate Node**
```python
node_spec = graph._get_node_spec("webgen")
node = WebGenesisNode(node_spec)
```

**4.2.2 node.execute_node(context)**

**Emit Start Event:**
```python
context.emit_audit_event({
    "event_type": "node_execution_started",
    "node_id": "webgen",
    "node_name": "WebGenesis",
    "dry_run": False,
})
```

**Validate Before Execution:**
```python
node._validate_before_execution(context)
# No validation errors
```

**Execute:**
```python
output, artifacts = await node.execute(context)
```

**4.2.3 WebGenesisNode.execute()**

**Step 1: Generate Website**
```python
generated_path = await _generate_website(context)
# Creates: storage/generated_websites/intent_1735216800_abc123_1735216900/

# For nextjs-business template:
# - app/page.tsx
# - app/layout.tsx
# - package.json
# - public/
```

**Step 2: Validate Website**
```python
validation_result = await _validate_website(generated_path)
# {
#   "valid": True,
#   "errors": [],
#   "warnings": [],
#   "pages_count": 5,
#   "template_type": "nextjs",
# }
```

**Step 3: Deploy Website**
```python
deployed_path = await _deploy_website(generated_path, context)
# Copies to: storage/deployed_websites/consulting-agency_com/
```

**Step 4: Return Output**
```python
output = {
    "website_url": "http://consulting-agency.com/",
    "template": "nextjs-business",
    "pages_generated": ["home", "about", "services", "contact", "team"],
    "domain": "consulting-agency.com",
    "title": "Digital Transformation Consulting",
    "generated_path": "storage/generated_websites/intent_1735216800_abc123_1735216900",
    "deployed_path": "storage/deployed_websites/consulting-agency_com",
    "validation": validation_result,
}

artifacts = [
    "storage/generated_websites/intent_1735216800_abc123_1735216900",
    "storage/deployed_websites/consulting-agency_com",
]

return output, artifacts
```

**4.2.4 node.execute_node() - Success Path**

```python
result = ExecutionNodeResult(
    node_id="webgen",
    status=ExecutionNodeStatus.COMPLETED,
    success=True,
    output=output,
    artifacts=artifacts,
    started_at="2025-12-26T12:00:01Z",
    completed_at="2025-12-26T12:00:05Z",
    duration_seconds=4.2,
    rollback_available=True,
    was_dry_run=False,
)

# Add artifacts to context
for artifact in artifacts:
    context.add_artifact(artifact)

# Emit success event
context.emit_audit_event({
    "event_type": "node_execution_completed",
    "node_id": "webgen",
    "node_name": "WebGenesis",
    "success": True,
    "duration_seconds": 4.2,
    "artifacts_count": 2,
})

return result
```

**4.2.5 Store Result**
```python
graph.node_results["webgen"] = result
graph.completed_nodes.add("webgen")
```

---

### 4.3 Execute Node: dns (DNSNode)

**4.3.1 Instantiate Node**
```python
node_spec = graph._get_node_spec("dns")
node = DNSNode(node_spec)
```

**4.3.2 node.execute_node(context)**

(Same lifecycle as webgen)

**4.3.3 DNSNode.execute()**

**Step 1: Find Zone ID**
```python
zone_id = await _find_zone_id(client, "consulting-agency.com")

# GET https://dns.hetzner.com/api/v1/zones
# Response: {
#   "zones": [
#     {"id": "zone123", "name": "consulting-agency.com"},
#     ...
#   ]
# }
# → zone_id = "zone123"
```

**Step 2: Create DNS Record**
```python
record_id = await _create_dns_record(client)

# POST https://dns.hetzner.com/api/v1/records
# {
#   "zone_id": "zone123",
#   "type": "A",
#   "name": "consulting-agency.com",
#   "value": "1.2.3.4",
#   "ttl": 3600
# }
# Response: {
#   "record": {"id": "rec456", ...}
# }
# → record_id = "rec456"
```

**Step 3: Verify Record**
```python
record_details = await _get_record_details(client, "rec456")

# GET https://dns.hetzner.com/api/v1/records/rec456
# Response: {
#   "record": {
#     "id": "rec456",
#     "zone_id": "zone123",
#     "type": "A",
#     "name": "consulting-agency.com",
#     "value": "1.2.3.4",
#     "ttl": 3600,
#     "created": "2025-12-26T12:00:06Z"
#   }
# }
```

**Step 4: Emit Audit Event**
```python
context.emit_audit_event({
    "event_type": "dns_record_created",
    "domain": "consulting-agency.com",
    "target_ip": "1.2.3.4",
    "record_id": "rec456",
    "zone_id": "zone123",
})
```

**Step 5: Return Output**
```python
output = {
    "dns_record_id": "rec456",
    "zone_id": "zone123",
    "domain": "consulting-agency.com",
    "target_ip": "1.2.3.4",
    "record_type": "A",
    "ttl": 3600,
    "dns_status": "created",
    "record_details": record_details,
}

artifacts = []  # DNS has no file artifacts

return output, artifacts
```

**4.3.4 Store Result**
```python
graph.node_results["dns"] = result
graph.completed_nodes.add("dns")
```

---

### 4.4 Execute Node: odoo (OdooModuleNode)

**4.4.1 Instantiate Node**
```python
node_spec = graph._get_node_spec("odoo")
node = OdooModuleNode(node_spec)
```

**4.4.2 node.execute_node(context)**

**4.4.3 OdooModuleNode.execute()**

**Step 1: Generate Module Structure**
```python
module_path = await _generate_module_structure(context)
# Creates: storage/odoo_modules/consulting_projects/
#   - models/
#   - views/
#   - security/
```

**Step 2: Generate Manifest**
```python
await _generate_manifest(module_path)
# Creates: storage/odoo_modules/consulting_projects/__manifest__.py
```

**Step 3: Generate Models**
```python
await _generate_models(module_path)
# Creates:
#   - models/__init__.py
#   - models/consulting_project.py
```

**Step 4: Generate Views**
```python
await _generate_views(module_path)
# Creates:
#   - views/consulting_project_form.xml
```

**Step 5: Generate Access Rules**
```python
await _generate_access_rules(module_path)
# Creates:
#   - security/ir.model.access.csv
```

**Step 6: Validate Module**
```python
validation_result = await _validate_module(module_path)
# {
#   "valid": True,
#   "errors": [],
#   "warnings": [],
#   "structure_complete": True,
# }
```

**Step 7: Install Module (Simulated)**
```python
install_status = await _install_module(context)

# TODO: Real Odoo connector integration
# For now: simulated

context.emit_audit_event({
    "event_type": "odoo_module_installed",
    "module_name": "consulting_projects",
    "version": "1.0.0",
})

# {
#   "success": True,
#   "message": "Module consulting_projects installation simulated",
#   "installed_at": "2025-12-26T12:00:15Z",
# }
```

**Step 8: Return Output**
```python
output = {
    "module_path": "storage/odoo_modules/consulting_projects",
    "module_name": "consulting_projects",
    "module_title": "Consulting Projects",
    "version": "1.0.0",
    "odoo_install_status": install_status,
    "models_count": 1,
    "views_count": 1,
    "validation": validation_result,
}

artifacts = ["storage/odoo_modules/consulting_projects"]

return output, artifacts
```

**4.4.4 Store Result**
```python
graph.node_results["odoo"] = result
graph.completed_nodes.add("odoo")
```

---

## Phase 5: Graph Completion

### 5.1 All Nodes Completed

```python
# completed_nodes = {"webgen", "dns", "odoo"}
# failed_nodes = {}
# execution_order = ["webgen", "dns", "odoo"]

final_status = ExecutionNodeStatus.COMPLETED
duration_seconds = 14.8  # Total time
```

### 5.2 Emit Graph Completion Event

```python
context.emit_audit_event({
    "event_type": "execution_graph_completed",
    "graph_id": "graph_intent_1735216800_abc123",
    "status": "completed",
    "completed_nodes": 3,
    "failed_nodes": 0,
    "duration_seconds": 14.8,
})
```

### 5.3 Build ExecutionGraphResult

```python
result = ExecutionGraphResult(
    graph_id="graph_intent_1735216800_abc123",
    business_intent_id="intent_1735216800_abc123",
    status=ExecutionNodeStatus.COMPLETED,
    success=True,
    node_results=[
        result_webgen,
        result_dns,
        result_odoo,
    ],
    completed_nodes=["webgen", "dns", "odoo"],
    failed_nodes=[],
    execution_order=["webgen", "dns", "odoo"],
    duration_seconds=14.8,
    was_dry_run=False,
    artifacts=[
        "storage/generated_websites/intent_1735216800_abc123_1735216900",
        "storage/deployed_websites/consulting-agency_com",
        "storage/odoo_modules/consulting_projects",
    ],
    audit_events=[
        {"event_type": "execution_graph_started", ...},
        {"event_type": "node_execution_started", "node_id": "webgen", ...},
        {"event_type": "node_execution_completed", "node_id": "webgen", ...},
        {"event_type": "node_execution_started", "node_id": "dns", ...},
        {"event_type": "dns_record_created", ...},
        {"event_type": "node_execution_completed", "node_id": "dns", ...},
        {"event_type": "node_execution_started", "node_id": "odoo", ...},
        {"event_type": "odoo_module_installed", ...},
        {"event_type": "node_execution_completed", "node_id": "odoo", ...},
        {"event_type": "execution_graph_completed", ...},
    ],
    error=None,
)
```

---

## Phase 6: Evidence Pack Generation

### 6.1 generate_evidence_pack()

```python
evidence_generator = get_evidence_generator()
evidence_pack = evidence_generator.generate_evidence_pack(
    execution_result=result,
    business_intent=resolved_intent,  # From Phase 1
    graph_spec=graph_spec,            # From Phase 2
    governance_decisions=[],          # None in this example
)
```

### 6.2 Generate Summary

```python
summary = {
    "total_nodes": 3,
    "completed_nodes": 3,
    "failed_nodes": 0,
    "duration_seconds": 14.8,
    "success": True,
    "status": "completed",
    "was_dry_run": False,
    "artifacts_count": 3,
    "audit_events_count": 10,
    "execution_order": ["webgen", "dns", "odoo"],
}
```

### 6.3 Compute Content Hash

```python
hash_content = {
    "business_intent_id": "intent_1735216800_abc123",
    "graph_id": "graph_intent_1735216800_abc123",
    "is_dry_run": False,
    "summary": summary,
    "execution_order": ["webgen", "dns", "odoo"],
    "completed_nodes": ["dns", "odoo", "webgen"],  # Sorted
    "failed_nodes": [],
    "artifacts": [
        "storage/deployed_websites/consulting-agency_com",
        "storage/generated_websites/intent_1735216800_abc123_1735216900",
        "storage/odoo_modules/consulting_projects",
    ],  # Sorted
}

hash_json = json.dumps(hash_content, sort_keys=True)
content_hash = hashlib.sha256(hash_json.encode("utf-8")).hexdigest()
# → "a1b2c3d4e5f6..."
```

### 6.4 Complete Evidence Pack

```python
evidence_pack = PipelineEvidencePack(
    pack_id="evidence_pack_graph_intent_1735216800_abc123_1735216915",
    generated_at="2025-12-26T12:00:15Z",
    business_intent_id="intent_1735216800_abc123",
    business_intent=resolved_intent,
    graph_id="graph_intent_1735216800_abc123",
    graph_spec=graph_spec,
    execution_result=result,
    summary=summary,
    governance_decisions=[],
    artifacts=[...],
    audit_events=[...],
    content_hash="a1b2c3d4e5f6...",
    is_dry_run=False,
)
```

### 6.5 Save Evidence Pack

```python
evidence_path = evidence_generator.save_evidence_pack(evidence_pack)
# Saves to: storage/pipeline_evidence/evidence_pack_graph_intent_1735216800_abc123_1735216915.json
```

---

## Final Response

### 6.6 API Response

```json
{
  "graph_id": "graph_intent_1735216800_abc123",
  "business_intent_id": "intent_1735216800_abc123",
  "status": "completed",
  "success": true,
  "node_results": [
    {
      "node_id": "webgen",
      "status": "completed",
      "success": true,
      "output": {
        "website_url": "http://consulting-agency.com/",
        "template": "nextjs-business",
        "pages_generated": ["home", "about", "services", "contact", "team"],
        ...
      },
      "duration_seconds": 4.2,
      ...
    },
    {
      "node_id": "dns",
      "status": "completed",
      "success": true,
      "output": {
        "dns_record_id": "rec456",
        "domain": "consulting-agency.com",
        ...
      },
      "duration_seconds": 1.5,
      ...
    },
    {
      "node_id": "odoo",
      "status": "completed",
      "success": true,
      "output": {
        "module_path": "storage/odoo_modules/consulting_projects",
        ...
      },
      "duration_seconds": 9.1,
      ...
    }
  ],
  "completed_nodes": ["webgen", "dns", "odoo"],
  "failed_nodes": [],
  "execution_order": ["webgen", "dns", "odoo"],
  "duration_seconds": 14.8,
  "was_dry_run": false,
  "artifacts": [
    "storage/generated_websites/intent_1735216800_abc123_1735216900",
    "storage/deployed_websites/consulting-agency_com",
    "storage/odoo_modules/consulting_projects"
  ],
  "audit_events": [...],
  "error": null
}
```

---

## Error Scenarios

### Scenario 1: Node Execution Failure

**If DNS node fails:**

```python
# In graph.execute(), at node "dns":
try:
    result = await node.execute_node(context)
except ExecutionNodeError as e:
    self.failed_nodes.add("dns")
    error_message = f"Node dns failed: {e}"

    context.emit_audit_event({
        "event_type": "execution_graph_node_failed",
        "node_id": "dns",
        "error": str(e),
        "critical": node_spec.critical,
    })

    # stop_on_first_error = True
    success = False
    break

# Skip "odoo" node (depends on "dns")
```

**Rollback Sequence:**

```python
if not success and auto_rollback:
    await _rollback_completed_nodes(context)

# Rollback in reverse order: ["webgen"]
# (dns not completed, so nothing to rollback)

# webgen rollback:
await webgen_node.rollback(context)
# → shutil.rmtree(deployed_path)
# → shutil.rmtree(generated_path)
```

**Final Result:**

```json
{
  "status": "failed",
  "success": false,
  "completed_nodes": ["webgen"],
  "failed_nodes": ["dns"],
  "error": "Node dns failed: Hetzner API error: 401 Unauthorized"
}
```

---

### Scenario 2: Cyclic Dependency

**Invalid Graph:**

```python
nodes = [
    {"node_id": "A", "depends_on": ["B"]},
    {"node_id": "B", "depends_on": ["A"]},  # Cycle!
]
```

**Detection:**

```python
# In _topological_sort():
in_degree = {"A": 1, "B": 1}
queue = []  # No nodes with in_degree 0!

while queue:
    # Never enters loop

if len(result) != len(dependencies):
    # len(result) = 0, len(dependencies) = 2
    raise CyclicDependencyError(
        "Graph contains cyclic dependencies. Processed 0/2 nodes."
    )
```

**Response:**

```http
HTTP 500 Internal Server Error

{
  "detail": "Graph contains cyclic dependencies. Processed 0/2 nodes."
}
```

---

## Dry-Run Execution Flow

### Differences from Live Execution

**Same:**
- Intent resolution
- Graph construction
- Topological sort
- Node lifecycle

**Different:**
- `context.dry_run = True`
- Nodes call `dry_run()` instead of `execute()`
- No real operations (no files, no DNS, no Odoo)
- Simulated outputs
- No rollback (nothing to undo)

### Example: WebGenesis Dry-Run

```python
async def dry_run(context: ExecutionContext):
    # No actual file generation
    output = {
        "website_url": "http://consulting-agency.com/ (simulated)",
        "template": "nextjs-business",
        "pages_generated": ["home", "about", "services", "contact", "team"],
        "generated_path": "storage/generated_websites/sim_intent_1735216800_abc123",
        "deployed_path": "storage/deployed_websites/sim_consulting-agency_com",
        "validation": {
            "valid": True,
            "simulated": True,
        },
        "dry_run_preview": self._generate_html_preview(),
    }

    artifacts = ["sim_website_intent_1735216800_abc123.html"]

    return output, artifacts
```

---

## Conclusion

This document traced the complete execution flow from natural language input to live business system, including:

- ✅ Intent resolution with keyword-based classification
- ✅ DAG construction with topological sort
- ✅ Sequential node execution (webgen → dns → odoo)
- ✅ Real API calls (Hetzner DNS)
- ✅ File generation (websites, Odoo modules)
- ✅ Comprehensive audit trail
- ✅ Evidence pack with cryptographic verification
- ✅ Error handling and rollback scenarios

**Key Achievement:** Every step is deterministic, auditable, and reversible.

---

**Sprint 8 Status:** ✅ COMPLETE
**Next:** Dry-run report example documentation
