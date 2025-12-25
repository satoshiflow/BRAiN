# Evidence Export Automation

**Purpose:** Automated daily audit log export with SHA256 integrity verification.

**Version:** 1.0.0
**Last Updated:** 2025-12-25

---

## Overview

This automation exports BRAiN governance audit logs daily at 02:00 server time and stores them as append-only JSONL files with SHA256 hashes for integrity verification.

**Key Features:**
- ✅ **Daily Automated Export**: systemd timer runs at 02:00
- ✅ **SHA256 Integrity**: Every export includes tamper-proof hash
- ✅ **Append-Only**: Existing exports are never modified
- ✅ **90-Day Retention**: Automatic cleanup (configurable)
- ✅ **Fail-Safe**: Clear error messages in systemd journal
- ✅ **Idempotent**: Safe to run multiple times
- ✅ **No Secrets in Repo**: Configuration via ENV or external file

---

## Quick Start

### 1. Prerequisites

- BRAiN backend must be running
- systemd (Linux)
- Required commands: `curl`, `jq`, `sha256sum`
- Permissions: root or dedicated user with write access to `/var/lib/brain/evidence`

### 2. Installation

```bash
# From repository root
cd /opt/brain  # or wherever BRAiN is deployed

# Copy service and timer files to systemd
sudo cp ops/evidence/brain-evidence-export.service /etc/systemd/system/
sudo cp ops/evidence/brain-evidence-export.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable timer (start on boot)
sudo systemctl enable brain-evidence-export.timer

# Start timer
sudo systemctl start brain-evidence-export.timer

# Verify timer is active
sudo systemctl list-timers | grep brain-evidence
```

**Expected output:**
```
NEXT                        LEFT          LAST  PASSED  UNIT                           ACTIVATES
Thu 2025-12-26 02:00:00 UTC 11h left      n/a   n/a     brain-evidence-export.timer    brain-evidence-export.service
```

### 3. Manual Test Run

Before relying on the timer, test the export manually:

```bash
# Run export script directly
sudo bash /opt/brain/ops/evidence/export_audit.sh

# Or trigger via systemd
sudo systemctl start brain-evidence-export.service

# Check status
sudo systemctl status brain-evidence-export.service

# View logs
journalctl -u brain-evidence-export.service -n 50
```

### 4. Verify Export

```bash
# List exported files
ls -lh /var/lib/brain/evidence/

# Expected files:
# - audit-2025-12-25.jsonl
# - audit-2025-12-25.jsonl.sha256

# Verify hash integrity
cd /var/lib/brain/evidence
sha256sum -c audit-2025-12-25.jsonl.sha256

# Expected output: audit-2025-12-25.jsonl: OK
```

---

## Configuration

### Option 1: Environment Variables (Recommended)

Edit `/etc/systemd/system/brain-evidence-export.service`:

```ini
[Service]
Environment="BACKEND_URL=http://localhost:8000"
Environment="EVIDENCE_DIR=/var/lib/brain/evidence"
Environment="RETENTION_DAYS=90"
Environment="DEBUG=1"
```

Then reload systemd:
```bash
sudo systemctl daemon-reload
```

### Option 2: External Configuration File

Create `/etc/brain/evidence-export.conf`:

```bash
# BRAiN Evidence Export Configuration
BACKEND_URL="http://localhost:8000"
EVIDENCE_DIR="/var/lib/brain/evidence"
RETENTION_DAYS=90
DEBUG=0
```

Uncomment in service file:
```ini
EnvironmentFile=-/etc/brain/evidence-export.conf
```

### Option 3: Script Defaults

Edit `ops/evidence/export_audit.sh` directly (not recommended):

```bash
BACKEND_URL="${BACKEND_URL:-http://custom-backend:8000}"
EVIDENCE_DIR="${EVIDENCE_DIR:-/custom/path}"
RETENTION_DAYS="${RETENTION_DAYS:-180}"
```

---

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://localhost:8000` | BRAiN backend URL |
| `EVIDENCE_DIR` | `/var/lib/brain/evidence` | Export storage directory |
| `RETENTION_DAYS` | `90` | Delete files older than N days (0 = disabled) |
| `DEBUG` | `0` | Enable debug logging (1 = enabled) |
| `DRY_RUN` | `0` | Test mode without writes (1 = enabled) |

---

## Export File Format

### JSONL (JSON Lines)

Each line is a complete JSON object representing one audit event:

