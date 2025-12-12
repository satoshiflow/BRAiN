# WebDev Cluster - Architecture & Standards

**Version:** 1.0.0
**Created:** 2025-12-12
**Purpose:** Standardized agent cluster system for web development automation

---

## 📁 Repository Structure

```
backend/
├── brain/
│   ├── agents/              # Existing agent system
│   │   ├── base_agent.py
│   │   ├── supervisor_agent.py
│   │   └── ...
│   │
│   └── clusters/            # 🆕 NEW: Specialized agent clusters
│       ├── __init__.py
│       ├── base_cluster.py  # Abstract cluster base class
│       │
│       ├── webdev/          # WebDev Cluster
│       │   ├── __init__.py
│       │   ├── cluster.py   # WebDevCluster main class
│       │   │
│       │   ├── coding/
│       │   │   ├── __init__.py
│       │   │   ├── code_generation_agent.py
│       │   │   ├── code_completion_agent.py
│       │   │   └── code_review_agent.py
│       │   │
│       │   ├── webgrafik/
│       │   │   ├── __init__.py
│       │   │   ├── ui_design_agent.py
│       │   │   ├── component_generation_agent.py
│       │   │   └── style_system_agent.py
│       │   │
│       │   ├── serveradmin/
│       │   │   ├── __init__.py
│       │   │   ├── infrastructure_agent.py
│       │   │   ├── deployment_agent.py
│       │   │   └── monitoring_agent.py
│       │   │
│       │   └── integration/
│       │       ├── __init__.py
│       │       ├── claude_bridge.py
│       │       ├── github_connector.py
│       │       └── language_parser.py
│       │
│       ├── devops/          # Future: DevOps Cluster
│       │   └── ...
│       │
│       └── data_science/    # Future: Data Science Cluster
│           └── ...
```

---

## 🎯 Design Philosophy

### Core Principles

1. **Cluster-Based Organization**
   - Agents are grouped into logical clusters
   - Each cluster is self-contained
   - Clusters can communicate with each other

2. **Standardized Interface**
   - All agents extend `BaseAgent`
   - All clusters extend `BaseCluster`
   - Consistent API across all implementations

3. **Modular & Extensible**
   - Easy to add new clusters
   - Easy to add agents to existing clusters
   - No tight coupling between clusters

4. **Observable & Testable**
   - Built-in logging
   - Health checks
   - Performance metrics

---

## 📐 Agent Standards

### Agent File Structure

```python
# backend/brain/clusters/webdev/coding/code_generation_agent.py

from typing import Dict, Any
from backend.brain.agents.base_agent import BaseAgent, AgentResult
from backend.modules.llm_client import get_llm_client

class CodeGenerationAgent(BaseAgent):
    """
    Generates code based on specifications.

    Capabilities:
    - Generate functions from descriptions
    - Create classes with full implementation
    - Generate tests for code
    - Support multiple languages (Python, TypeScript, etc.)
    """

    def __init__(self):
        super().__init__(llm_client=get_llm_client())
        self.agent_id = "code_generation"
        self.cluster = "webdev.coding"
        self.version = "1.0.0"

        # Register tools
        self.register_tool("generate_function", self._generate_function)
        self.register_tool("generate_class", self._generate_class)
        self.register_tool("generate_tests", self._generate_tests)

    async def run(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Execute code generation task.

        Args:
            task: Natural language description of code to generate
            context: Additional context (language, framework, style guide, etc.)

        Returns:
            AgentResult with generated code
        """
        context = context or {}
        language = context.get("language", "python")

        prompt = self._build_prompt(task, language, context)

        try:
            code = await self.call_llm(prompt)

            return AgentResult(
                success=True,
                data={
                    "code": code,
                    "language": language,
                    "task": task
                },
                agent_id=self.agent_id,
                metadata={
                    "cluster": self.cluster,
                    "version": self.version
                }
            )
        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                agent_id=self.agent_id
            )

    def _build_prompt(self, task: str, language: str, context: Dict) -> str:
        """Build optimized prompt for code generation."""
        return f"""You are an expert {language} developer.

Task: {task}

Context:
- Language: {language}
- Framework: {context.get('framework', 'standard')}
- Style: {context.get('style', 'clean and maintainable')}

Generate production-ready code:"""

    async def _generate_function(self, spec: Dict[str, Any]) -> str:
        """Generate a single function."""
        # Implementation
        pass

    async def _generate_class(self, spec: Dict[str, Any]) -> str:
        """Generate a complete class."""
        # Implementation
        pass

    async def _generate_tests(self, code: str, language: str) -> str:
        """Generate tests for given code."""
        # Implementation
        pass
```

