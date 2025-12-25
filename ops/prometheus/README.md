# Prometheus Governance Sensor

**Purpose:** Read-only Prometheus monitoring for BRAiN governance metrics.

**Version:** 1.0.0
**Last Updated:** 2025-12-25

---

## Overview

This Prometheus deployment scrapes governance metrics from the BRAiN backend and stores them for monitoring, alerting, and compliance.

**Key Features:**
- ✅ **Read-Only**: No writes to BRAiN backend
- ✅ **Internal Network**: Uses existing `brain_internal` Docker network
- ✅ **90-Day Retention**: Compliance-ready metric storage
- ✅ **Localhost Only**: Port 9090 bound to 127.0.0.1 (not publicly exposed)
- ✅ **Zero Governance Changes**: No modifications to G1-G4 code

---

## Quick Start

### 1. Prerequisites

- BRAiN backend must be running (`docker ps | grep brain-backend`)
- Docker and Docker Compose installed
- `brain_internal` network must exist (created by main docker-compose.yml)

### 2. Start Prometheus

```bash
# From repository root
cd ops/prometheus

# Start Prometheus
docker compose -f docker-compose.prometheus.yml up -d

# Check logs
docker compose -f docker-compose.prometheus.yml logs -f
```

### 3. Verify Deployment

```bash
# Check Prometheus is ready
curl -s http://localhost:9090/-/ready
# Expected output: Prometheus Server is Ready.

# Check Prometheus health
curl -s http://localhost:9090/-/healthy
# Expected output: Prometheus Server is Healthy.

# Check targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health, lastScrape: .lastScrape}'

# Expected output:
# {
#   "job": "brain-governance",
#   "health": "up",
#   "lastScrape": "2025-12-25T10:30:45.123Z"
# }
```

### 4. Access Prometheus UI

Open in browser: http://localhost:9090

**Default Credentials:** None (read-only, localhost access only)

---

## Metrics Reference

### Governance Metrics (Job: brain-governance)

**Endpoint:** `http://backend:8000/api/sovereign-mode/metrics`

**Key Metrics:**

| Metric Name | Type | Description |
|-------------|------|-------------|
| `sovereign_mode_switch_total{target_mode}` | Counter | Total mode switches by target mode |
| `sovereign_preflight_failure_total{gate}` | Counter | Preflight check failures by gate |
| `sovereign_override_usage_total` | Counter | Total override usage count |
| `sovereign_bundle_signature_failure_total` | Counter | Bundle signature validation failures |
| `sovereign_bundle_quarantine_total` | Counter | Total bundles quarantined |
| `axe_trust_violation_total{trust_tier}` | Counter | AXE trust tier violations |
| `sovereign_override_active` | Gauge | Override currently active (0 or 1) |

**Labels:**
- `target_mode`: `online`, `offline`, `sovereign`, `quarantine`
- `gate`: `network_gate`, `ipv6_gate`, `dmz_gate`, `bundle_trust_gate`
- `trust_tier`: `core`, `internal`, `external`

### IPv6 Metrics (Job: brain-ipv6)

**Endpoint:** `http://backend:8000/api/sovereign-mode/ipv6/metrics/prometheus`

**Key Metrics:**

| Metric Name | Type | Description |
|-------------|------|-------------|
| `ipv6_enabled` | Gauge | IPv6 status (1=enabled, 0=disabled) |
| `ipv6_packets_received_total` | Counter | Total IPv6 packets received |
| `ipv6_packets_sent_total` | Counter | Total IPv6 packets sent |
| `ipv6_firewall_dropped_packets_total` | Counter | Packets dropped by IPv6 firewall |

---

## Query Examples

### Basic Queries (Prometheus UI)

**1. Check if override is currently active:**
```promql
sovereign_override_active
```
Expected: `0` (safe) or `1` (override active - WARNING)

**2. Total mode switches to SOVEREIGN mode:**
```promql
sovereign_mode_switch_total{target_mode="sovereign"}
```