```jsonl
{"timestamp":"2025-12-25T10:00:00.123456Z","event_type":"sovereign.mode_changed","severity":"INFO","success":true,"reason":"Mode changed from ONLINE to SOVEREIGN","metadata":{"old_mode":"online","new_mode":"sovereign"}}
{"timestamp":"2025-12-25T10:15:00.789012Z","event_type":"sovereign.bundle_loaded","severity":"INFO","success":true,"reason":"Bundle loaded successfully","metadata":{"bundle_id":"llama-3.2-offline"}}
```

### SHA256 Hash File

Format: `HASH  FILENAME`

```
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2  audit-2025-12-25.jsonl
```

---

## Maintenance

### Check Next Run Time

```bash
systemctl status brain-evidence-export.timer

# Output:
# ● brain-evidence-export.timer - BRAiN Governance Audit Export Timer
#    Loaded: loaded (/etc/systemd/system/brain-evidence-export.timer; enabled)
#    Active: active (waiting) since ...
#   Trigger: Thu 2025-12-26 02:00:00 UTC; 11h left
```

### View Logs

```bash
# Recent logs (service)
journalctl -u brain-evidence-export.service -n 100

# Follow logs in real-time
journalctl -u brain-evidence-export.service -f

# Logs from last run
journalctl -u brain-evidence-export.service --since today

# Timer logs
journalctl -u brain-evidence-export.timer -f
```

### Manual Export

```bash
# Trigger export immediately
sudo systemctl start brain-evidence-export.service

# Check status
sudo systemctl status brain-evidence-export.service

# View output
journalctl -u brain-evidence-export.service -n 50 --no-pager
```

### Disable/Enable Timer

```bash
# Disable (stop automatic exports)
sudo systemctl disable brain-evidence-export.timer
sudo systemctl stop brain-evidence-export.timer

# Enable (resume automatic exports)
sudo systemctl enable brain-evidence-export.timer
sudo systemctl start brain-evidence-export.timer
```

### Change Schedule

Edit `/etc/systemd/system/brain-evidence-export.timer`:

```ini
[Timer]
# Change from 02:00 to 03:00
OnCalendar=*-*-* 03:00:00
```

Reload systemd:
```bash
sudo systemctl daemon-reload
sudo systemctl restart brain-evidence-export.timer
```

### Manual Cleanup (Retention)

```bash
# Delete exports older than 90 days
find /var/lib/brain/evidence -name "audit-*.jsonl*" -type f -mtime +90 -delete

# Or use the script's retention feature
RETENTION_DAYS=90 /opt/brain/ops/evidence/export_audit.sh
```

---

## Troubleshooting

### Problem: Export fails with "Backend unreachable"

**Symptoms:**
```
[ERROR] Backend is unreachable: http://localhost:8000
[ERROR] Health check failed. Is BRAiN backend running?
```

**Solutions:**

1. **Check if backend is running:**
   ```bash
   docker ps | grep brain-backend
   curl http://localhost:8000/health
   ```

2. **Check backend URL in service:**
   ```bash
   sudo systemctl cat brain-evidence-export.service | grep BACKEND_URL
   ```

3. **Verify network connectivity:**
   ```bash
   curl -v http://localhost:8000/api/sovereign-mode/audit?limit=1
   ```

---

### Problem: Export file not created

**Symptoms:**
- Script runs successfully but no file in `/var/lib/brain/evidence/`

**Solutions:**

1. **Check directory permissions:**
   ```bash
   ls -ld /var/lib/brain/evidence
   # Should be writable by user running service (root)
   ```

2. **Create directory manually:**
   ```bash
   sudo mkdir -p /var/lib/brain/evidence
   sudo chown root:root /var/lib/brain/evidence
   sudo chmod 0755 /var/lib/brain/evidence
   ```

3. **Check logs for errors:**
   ```bash
   journalctl -u brain-evidence-export.service -n 100 | grep ERROR
   ```

---

### Problem: Hash verification fails

**Symptoms:**
```bash
sha256sum -c audit-2025-12-25.jsonl.sha256
# Output: audit-2025-12-25.jsonl: FAILED
```

**Diagnosis:**
- File was modified after hash was computed
- File corruption
- Hash file corruption

**Solutions:**

1. **Re-compute hash:**
   ```bash
   sha256sum audit-2025-12-25.jsonl > audit-2025-12-25.jsonl.sha256.new
   sha256sum -c audit-2025-12-25.jsonl.sha256.new
   ```

2. **Check file permissions (should be read-only):**
   ```bash
   ls -l audit-2025-12-25.jsonl
   # Expected: -r--r--r-- (0444)
   ```

3. **If file is corrupted, re-export:**
   ```bash
   sudo systemctl start brain-evidence-export.service
   ```

---

### Problem: Timer not triggering

**Symptoms:**
- Timer shows "active (waiting)" but never runs
- `systemctl list-timers` shows no next run