### Agent Standards Checklist

**Every agent MUST have:**

- ✅ Docstring describing capabilities
- ✅ `agent_id` (unique identifier)
- ✅ `cluster` (cluster.category format)
- ✅ `version` (semantic versioning)
- ✅ `run()` method with type hints
- ✅ `AgentResult` return type
- ✅ Error handling (try/except)
- ✅ Tool registration for specialized functions

**Every agent SHOULD have:**

- ✅ Detailed docstrings for all public methods
- ✅ Type hints for all parameters
- ✅ Context parameter support
- ✅ Metadata in results
- ✅ Logging of important operations

---

## 🏢 Cluster Standards

### Cluster File Structure

```python
# backend/brain/clusters/webdev/cluster.py

from typing import Dict, List, Any
from backend.brain.clusters.base_cluster import BaseCluster
from .coding.code_generation_agent import CodeGenerationAgent
from .coding.code_completion_agent import CodeCompletionAgent
from .coding.code_review_agent import CodeReviewAgent
from .webgrafik.ui_design_agent import UIDesignAgent
from .webgrafik.component_generation_agent import ComponentGenerationAgent
from .webgrafik.style_system_agent import StyleSystemAgent
from .serveradmin.infrastructure_agent import InfrastructureAgent
from .serveradmin.deployment_agent import DeploymentAgent
from .serveradmin.monitoring_agent import MonitoringAgent

class WebDevCluster(BaseCluster):
    """
    Cluster for web development automation.

    Categories:
    - Coding: Code generation, completion, review
    - WebGrafik: UI design, components, styling
    - ServerAdmin: Infrastructure, deployment, monitoring
    - Integration: External service connectors
    """

    def __init__(self):
        super().__init__(
            cluster_id="webdev",
            name="Web Development Cluster",
            version="1.0.0"
        )

        # Initialize agents
        self._init_agents()

    def _init_agents(self):
        """Initialize all cluster agents."""
        # Coding category
        self.register_agent("code_generation", CodeGenerationAgent())
        self.register_agent("code_completion", CodeCompletionAgent())
        self.register_agent("code_review", CodeReviewAgent())

        # WebGrafik category
        self.register_agent("ui_design", UIDesignAgent())
        self.register_agent("component_generation", ComponentGenerationAgent())
        self.register_agent("style_system", StyleSystemAgent())

        # ServerAdmin category
        self.register_agent("infrastructure", InfrastructureAgent())
        self.register_agent("deployment", DeploymentAgent())
        self.register_agent("monitoring", MonitoringAgent())

    async def execute_workflow(
        self,
        workflow_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a multi-agent workflow.

        Examples:
        - "full_stack_feature": Code + UI + Deployment
        - "ui_redesign": UI Design + Components + Styling
        - "deploy_pipeline": Infrastructure + Deployment + Monitoring
        """
        workflows = {
            "full_stack_feature": self._full_stack_workflow,
            "ui_redesign": self._ui_redesign_workflow,
            "deploy_pipeline": self._deploy_workflow,
        }

        if workflow_type not in workflows:
            raise ValueError(f"Unknown workflow: {workflow_type}")

        return await workflows[workflow_type](params)

    async def _full_stack_workflow(self, params: Dict) -> Dict:
        """
        Complete feature: Backend + Frontend + Deployment
        """
        results = {}

        # 1. Generate backend code
        code_agent = self.get_agent("code_generation")
        results["backend"] = await code_agent.run(
            task=params["backend_task"],
            context={"language": "python"}
        )

        # 2. Generate UI
        ui_agent = self.get_agent("ui_design")
        results["ui"] = await ui_agent.run(
            task=params["ui_task"],
            context={"framework": "react"}
        )

        # 3. Generate components
        comp_agent = self.get_agent("component_generation")
        results["components"] = await comp_agent.run(
            task=params["component_task"],
            context={"ui_design": results["ui"]}
        )

        # 4. Deploy
        deploy_agent = self.get_agent("deployment")
        results["deployment"] = await deploy_agent.run(
            task="deploy_feature",
            context={
                "backend_code": results["backend"],
                "frontend_code": results["components"]
            }
        )

        return results

    async def _ui_redesign_workflow(self, params: Dict) -> Dict:
        """UI-focused workflow."""
        # Implementation
        pass

    async def _deploy_workflow(self, params: Dict) -> Dict:
        """Deployment workflow."""
        # Implementation
        pass
```

