"""
Infrastructure Agent - Infrastructure as Code generation and management

Generates Docker, Kubernetes, Terraform configurations for infrastructure deployment.
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

logger = logging.getLogger(__name__)


class InfraType(str, Enum):
    """Infrastructure types"""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    TERRAFORM = "terraform"
    ANSIBLE = "ansible"


@dataclass
class InfraSpec:
    """Infrastructure specification"""
    name: str
    type: InfraType
    services: List[str]
    environment: str  # dev, staging, production
    resources: Dict[str, any] = None


@dataclass
class InfraConfig:
    """Generated infrastructure configuration"""
    spec: InfraSpec
    config_files: Dict[str, str]
    tokens_used: int


class InfrastructureAgent:
    """Infrastructure management agent"""

    def __init__(self):
        self.token_manager = get_token_manager()
        logger.info("InfrastructureAgent initialized")

    @with_error_handling("generate_infra", "infrastructure_agent", reraise=True)
    def generate(self, spec: InfraSpec) -> InfraConfig:
        """Generate infrastructure configuration"""
        logger.info(f"Generating {spec.type.value} config for {spec.name}")

        estimated_tokens = 3000 + len(spec.services) * 500
        available, msg = self.token_manager.check_availability(estimated_tokens, "infra_gen")

        if not available:
            raise Exception(f"Insufficient tokens: {msg}")

        operation_id = self.token_manager.reserve_tokens("infra_gen", estimated_tokens)

        try:
            if spec.type == InfraType.DOCKER:
                config_files = self._generate_docker(spec)
            elif spec.type == InfraType.KUBERNETES:
                config_files = self._generate_kubernetes(spec)
            elif spec.type == InfraType.TERRAFORM:
                config_files = self._generate_terraform(spec)
            else:
                raise NotImplementedError(f"{spec.type.value} not implemented")

            actual_tokens = 2500 + len(spec.services) * 400
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            return InfraConfig(spec=spec, config_files=config_files, tokens_used=actual_tokens)

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def _generate_docker(self, spec: InfraSpec) -> Dict[str, str]:
        """Generate Docker configuration"""
        dockerfile = f"""# {spec.name} Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV ENVIRONMENT={spec.environment}

EXPOSE 8000

CMD ["python", "main.py"]
"""

        compose = f"""version: '3.8'

services:
"""
        for service in spec.services:
            compose += f"""  {service}:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT={spec.environment}
    restart: unless-stopped

"""

        return {
            "Dockerfile": dockerfile,
            "docker-compose.yml": compose
        }

    def _generate_kubernetes(self, spec: InfraSpec) -> Dict[str, str]:
        """Generate Kubernetes manifests"""
        deployment = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {spec.name}
  labels:
    app: {spec.name}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {spec.name}
  template:
    metadata:
      labels:
        app: {spec.name}
    spec:
      containers:
      - name: {spec.name}
        image: {spec.name}:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: {spec.environment}
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
"""

        service = f"""apiVersion: v1
kind: Service
metadata:
  name: {spec.name}-service
spec:
  selector:
    app: {spec.name}
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
"""

        return {
            "deployment.yaml": deployment,
            "service.yaml": service
        }

    def _generate_terraform(self, spec: InfraSpec) -> Dict[str, str]:
        """Generate Terraform configuration"""
        main_tf = f"""terraform {{
  required_version = ">= 1.0"

  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "us-east-1"
}}

resource "aws_instance" "{spec.name}" {{
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  tags = {{
    Name        = "{spec.name}"
    Environment = "{spec.environment}"
  }}
}}
"""

        return {"main.tf": main_tf}
