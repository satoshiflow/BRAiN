"""
Monitoring Agent - System and application monitoring setup

Generates monitoring, logging, and alerting configurations for production systems.
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


class MonitoringStack(str, Enum):
    """Monitoring stacks"""
    PROMETHEUS_GRAFANA = "prometheus_grafana"
    ELK = "elk"
    DATADOG = "datadog"
    NEW_RELIC = "new_relic"


@dataclass
class MonitoringSpec:
    """Monitoring specification"""
    project_name: str
    stack: MonitoringStack
    metrics: List[str]
    alerts: List[str]
    log_retention_days: int = 30


@dataclass
class MonitoringConfig:
    """Generated monitoring configuration"""
    spec: MonitoringSpec
    config_files: Dict[str, str]
    tokens_used: int


class MonitoringAgent:
    """System monitoring agent"""

    def __init__(self):
        self.token_manager = get_token_manager()
        logger.info("MonitoringAgent initialized")

    @with_error_handling("generate_monitoring", "monitoring_agent", reraise=True)
    def generate(self, spec: MonitoringSpec) -> MonitoringConfig:
        """Generate monitoring configuration"""
        logger.info(f"Generating {spec.stack.value} config for {spec.project_name}")

        estimated_tokens = 3000
        available, msg = self.token_manager.check_availability(estimated_tokens, "monitoring_gen")

        if not available:
            raise Exception(f"Insufficient tokens: {msg}")

        operation_id = self.token_manager.reserve_tokens("monitoring_gen", estimated_tokens)

        try:
            if spec.stack == MonitoringStack.PROMETHEUS_GRAFANA:
                config_files = self._generate_prometheus_grafana(spec)
            elif spec.stack == MonitoringStack.ELK:
                config_files = self._generate_elk(spec)
            else:
                raise NotImplementedError(f"{spec.stack.value} not implemented")

            actual_tokens = 2800
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            return MonitoringConfig(
                spec=spec,
                config_files=config_files,
                tokens_used=actual_tokens
            )

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def _generate_prometheus_grafana(self, spec: MonitoringSpec) -> Dict[str, str]:
        """Generate Prometheus + Grafana configuration"""
        prometheus_yml = f"""global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - 'alerts.yml'

scrape_configs:
  - job_name: '{spec.project_name}'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
"""

        alerts_yml = f"""groups:
  - name: {spec.project_name}_alerts
    rules:
"""
        for alert in spec.alerts:
            alerts_yml += f"""      - alert: {alert}
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{{{$labels.instance}}}} down"
          description: "{{{{$labels.instance}}}} has been down for more than 1 minute"

"""

        grafana_dashboard = f"""{{
  "dashboard": {{
    "title": "{spec.project_name} Dashboard",
    "panels": [
      {{
        "title": "CPU Usage",
        "targets": [
          {{
            "expr": "rate(process_cpu_seconds_total[5m])"
          }}
        ]
      }},
      {{
        "title": "Memory Usage",
        "targets": [
          {{
            "expr": "process_resident_memory_bytes"
          }}
        ]
      }}
    ]
  }}
}}
"""

        return {
            "prometheus.yml": prometheus_yml,
            "alerts.yml": alerts_yml,
            "grafana-dashboard.json": grafana_dashboard
        }

    def _generate_elk(self, spec: MonitoringSpec) -> Dict[str, str]:
        """Generate ELK stack configuration"""
        logstash_conf = f"""input {{
  beats {{
    port => 5044
  }}
}}

filter {{
  grok {{
    match => {{ "message" => "%{{COMBINEDAPACHELOG}}" }}
  }}
  date {{
    match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
  }}
}}

output {{
  elasticsearch {{
    hosts => ["elasticsearch:9200"]
    index => "{spec.project_name}-%{{+YYYY.MM.dd}}"
  }}
}}
"""

        filebeat_yml = f"""filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/{spec.project_name}/*.log

output.logstash:
  hosts: ["logstash:5044"]

logging.level: info
"""

        return {
            "logstash.conf": logstash_conf,
            "filebeat.yml": filebeat_yml
        }