### Cluster Standards Checklist

**Every cluster MUST have:**

- ✅ `cluster_id` (unique identifier)
- ✅ `name` (human-readable name)
- ✅ `version` (semantic versioning)
- ✅ `_init_agents()` method
- ✅ `execute_workflow()` method
- ✅ Docstring describing categories

**Every cluster SHOULD have:**

- ✅ Pre-defined workflows
- ✅ Health check method
- ✅ Agent dependency management
- ✅ Error handling and rollback

---

## 🔌 Base Classes

### BaseCluster (Abstract)

```python
# backend/brain/clusters/base_cluster.py

from abc import ABC, abstractmethod
from typing import Dict, Optional
from backend.brain.agents.base_agent import BaseAgent

class BaseCluster(ABC):
    """
    Abstract base class for agent clusters.
    """

    def __init__(self, cluster_id: str, name: str, version: str):
        self.cluster_id = cluster_id
        self.name = name
        self.version = version
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent_id: str, agent: BaseAgent):
        """Register an agent in the cluster."""
        self.agents[agent_id] = agent

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def list_agents(self) -> Dict[str, str]:
        """List all agents in cluster."""
        return {
            agent_id: agent.__class__.__name__
            for agent_id, agent in self.agents.items()
        }

    @abstractmethod
    async def execute_workflow(
        self,
        workflow_type: str,
        params: Dict
    ) -> Dict:
        """Execute a multi-agent workflow."""
        pass

    async def health_check(self) -> Dict:
        """Check health of all agents."""
        health = {}
        for agent_id, agent in self.agents.items():
            try:
                # Basic health check - can agent respond?
                result = await agent.run("health_check")
                health[agent_id] = "healthy" if result.success else "unhealthy"
            except Exception as e:
                health[agent_id] = f"error: {str(e)}"

        return {
            "cluster": self.cluster_id,
            "agents": health,
            "overall": "healthy" if all(v == "healthy" for v in health.values()) else "degraded"
        }
```

---

## 🌐 API Integration

### REST API Endpoints

```python
# backend/api/routes/clusters.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from backend.brain.clusters.webdev.cluster import WebDevCluster

router = APIRouter(prefix="/api/clusters", tags=["clusters"])

# Initialize clusters
webdev_cluster = WebDevCluster()

class WorkflowRequest(BaseModel):
    workflow_type: str
    params: Dict[str, Any]

@router.get("/webdev/info")
async def webdev_info():
    """Get WebDev cluster information."""
    return {
        "cluster_id": webdev_cluster.cluster_id,
        "name": webdev_cluster.name,
        "version": webdev_cluster.version,
        "agents": webdev_cluster.list_agents()
    }

@router.get("/webdev/health")
async def webdev_health():
    """Check WebDev cluster health."""
    return await webdev_cluster.health_check()

@router.post("/webdev/workflow")
async def execute_webdev_workflow(request: WorkflowRequest):
    """Execute a WebDev workflow."""
    try:
        result = await webdev_cluster.execute_workflow(
            workflow_type=request.workflow_type,
            params=request.params
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webdev/agent/{agent_id}/run")
async def run_webdev_agent(agent_id: str, task: str, context: Dict = None):
    """Run a specific agent in the cluster."""
    agent = webdev_cluster.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    result = await agent.run(task, context)
    return result.model_dump()
```