**3. Preflight failure rate (last 1 hour):**
```promql
rate(sovereign_preflight_failure_total[1h])
```

**4. Bundle quarantine count:**
```promql
sovereign_bundle_quarantine_total
```

**5. AXE trust violations by tier:**
```promql
axe_trust_violation_total
```

### Advanced Queries

**6. Mode switch rate (per minute, last 5 minutes):**
```promql
rate(sovereign_mode_switch_total[5m]) * 60
```

**7. Preflight failures by gate (last 24 hours):**
```promql
increase(sovereign_preflight_failure_total[24h])
```

**8. Override usage trend (last 7 days):**
```promql
increase(sovereign_override_usage_total[7d])
```

**9. Bundle signature failure anomaly detection:**
```promql
delta(sovereign_bundle_signature_failure_total[1h]) > 0
```

**10. Total governance violations (composite):**
```promql
sum(
  rate(sovereign_preflight_failure_total[1h]) +
  rate(sovereign_bundle_signature_failure_total[1h]) +
  rate(axe_trust_violation_total[1h])
)
```

---

## Alert Rules (Example)

These rules can be loaded into Prometheus when Alertmanager is deployed.

**File:** `rules/governance_alerts.yml` (not yet deployed)

```yaml
groups:
  - name: governance_critical
    interval: 30s
    rules:
      # GA-001: Governance Override Active
      - alert: GovernanceOverrideActive
        expr: sovereign_override_active == 1
        for: 5m
        labels:
          severity: critical
          component: governance
          alert_id: GA-001
        annotations:
          summary: "Governance Override Currently Active"
          description: "Owner override is active. Mode switch governance bypassed."

      # GA-002: Bundle Quarantine Triggered
      - alert: BundleQuarantineTriggered
        expr: increase(sovereign_bundle_quarantine_total[1m]) > 0
        labels:
          severity: critical
          component: governance
          alert_id: GA-002
        annotations:
          summary: "Bundle Quarantined - Trust Violation"
          description: "A bundle has been quarantined due to signature validation failure."

      # GA-003: AXE Trust Tier Violation
      - alert: AXETrustViolation
        expr: rate(axe_trust_violation_total[5m]) > 0.1
        labels:
          severity: critical
          component: governance
          alert_id: GA-003
        annotations:
          summary: "AXE Trust Tier Violation Detected"
          description: "External requests are violating trust tier policies."

      # GA-004: Mode Switch Rate Anomaly
      - alert: ModeSwitchRateAnomaly
        expr: rate(sovereign_mode_switch_total[5m]) > 0.5
        for: 10m
        labels:
          severity: warning
          component: governance
          alert_id: GA-004
        annotations:
          summary: "Abnormally High Mode Switch Rate"
          description: "Mode switches are occurring more frequently than expected."

      # GA-006: Preflight Failure Rate High
      - alert: PreflightFailureRateHigh
        expr: rate(sovereign_preflight_failure_total[1h]) > 0.1
        for: 15m
        labels:
          severity: warning
          component: governance
          alert_id: GA-006
        annotations:
          summary: "High Preflight Failure Rate"
          description: "Preflight checks are failing at an elevated rate."
```

---

## Maintenance

### Stop Prometheus

```bash
docker compose -f ops/prometheus/docker-compose.prometheus.yml down
```

### Restart Prometheus

```bash
docker compose -f ops/prometheus/docker-compose.prometheus.yml restart
```

### Reload Configuration (without restart)

```bash
# Hot reload (requires --web.enable-lifecycle flag)
curl -X POST http://localhost:9090/-/reload
```

### View Logs

```bash
docker compose -f ops/prometheus/docker-compose.prometheus.yml logs -f
```

### Clean Up (Delete Data)

```bash
# Stop and remove container + volume
docker compose -f ops/prometheus/docker-compose.prometheus.yml down -v
```

**⚠️ WARNING:** This will delete all stored metrics (90 days of data).

---

## Troubleshooting

### Problem: Target "brain-governance" is DOWN

**Symptoms:**
```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.job=="brain-governance") | .health'
# Output: "down"
```

