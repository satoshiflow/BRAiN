# BRAiN Grafana Monitoring

Prometheus + Grafana monitoring stack für Constitutional Agents Framework.

## Übersicht

Dieses Monitoring-Setup sammelt und visualisiert Metriken für:
- **Supervisor Operations** - Genehmigungsanfragen, Entscheidungen, Response-Zeiten
- **HITL (Human-in-the-Loop)** - Queue-Größe, Genehmigungen, Approval-Zeiten
- **Policy Engine** - Policy-Evaluierungen, aktive Policies, Regeln
- **Agent Operations** - Code-Generierung, Deployments, Compliance-Checks
- **Authentication** - Login-Versuche, aktive Sessions, Token-Refreshes
- **Mission System** - Queue-Größe, Ausführungszeiten

## Schnellstart

### 1. Monitoring-Stack starten

```bash
# Netzwerk erstellen (falls noch nicht vorhanden)
docker network create brain-network

# Monitoring-Stack mit Backend starten
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Logs prüfen
docker compose logs -f prometheus grafana
```

### 2. Auf Services zugreifen

- **Grafana:** http://localhost:3100
  - User: `admin`
  - Password: `admin` (beim ersten Login ändern!)

- **Prometheus:** http://localhost:9090

- **BRAiN Metrics:** http://localhost:8000/metrics

### 3. Dashboard ansehen

Das **Constitutional Agents Dashboard** wird automatisch geladen:
1. Öffne Grafana (http://localhost:3100)
2. Login mit admin/admin
3. Gehe zu **Dashboards** → **BRAiN** Ordner
4. Wähle **BRAiN - Constitutional Agents**

## Metriken-Übersicht

### Supervisor Metriken

```promql
# Gesamte Supervision Requests
sum(increase(supervisor_requests_total[5m]))

# Approval Rate nach Risk Level
rate(supervisor_approvals_total[5m])

# Response Time (95th Percentile)
histogram_quantile(0.95, sum(rate(supervisor_response_time_seconds_bucket[5m])) by (le, risk_level))
```

### HITL Metriken

```promql
# Aktuelle Queue-Größe
hitl_queue_size

# Genehmigungen pro Stunde
sum by(decision) (increase(hitl_approvals_total[1h]))

# Durchschnittliche Approval-Zeit
rate(hitl_approval_time_seconds_sum[5m]) / rate(hitl_approval_time_seconds_count[5m])
```

### Policy Engine Metriken

```promql
# Policy-Evaluierungen nach Effect
sum by(effect) (rate(policy_evaluations_total[5m]))

# Aktive Policies
policy_active_policies

# Evaluation Response Time
histogram_quantile(0.99, sum(rate(policy_evaluation_time_seconds_bucket[5m])) by (le))
```

### Agent Operations Metriken

```promql
# Erfolgreiche Operations pro Agent
sum by(agent, operation) (rate(agent_operations_total{status="success"}[5m]))

# Code-Generierungen
sum(increase(agent_code_generation_total[1h]))

# Deployments nach Environment
sum by(environment, status) (increase(agent_deployments_total[1h]))
```

## Dashboard-Panels

Das vorkonfigurierte Dashboard enthält:

1. **Supervision Requests (5m)** - Gauge für aktuelle Request-Rate
2. **HITL Queue Size** - Gauge mit Thresholds (Gelb >5, Rot >10)
3. **Supervisor Decisions Rate** - Timeseries für Approvals vs Denials
4. **Policy Decisions (1h)** - Pie Chart der Policy-Effekte
5. **Supervisor Response Time** - p95 & p99 Latencies
6. **Agent Operations Rate** - Erfolgreiche Operations pro Agent
7. **HITL Approvals (1h)** - Stacked Bars für Approved/Denied
8. **Login Attempts Rate** - Success vs Failure Rate

## Alerting (Optional)

Beispiel Prometheus Alert Rules:

```yaml
# /etc/prometheus/alerts/brain.yml
groups:
  - name: brain_alerts
    interval: 30s
    rules:
      - alert: HITLQueueTooLarge
        expr: hitl_queue_size > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "HITL Queue ist groß ({{ $value }} Requests)"

      - alert: HighDenialRate
        expr: rate(supervisor_denials_total[5m]) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Hohe Denial-Rate: {{ $value }} denials/sec"

      - alert: SlowSupervisorResponses
        expr: histogram_quantile(0.95, sum(rate(supervisor_response_time_seconds_bucket[5m])) by (le)) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Supervisor Response Time > 5s (p95)"
```

## Konfiguration

### Prometheus

Konfiguration: `prometheus.yml`
- Scrape Interval: 15s
- Metrics Path: `/metrics`
- Target: `backend:8000`

### Grafana

Konfiguration automatisch provisioniert:
- Datasource: `datasources/prometheus.yml`
- Dashboards: `dashboards/dashboards.yml`

## Metriken im Backend aktivieren

Das Backend exportiert Metriken automatisch via `/metrics` Endpoint.

Metriken werden in `backend/app/core/metrics.py` definiert und können so verwendet werden:

```python
from app.core.metrics import record_supervisor_request

# Supervision Request aufzeichnen
record_supervisor_request(
    agent="CoderAgent",
    risk_level="high",
    approved=True,
    duration=1.2
)
```

## Troubleshooting

### Prometheus kann Backend nicht erreichen

```bash
# Prüfe ob Services im gleichen Netzwerk sind
docker network inspect brain-network

# Prüfe Backend-Logs
docker compose logs backend
```

### Grafana zeigt keine Daten

1. Prüfe Prometheus Targets: http://localhost:9090/targets
2. Prüfe ob Metriken verfügbar: http://localhost:8000/metrics
3. Prüfe Grafana Datasource: Settings → Data sources → Prometheus → Test

### Dashboard fehlt

```bash
# Dashboard neu provisionieren
docker compose restart grafana

# Manuell importieren:
# Grafana UI → Create → Import → Upload JSON File
# Datei: grafana/dashboards/constitutional-agents.json
```

## Weiterführende Links

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/best-practices-for-creating-dashboards/)

## Produktion

Für Production-Deployments:

1. **Persistent Storage** für Prometheus konfigurieren
2. **Retention Policy** anpassen (default: 15 Tage)
3. **Alertmanager** für Notifications einrichten
4. **Grafana Authentication** mit OAuth/LDAP konfigurieren
5. **TLS/SSL** für alle Endpoints aktivieren
6. **Backup** Strategie für Grafana Dashboards

```bash
# Prometheus mit längerer Retention
prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.retention.time=90d \
  --storage.tsdb.retention.size=50GB
```