**Solutions:**

1. **Check timer status:**
   ```bash
   systemctl status brain-evidence-export.timer
   systemctl list-timers --all | grep brain-evidence
   ```

2. **Restart timer:**
   ```bash
   sudo systemctl restart brain-evidence-export.timer
   ```

3. **Check timer syntax:**
   ```bash
   systemctl cat brain-evidence-export.timer
   systemd-analyze verify brain-evidence-export.timer
   ```

4. **Enable persistent mode:**
   Edit timer file, ensure:
   ```ini
   [Timer]
   Persistent=true
   ```

---

### Problem: Permission denied

**Symptoms:**
```
[ERROR] Failed to create directory: /var/lib/brain/evidence
Permission denied
```

**Solutions:**

1. **Run as root:**
   ```bash
   sudo systemctl start brain-evidence-export.service
   ```

2. **Create directory with correct permissions:**
   ```bash
   sudo mkdir -p /var/lib/brain/evidence
   sudo chown root:root /var/lib/brain/evidence
   sudo chmod 0755 /var/lib/brain/evidence
   ```

3. **Or run as dedicated user:**
   Edit service file:
   ```ini
   [Service]
   User=brain
   Group=brain
   ```
   Then create user and set permissions:
   ```bash
   sudo useradd -r -s /bin/false brain
   sudo chown brain:brain /var/lib/brain/evidence
   ```

---

## Security Notes

- ✅ **Append-Only**: Exports are never modified after creation (0444 permissions)
- ✅ **SHA256 Integrity**: Tamper detection via cryptographic hash
- ✅ **No Secrets in Repo**: Configuration via ENV or external file
- ✅ **Systemd Hardening**: `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`
- ✅ **Resource Limits**: CPU and memory limits prevent resource exhaustion
- ✅ **Audit Trail**: All operations logged to systemd journal

**For Production:**
- Store exports on dedicated partition (prevent disk exhaustion)
- Encrypt exports at rest (LUKS, eCryptfs)
- Ship exports to off-site storage (S3, SFTP)
- Implement access control (AppArmor, SELinux)
- Monitor export failures (Prometheus alerting)

---

## SIEM Integration

### Splunk HEC (HTTP Event Collector)

```bash
# Install Splunk Universal Forwarder
# Configure inputs.conf:

[monitor:///var/lib/brain/evidence/*.jsonl]
disabled = false
index = brain_governance
sourcetype = brain:audit:jsonl
```

### ELK Stack (Elasticsearch, Logstash, Kibana)

```bash
# Logstash input configuration:

input {
  file {
    path => "/var/lib/brain/evidence/*.jsonl"
    start_position => "beginning"
    codec => "json_lines"
    type => "brain_audit"
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "brain-audit-%{+YYYY.MM.dd}"
  }
}
```

### Rsyslog (Forward to SIEM)

```bash
# /etc/rsyslog.d/brain-evidence.conf

# Monitor evidence directory
input(type="imfile"
      File="/var/lib/brain/evidence/*.jsonl"
      Tag="brain:audit"
      StateFile="brain-evidence-state")

# Forward to SIEM
action(type="omfwd"
       target="siem.example.com"
       port="514"
       protocol="tcp")
```

---

## Compliance Notes

**SOC 2 Type II:**
- CC6.6: Audit log retention (90 days hot, 7 years cold)
- CC7.2: Tamper-proof audit trail (SHA256 hash)
- CC8.1: Automated compliance export (daily systemd timer)

**ISO 27001:**
- A.12.4.1: Event logging (audit events)
- A.12.4.2: Protection of log information (SHA256, read-only)
- A.12.4.3: Administrator and operator logs (systemd journal)

**NIST CSF:**
- PR.PT-1: Audit logs are determined (audit export)
- DE.CM-1: Network monitoring (governance events)
- DE.AE-3: Event data are aggregated (JSONL format)

---

## Support

**Issues:**
- Check troubleshooting section above
- Review systemd journal: `journalctl -u brain-evidence-export.service -f`
- Test script manually: `sudo bash /opt/brain/ops/evidence/export_audit.sh`

**Monitoring:**
- Timer status: `systemctl status brain-evidence-export.timer`
- Next run: `systemctl list-timers | grep brain-evidence`
- Last run: `journalctl -u brain-evidence-export.service --since "1 day ago"`

**Files:**
- Script: `/opt/brain/ops/evidence/export_audit.sh`
- Service: `/etc/systemd/system/brain-evidence-export.service`
- Timer: `/etc/systemd/system/brain-evidence-export.timer`
- Exports: `/var/lib/brain/evidence/audit-YYYY-MM-DD.jsonl`

---

**End of README**
