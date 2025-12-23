# Sovereign Mode Module

**Version:** 1.0.0
**Status:** Production Ready
**Security Level:** High (Fail-Closed Design)

## Overview

The Sovereign Mode module provides secure offline operation for BRAiN with strict network isolation, model bundle management, and comprehensive validation. It ensures the system can operate autonomously without external dependencies while maintaining security and auditability.

## Key Features

- 🔒 **Fail-Closed Security** - Blocks all external access by default in offline modes
- 📦 **Bundle Management** - Offline model bundle discovery, validation, and loading
- 🔐 **SHA256 Validation** - Strict hash-based integrity verification
- 🌐 **Network Guards** - HTTP request interception and blocking
- 🔍 **Auto-Detection** - Automatic network connectivity monitoring
- 📊 **Audit Logging** - Comprehensive operation tracking
- ⚡ **Policy Integration** - Works with existing Policy Engine

## Architecture

```
sovereign_mode/
├── __init__.py           # Package exports
├── schemas.py            # Pydantic data models
├── service.py            # Core orchestration service
├── router.py             # FastAPI endpoints
├── mode_detector.py      # Network connectivity detection
├── bundle_manager.py     # Bundle discovery & management
├── hash_validator.py     # SHA256 validation
├── network_guard.py      # HTTP request blocking
└── README.md             # This file
```

## Operation Modes

| Mode | Description | Network Access | External Models | Use Case |
|------|-------------|----------------|-----------------|----------|
| **ONLINE** | Normal operation | ✅ Full | ✅ Allowed | Standard use |
| **OFFLINE** | Offline with bundles | ❌ Blocked | ❌ Bundles only | Air-gapped |
| **SOVEREIGN** | Strict offline | ❌ Blocked | ❌ Bundles only | Maximum security |
| **QUARANTINE** | Isolated mode | ❌ All blocked | ❌ None | Emergency isolation |

## Quick Start

### 1. Check Current Status

```bash
curl http://localhost:8000/api/sovereign-mode/status
```

**Response:**
```json
{
  "mode": "online",
  "is_online": true,
  "is_sovereign": false,
  "active_bundle": null,
  "available_bundles": 2,
  "validated_bundles": 1,
  "quarantined_bundles": 0,
  "network_blocks_count": 0,
  "config": {
    "current_mode": "online",
    "auto_detect_network": true,
    "strict_validation": true
  }
}
```

### 2. Create an Offline Bundle

**Directory Structure:**
```
storage/models/bundles/
└── llama-3.2-7b/
    ├── manifest.json
    └── model.gguf
```

**manifest.json:**
```json
{
  "id": "llama-3.2-7b-v1.0",
  "name": "Llama 3.2 7B",
  "version": "1.0.0",
  "model_type": "llama",
  "model_size": "7B",
  "model_file": "model.gguf",
  "sha256_hash": "abc123...",
  "sha256_manifest_hash": "",
  "description": "Offline Llama 3.2 7B model",
  "capabilities": ["chat", "completion", "reasoning"],
  "requirements": {
    "ram_gb": 16,
    "disk_gb": 8
  }
}
```

### 3. Discover Bundles

```bash
curl -X POST http://localhost:8000/api/sovereign-mode/bundles/discover
```

**Response:**
```json
{
  "discovered": 2,
  "bundles": ["llama-3.2-7b-v1.0", "mistral-7b-v1.0"]
}
```

### 4. Validate Bundle

```bash
curl -X POST "http://localhost:8000/api/sovereign-mode/bundles/llama-3.2-7b-v1.0/validate?force=true"
```

**Response:**
```json
{
  "is_valid": true,
  "bundle_id": "llama-3.2-7b-v1.0",
  "hash_match": true,
  "expected_hash": "abc123...",
  "actual_hash": "abc123...",
  "file_exists": true,
  "manifest_valid": true,
  "errors": [],
  "warnings": []
}
```

### 5. Switch to Sovereign Mode