---

## 📊 Example Usage

### Python SDK

```python
from backend.brain.clusters.webdev.cluster import WebDevCluster

# Initialize cluster
cluster = WebDevCluster()

# Execute full-stack workflow
result = await cluster.execute_workflow(
    workflow_type="full_stack_feature",
    params={
        "backend_task": "Create user authentication API with JWT",
        "ui_task": "Design login page with modern UI",
        "component_task": "Create login form component",
    }
)

# Use individual agent
code_agent = cluster.get_agent("code_generation")
code = await code_agent.run(
    task="Generate FastAPI endpoint for user login",
    context={"language": "python", "framework": "fastapi"}
)
```

### REST API

```bash
# Get cluster info
curl http://localhost:8000/api/clusters/webdev/info

# Execute workflow
curl -X POST http://localhost:8000/api/clusters/webdev/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "full_stack_feature",
    "params": {
      "backend_task": "Create user API",
      "ui_task": "Design login page"
    }
  }'

# Run specific agent
curl -X POST "http://localhost:8000/api/clusters/webdev/agent/code_generation/run?task=Generate%20login%20function"
```

---

## 🎨 Frontend Integration

```typescript
// frontend/control_deck/src/lib/clusters/webdevApi.ts

export const webdevCluster = {
  getInfo: () => api.get("/api/clusters/webdev/info"),

  getHealth: () => api.get("/api/clusters/webdev/health"),

  executeWorkflow: (workflowType: string, params: Record<string, any>) =>
    api.post("/api/clusters/webdev/workflow", { workflow_type: workflowType, params }),

  runAgent: (agentId: string, task: string, context?: Record<string, any>) =>
    api.post(`/api/clusters/webdev/agent/${agentId}/run`, { task, context }),
};

// Usage in React component
import { webdevCluster } from "@/lib/clusters/webdevApi";

function WebDevClusterPanel() {
  const { data: info } = useQuery({
    queryKey: ["webdev", "info"],
    queryFn: () => webdevCluster.getInfo(),
  });

  const executeWorkflow = useMutation({
    mutationFn: (params: { workflow: string; data: any }) =>
      webdevCluster.executeWorkflow(params.workflow, params.data),
  });

  return (
    <div>
      <h2>WebDev Cluster</h2>
      <p>Agents: {Object.keys(info?.agents || {}).length}</p>
      <button onClick={() => executeWorkflow.mutate({
        workflow: "full_stack_feature",
        data: { backend_task: "..." }
      })}>
        Execute Workflow
      </button>
    </div>
  );
}
```

---

## 📝 Development Checklist

### Creating a New Cluster

- [ ] Create cluster directory under `backend/brain/clusters/`
- [ ] Implement cluster class extending `BaseCluster`
- [ ] Create category subdirectories (coding, webgrafik, etc.)
- [ ] Implement individual agents
- [ ] Add workflow methods
- [ ] Create API routes in `backend/api/routes/clusters.py`
- [ ] Add frontend API client
- [ ] Write tests
- [ ] Update documentation

### Creating a New Agent

- [ ] Create agent file in appropriate category
- [ ] Extend `BaseAgent`
- [ ] Implement `run()` method
- [ ] Add tool methods
- [ ] Register in cluster's `_init_agents()`
- [ ] Write unit tests
- [ ] Update cluster documentation

---

## 🚀 Roadmap

### Phase 1: WebDev Cluster (Current)
- ✅ Base infrastructure
- ⏳ Coding agents
- ⏳ WebGrafik agents
- ⏳ ServerAdmin agents
- ⏳ Integration layer

### Phase 2: DevOps Cluster
- CI/CD automation
- Infrastructure as Code
- Container orchestration

### Phase 3: Data Science Cluster
- Data analysis
- ML model training
- Visualization

---

**Last Updated:** 2025-12-12
**Maintainer:** BRAiN Development Team
**License:** MIT
