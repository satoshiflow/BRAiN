"""
Deployment Agent - Automated deployment orchestration

Manages deployment pipelines, CI/CD workflows, and release automation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.token_manager import get_token_manager
from core.error_handler import with_error_handling
from core.self_healing import with_retry

logger = logging.getLogger(__name__)


class DeploymentStrategy(str, Enum):
    """Deployment strategies"""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    RECREATE = "recreate"


class CIPlatform(str, Enum):
    """CI/CD platforms"""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"
    CIRCLE_CI = "circle_ci"


@dataclass
class DeploymentSpec:
    """Deployment specification"""
    project_name: str
    platform: CIPlatform
    strategy: DeploymentStrategy
    environments: List[str]
    tests_required: bool = True
    auto_deploy: bool = False


@dataclass
class DeploymentConfig:
    """Generated deployment configuration"""
    spec: DeploymentSpec
    pipeline_files: Dict[str, str]
    tokens_used: int


class DeploymentAgent:
    """Automated deployment agent"""

    def __init__(self):
        self.token_manager = get_token_manager()
        logger.info("DeploymentAgent initialized")

    @with_error_handling("generate_deployment", "deployment_agent", reraise=True)
    def generate(self, spec: DeploymentSpec) -> DeploymentConfig:
        """Generate deployment pipeline configuration"""
        logger.info(f"Generating {spec.platform.value} pipeline for {spec.project_name}")

        estimated_tokens = 4000
        available, msg = self.token_manager.check_availability(estimated_tokens, "deployment_gen")

        if not available:
            raise Exception(f"Insufficient tokens: {msg}")

        operation_id = self.token_manager.reserve_tokens("deployment_gen", estimated_tokens)

        try:
            if spec.platform == CIPlatform.GITHUB_ACTIONS:
                pipeline_files = self._generate_github_actions(spec)
            elif spec.platform == CIPlatform.GITLAB_CI:
                pipeline_files = self._generate_gitlab_ci(spec)
            else:
                raise NotImplementedError(f"{spec.platform.value} not implemented")

            actual_tokens = 3500
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            return DeploymentConfig(
                spec=spec,
                pipeline_files=pipeline_files,
                tokens_used=actual_tokens
            )

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def _generate_github_actions(self, spec: DeploymentSpec) -> Dict[str, str]:
        """Generate GitHub Actions workflow"""
        test_step = """      - name: Run Tests
        run: |
          npm test
          npm run test:coverage
""" if spec.tests_required else ""

        deploy_steps = ""
        for env in spec.environments:
            deploy_steps += f"""      - name: Deploy to {env}
        if: github.ref == 'refs/heads/{env == 'production' and 'main' or env}'
        run: |
          echo "Deploying to {env}"
          # Add deployment commands here

"""

        workflow = f"""name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop, staging ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

{test_step}

  build:
    needs: test
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Build
        run: npm run build

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build
          path: dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    steps:
      - uses: actions/checkout@v3

      - name: Download artifacts
        uses: actions/download-artifact@v3
        with:
          name: build
          path: dist/

{deploy_steps}
"""

        return {".github/workflows/ci-cd.yml": workflow}

    def _generate_gitlab_ci(self, spec: DeploymentSpec) -> Dict[str, str]:
        """Generate GitLab CI configuration"""
        test_stage = """test:
  stage: test
  script:
    - npm test
    - npm run test:coverage
  coverage: '/Coverage: \\d+\\.\\d+%/'
""" if spec.tests_required else ""

        gitlab_ci = f"""stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/

{test_stage}

deploy:
  stage: deploy
  script:
    - echo "Deploying to production"
    # Add deployment commands
  only:
    - main
"""

        return {".gitlab-ci.yml": gitlab_ci}