**Diagnosis:**

1. **Check if backend is running:**
   ```bash
   docker ps | grep brain-backend
   ```

2. **Check if backend metrics endpoint is accessible:**
   ```bash
   docker exec brain-prometheus wget -O- http://backend:8000/api/sovereign-mode/metrics
   ```

3. **Check Prometheus logs:**
   ```bash
   docker logs brain-prometheus | grep error
   ```

**Solutions:**

- **Backend not running:** Start backend first
  ```bash
  docker compose up -d backend
  ```

- **Network issue:** Verify Prometheus is on `brain_internal` network
  ```bash
  docker network inspect brain_brain_internal | grep brain-prometheus
  ```

- **Wrong endpoint:** Check `prometheus.yml` has correct `metrics_path`

---

### Problem: Prometheus UI not accessible

**Symptoms:**
```bash
curl http://localhost:9090
# Connection refused
```

**Solutions:**

1. **Check if Prometheus is running:**
   ```bash
   docker ps | grep brain-prometheus
   ```

2. **Check if port is bound correctly:**
   ```bash
   docker port brain-prometheus
   # Expected: 9090/tcp -> 127.0.0.1:9090
   ```

3. **Check firewall:**
   ```bash
   sudo ufw status | grep 9090
   ```

---

### Problem: Metrics are not being scraped

**Symptoms:** Queries return no data or "No data"

**Diagnosis:**

1. **Check scrape status:**
   ```bash
   curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, lastError: .lastError}'
   ```

2. **Manual scrape test:**
   ```bash
   curl http://localhost:8000/api/sovereign-mode/metrics
   ```

**Solutions:**

- **Check scrape interval:** Verify metrics are updating (may take up to 30s)
- **Check Prometheus logs:** Look for scrape errors
- **Verify backend is healthy:** `curl http://localhost:8000/health`

---

## Configuration

### Change Scrape Interval

Edit `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s  # Change from 30s to 15s
```

Reload configuration:
```bash
curl -X POST http://localhost:9090/-/reload
```

### Change Retention Period

Edit `docker-compose.prometheus.yml`:

```yaml
command:
  - '--storage.tsdb.retention.time=180d'  # Change from 90d to 180d
```

Restart Prometheus:
```bash
docker compose -f docker-compose.prometheus.yml restart
```

### Add Custom Labels

Edit `prometheus.yml`:

```yaml
global:
  external_labels:
    datacenter: 'eu-central-1'  # Add custom label
    team: 'platform'
```

---

## Integration with Grafana (Future)

Once Grafana is deployed, import governance dashboards:

1. **Add Prometheus data source:**
   - URL: `http://prometheus:9090`
   - Access: Server (not browser)

2. **Import dashboards:**
   - Dashboard ID: (to be created)
   - Data source: Prometheus

3. **Pre-built dashboards:**
   - Governance Overview (G1-G4 health)
   - Mode Switch Timeline
   - Override Tracking
   - Bundle Trust Status
   - AXE Security Violations

---

## Security Notes

- ✅ **Read-Only**: Prometheus only reads metrics, never writes to backend
- ✅ **Localhost Binding**: Port 9090 bound to 127.0.0.1 (not publicly exposed)
- ✅ **Internal Network**: Uses existing `brain_internal` network (no external access)
- ✅ **No Secrets**: No authentication required (internal service)
- ✅ **Resource Limits**: CPU and memory limits prevent resource exhaustion

**For Production:**
- Consider adding authentication (basic auth, OAuth)
- Expose only via reverse proxy (Nginx)
- Enable TLS for Prometheus UI
- Implement network policies (Kubernetes) or firewall rules (Docker)

---

## Support

**Issues:**
- Check troubleshooting section above
- Review Prometheus logs: `docker logs brain-prometheus`
- Consult Prometheus documentation: https://prometheus.io/docs/

**Monitoring:**
- Prometheus UI: http://localhost:9090
- Targets: http://localhost:9090/targets
- Configuration: http://localhost:9090/config

---

**End of README**