```bash
curl -X POST http://localhost:8000/api/sovereign-mode/mode \
  -H "Content-Type: application/json" \
  -d '{
    "target_mode": "sovereign",
    "bundle_id": "llama-3.2-7b-v1.0",
    "reason": "Entering secure offline operation"
  }'
```

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sovereign-mode/info` | System information |
| GET | `/api/sovereign-mode/status` | Current status |
| POST | `/api/sovereign-mode/mode` | Change operation mode |
| GET | `/api/sovereign-mode/bundles` | List bundles |
| GET | `/api/sovereign-mode/bundles/{id}` | Get bundle details |
| POST | `/api/sovereign-mode/bundles/load` | Load bundle |
| POST | `/api/sovereign-mode/bundles/{id}/validate` | Validate bundle |
| POST | `/api/sovereign-mode/bundles/discover` | Discover bundles |
| GET | `/api/sovereign-mode/network/check` | Check connectivity |
| GET | `/api/sovereign-mode/config` | Get configuration |
| PUT | `/api/sovereign-mode/config` | Update configuration |
| GET | `/api/sovereign-mode/audit` | Get audit log |
| GET | `/api/sovereign-mode/statistics` | Get statistics |

### Detailed Examples

#### Change Mode with Bundle

```bash
curl -X POST http://localhost:8000/api/sovereign-mode/mode \
  -H "Content-Type: application/json" \
  -d '{
    "target_mode": "sovereign",
    "force": false,
    "reason": "Manual activation",
    "bundle_id": "llama-3.2-7b-v1.0"
  }'
```

#### Load Bundle

```bash
curl -X POST http://localhost:8000/api/sovereign-mode/bundles/load \
  -H "Content-Type: application/json" \
  -d '{
    "bundle_id": "llama-3.2-7b-v1.0",
    "force_revalidate": true,
    "skip_quarantine_check": false
  }'
```

#### Update Configuration

```bash
curl -X PUT http://localhost:8000/api/sovereign-mode/config \
  -H "Content-Type: application/json" \
  -d '{
    "auto_detect_network": true,
    "network_check_interval": 60,
    "strict_validation": true,
    "block_external_http": true,
    "allowed_domains": ["localhost", "127.0.0.1"],
    "quarantine_on_failure": true,
    "audit_mode_changes": true
  }'
```

#### Get Audit Log

```bash
curl "http://localhost:8000/api/sovereign-mode/audit?limit=50&event_type=mode_change"
```

## Configuration

### ModeConfig Schema

```python
{
    "current_mode": "online",              # Current operation mode
    "active_bundle_id": null,              # Active bundle ID

    # Auto-detection
    "auto_detect_network": true,           # Auto-switch on network loss
    "network_check_interval": 30,          # Seconds between checks
    "network_check_enabled": true,         # Enable monitoring

    # Security
    "strict_validation": true,             # Enforce strict hash validation
    "allow_unsigned_bundles": false,       # Allow unsigned bundles
    "quarantine_on_failure": true,         # Auto-quarantine failed bundles

    # Network guards
    "block_external_http": true,           # Block HTTP in offline mode
    "block_external_dns": true,            # Block DNS in offline mode
    "allowed_domains": [],                 # Whitelisted domains

    # Fallback
    "fallback_to_offline": true,           # Fallback on network loss
    "fallback_bundle_id": null,            # Default offline bundle

    # Audit
    "audit_mode_changes": true,            # Log mode changes
    "audit_bundle_loads": true,            # Log bundle operations
    "audit_network_blocks": true           # Log blocked requests
}
```

## Bundle Manifest Specification

### Offline Model Bundle Standard v1.0

```json
{
  "id": "unique-bundle-id",
  "name": "Human Readable Name",
  "version": "1.0.0",
  "model_type": "llama|mistral|gpt|custom",
  "model_size": "7B|13B|70B|custom",
  "model_file": "model.gguf",

  "sha256_hash": "SHA256 hash of model file (required)",
  "sha256_manifest_hash": "SHA256 hash of this manifest (auto-computed)",
  "signed_by": "Optional digital signature (future)",

  "description": "Optional description",
  "capabilities": ["chat", "completion", "reasoning"],
  "requirements": {
    "ram_gb": 16,
    "disk_gb": 8,
    "gpu_vram_gb": 0,
    "min_cpu_cores": 4
  },

  "created_at": "2025-12-23T12:00:00Z",
  "metadata": {}
}
```

### Creating a Bundle

1. **Place model file** in `storage/models/bundles/bundle-name/`
2. **Compute SHA256 hash:**
   ```bash
   sha256sum model.gguf
   ```
3. **Create manifest.json** with the hash
4. **Discover bundle:**
   ```bash
   curl -X POST http://localhost:8000/api/sovereign-mode/bundles/discover
   ```
5. **Validate bundle:**
   ```bash
   curl -X POST http://localhost:8000/api/sovereign-mode/bundles/{id}/validate?force=true
   ```

## Security Features

### Fail-Closed Design

The system defaults to **blocking** all external access in offline modes. This ensures:
- No accidental data exfiltration
- No external API calls
- No DNS leaks
- No network fingerprinting

### Hash Validation

All bundles must pass SHA256 validation:
- Model file hash
- Manifest file hash
- Both must match expected values

Failed validation → **Automatic quarantine**

### Quarantine Mechanism

Bundles are quarantined if:
- Hash validation fails
- File corruption detected
- Load errors occur
- Manual quarantine requested

Quarantined bundles:
- Cannot be loaded
- Require manual review
- Logged in audit trail

### Network Guards

HTTP requests are intercepted in offline modes:
- Localhost always allowed
- Whitelisted domains configurable
- Blocked requests logged
- Callbacks for security events

### Audit Logging

All operations are logged:
- Mode changes
- Bundle loads
- Validation results
- Network blocks
- Configuration updates

Logs are:
- Immutable (append-only)
- Timestamped
- Structured (JSON)
- Searchable

## Integration with Existing Systems

### Policy Engine Integration

Create policy rules for sovereign mode:

```json
{
  "id": "sovereign-mode-external-api-block",
  "name": "Block External APIs in Sovereign Mode",
  "effect": "deny",
  "priority": 200,
  "conditions": {
    "action": {"==": "external_api_call"},
    "environment.sovereign_mode": {"==": "sovereign"}
  },
  "enabled": true
}
```

### Foundation Layer Integration

Safety checks for mode switching:

```python
from backend.app.modules.foundation.service import get_foundation_service

foundation = get_foundation_service()

# Check if mode switch is safe
result = await foundation.safety_check({
    "action": "switch_sovereign_mode",
    "parameters": {
        "target_mode": "sovereign",
        "bundle_id": "llama-3.2-7b-v1.0"
    }
})
```

### Threats Module Integration

Log security violations:

```python
from backend.app.modules.threats.service import get_threats_service

threats = get_threats_service()

# Create threat for blocked request
await threats.create_threat({
    "type": "network_violation",
    "severity": "high",
    "description": "External API call blocked in sovereign mode",
    "metadata": {
        "url": "https://external-api.com",
        "mode": "sovereign"
    }
})
```

## Testing

### Unit Tests

```bash
pytest backend/tests/test_sovereign_mode.py -v
```

### Integration Tests

```bash
# Test mode switching
curl -X POST http://localhost:8000/api/sovereign-mode/mode \
  -d '{"target_mode": "sovereign", "bundle_id": "test-bundle"}'

# Test network blocking
curl -X GET http://localhost:8000/api/sovereign-mode/network/check
```

### Security Tests

```bash
# Attempt external request in sovereign mode (should fail)
# Attempt to load invalid bundle (should quarantine)
# Attempt to modify quarantined bundle (should deny)
```

## Monitoring

### Health Checks

```bash
curl http://localhost:8000/api/sovereign-mode/status
curl http://localhost:8000/api/sovereign-mode/statistics
```

### Key Metrics

- `current_mode`: Current operation mode
- `validated_bundles`: Count of validated bundles
- `quarantined_bundles`: Count of quarantined bundles
- `network_blocks_count`: Total blocked requests
- `audit_entries`: Total audit log entries

### Alerts

Set up alerts for:
- Quarantined bundles
- Failed validations
- Blocked requests (spikes)
- Mode changes (unexpected)

## Troubleshooting

### Bundle Not Loading

**Problem:** Bundle validation fails

**Solution:**
1. Check hash matches: `sha256sum model.gguf`
2. Verify manifest.json syntax
3. Check file permissions
4. Force revalidation: `?force=true`

### Network Blocks in Online Mode

**Problem:** Requests blocked while in online mode

**Solution:**
1. Check current mode: GET `/status`
2. Verify mode is actually "online"
3. Check network guard config
4. Review allowed domains

### Auto-Detection Not Working

**Problem:** Network changes not detected

**Solution:**
1. Check `network_check_enabled`: true
2. Verify `network_check_interval`
3. Check monitor status in logs
4. Test manual check: GET `/network/check`

## Best Practices

1. **Always validate bundles** before loading
2. **Use strict validation** in production
3. **Enable auto-quarantine** for security
4. **Monitor audit logs** regularly
5. **Keep allowed_domains** minimal
6. **Test offline mode** before deployment
7. **Back up configurations** regularly
8. **Review quarantined bundles** promptly

## Future Enhancements

- [ ] Digital signature verification
- [ ] Bundle encryption at rest
- [ ] Automatic bundle updates
- [ ] Multi-bundle configurations
- [ ] Bundle version management
- [ ] Remote bundle distribution
- [ ] Integration with model registry
- [ ] Advanced threat detection

## Support

For issues or questions:
- Check logs: `docker compose logs backend | grep sovereign`
- Review audit log: GET `/api/sovereign-mode/audit`
- Check statistics: GET `/api/sovereign-mode/statistics`
- Report issues: GitHub Issues

## License

Part of BRAiN Framework - See main LICENSE file
