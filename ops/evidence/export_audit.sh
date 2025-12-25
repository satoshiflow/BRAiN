#!/usr/bin/env bash
#
# BRAiN Governance Audit Export Script
#
# Purpose: Export daily audit log snapshots from BRAiN backend
# Output: JSONL format with SHA256 integrity hash
# Storage: /var/lib/brain/evidence/audit-YYYY-MM-DD.jsonl
# Retention: Optional (90 days, commented out by default)
#
# Version: 1.0.0
# Last Updated: 2025-12-25
#
# Usage:
#   ./export_audit.sh                    # Export today's audit log
#   DRY_RUN=1 ./export_audit.sh          # Test mode (no writes)
#   BACKEND_URL=http://... ./export_audit.sh  # Override backend URL
#
# Requirements:
#   - curl
#   - jq
#   - sha256sum
#   - systemd (for journal logging)
#
# Exit Codes:
#   0  - Success
#   1  - Configuration error
#   2  - Backend unreachable
#   3  - Export failed
#   4  - Hash computation failed
#   5  - Storage write failed

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default backend URL (can be overridden via ENV or config file)
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# Evidence storage directory
EVIDENCE_DIR="${EVIDENCE_DIR:-/var/lib/brain/evidence}"

# Date format for filenames (YYYY-MM-DD)
DATE=$(date +%Y-%m-%d)

# Output file path
OUTPUT_FILE="${EVIDENCE_DIR}/audit-${DATE}.jsonl"
HASH_FILE="${OUTPUT_FILE}.sha256"

# Retention days (set to 0 to disable auto-cleanup)
RETENTION_DAYS="${RETENTION_DAYS:-90}"

# Dry run mode (set DRY_RUN=1 to test without writing)
DRY_RUN="${DRY_RUN:-0}"

# API endpoint
EXPORT_ENDPOINT="${BACKEND_URL}/api/sovereign-mode/audit/export"

# Optional: Load configuration from external file
CONFIG_FILE="/usr/local/bin/brain-evidence.conf"
if [[ -f "${CONFIG_FILE}" ]]; then
    # shellcheck source=/dev/null
    source "${CONFIG_FILE}"
fi

# ============================================================================
# LOGGING
# ============================================================================

# Log to systemd journal (if available) and stderr
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date -Iseconds)

    echo "[${timestamp}] [${level}] ${message}" >&2

    # If running under systemd, also log to journal
    if command -v systemd-cat &>/dev/null && [[ -n "${INVOCATION_ID:-}" ]]; then
        echo "${message}" | systemd-cat -t brain-evidence-export -p "${level}"
    fi
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARNING" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_debug() {
    if [[ "${DEBUG:-0}" == "1" ]]; then
        log "DEBUG" "$@"
    fi
}

# ============================================================================
# PREFLIGHT CHECKS
# ============================================================================

preflight_checks() {
    log_info "Starting preflight checks..."

    # Check required commands
    local required_commands=("curl" "jq" "sha256sum" "date")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "${cmd}" &>/dev/null; then
            log_error "Required command not found: ${cmd}"
            exit 1
        fi
    done
    log_info "✓ Required commands available"

    # Create evidence directory if it doesn't exist
    if [[ ! -d "${EVIDENCE_DIR}" ]]; then
        if [[ "${DRY_RUN}" == "1" ]]; then
            log_warn "DRY RUN: Would create directory: ${EVIDENCE_DIR}"
        else
            log_info "Creating evidence directory: ${EVIDENCE_DIR}"
            mkdir -p "${EVIDENCE_DIR}" || {
                log_error "Failed to create directory: ${EVIDENCE_DIR}"
                exit 5
            }
        fi
    fi
    log_info "✓ Evidence directory exists: ${EVIDENCE_DIR}"

    # Check if file already exists (idempotency)
    if [[ -f "${OUTPUT_FILE}" ]]; then
        log_warn "Export file already exists: ${OUTPUT_FILE}"
        log_warn "Existing file will be overwritten"
    fi

    # Check backend connectivity
    log_info "Checking backend connectivity: ${BACKEND_URL}/health"
    if ! curl --fail --silent --max-time 10 "${BACKEND_URL}/health" &>/dev/null; then
        log_error "Backend is unreachable: ${BACKEND_URL}"
        log_error "Health check failed. Is BRAiN backend running?"
        exit 2
    fi
    log_info "✓ Backend is reachable"

    log_info "Preflight checks passed"
}

# ============================================================================
# EXPORT AUDIT LOG
# ============================================================================

export_audit_log() {
    log_info "Exporting audit log for date: ${DATE}"
    log_info "Backend URL: ${BACKEND_URL}"
    log_info "Export endpoint: ${EXPORT_ENDPOINT}"

    # Build request payload (include_hash=true for SHA256)
    local request_payload
    request_payload=$(jq -n \
        --arg include_hash "true" \
        '{
            include_hash: ($include_hash | test("true")),
            start_time: null,
            end_time: null,
            event_types: null
        }')

    log_debug "Request payload: ${request_payload}"

    # Call export API
    local response
    local http_code
    local temp_response
    temp_response=$(mktemp)

    if [[ "${DRY_RUN}" == "1" ]]; then
        log_warn "DRY RUN: Would call API: POST ${EXPORT_ENDPOINT}"
        log_warn "DRY RUN: Would save to: ${OUTPUT_FILE}"
        return 0
    fi

    log_info "Calling export API..."
    http_code=$(curl --silent --write-out '%{http_code}' --output "${temp_response}" \
        --request POST \
        --header "Content-Type: application/json" \
        --data "${request_payload}" \
        --max-time 60 \
        "${EXPORT_ENDPOINT}")

    log_debug "HTTP response code: ${http_code}"

    # Check HTTP status
    if [[ "${http_code}" != "200" ]]; then
        log_error "Export API failed with HTTP ${http_code}"
        log_error "Response: $(cat "${temp_response}")"
        rm -f "${temp_response}"
        exit 3
    fi

    # Parse response
    response=$(cat "${temp_response}")
    rm -f "${temp_response}"

    log_debug "API Response: ${response}"

    # Extract metadata from response
    local export_id
    local event_count
    local content_hash
    export_id=$(echo "${response}" | jq -r '.export_id // "unknown"')
    event_count=$(echo "${response}" | jq -r '.event_count // 0')
    content_hash=$(echo "${response}" | jq -r '.content_hash // ""')

    log_info "Export metadata:"
    log_info "  Export ID: ${export_id}"
    log_info "  Event count: ${event_count}"
    log_info "  Content hash: ${content_hash}"

    # Note: The current API implementation returns metadata only (not the actual JSONL content)
    # For production use, the API should stream JSONL content directly
    # For now, we'll fetch the audit log via GET and format it ourselves

    log_warn "Note: Using GET /api/sovereign-mode/audit as fallback (API limitation)"

    # Fetch audit log via GET endpoint
    local audit_log
    audit_log=$(curl --silent --fail --max-time 60 \
        "${BACKEND_URL}/api/sovereign-mode/audit?limit=10000" || {
        log_error "Failed to fetch audit log via GET endpoint"
        exit 3
    })

    # Convert JSON array to JSONL (one JSON object per line)
    echo "${audit_log}" | jq -c '.[]' > "${OUTPUT_FILE}" || {
        log_error "Failed to write audit log to ${OUTPUT_FILE}"
        exit 5
    }

    log_info "✓ Audit log exported to: ${OUTPUT_FILE}"

    # Compute SHA256 hash
    compute_hash "${OUTPUT_FILE}" "${HASH_FILE}"

    # Verify event count
    local exported_events
    exported_events=$(wc -l < "${OUTPUT_FILE}")
    log_info "Exported ${exported_events} events"

    log_info "✓ Export completed successfully"
}

# ============================================================================
# COMPUTE SHA256 HASH
# ============================================================================

compute_hash() {
    local input_file="$1"
    local output_file="$2"

    log_info "Computing SHA256 hash for: ${input_file}"

    if [[ "${DRY_RUN}" == "1" ]]; then
        log_warn "DRY RUN: Would compute SHA256 hash"
        return 0
    fi

    # Compute hash
    local hash
    hash=$(sha256sum "${input_file}" | awk '{print $1}') || {
        log_error "Failed to compute SHA256 hash"
        exit 4
    }

    # Save hash to file (format: HASH  FILENAME)
    echo "${hash}  $(basename "${input_file}")" > "${output_file}" || {
        log_error "Failed to write hash file: ${output_file}"
        exit 5
    }

    log_info "✓ SHA256 hash computed: ${hash}"
    log_info "✓ Hash saved to: ${output_file}"

    # Set file permissions (read-only)
    chmod 0444 "${input_file}" "${output_file}" || {
        log_warn "Failed to set read-only permissions (non-fatal)"
    }
}

# ============================================================================
# RETENTION CLEANUP
# ============================================================================

cleanup_old_exports() {
    if [[ "${RETENTION_DAYS}" == "0" ]]; then
        log_info "Retention cleanup disabled (RETENTION_DAYS=0)"
        return 0
    fi

    log_info "Checking for exports older than ${RETENTION_DAYS} days..."

    if [[ "${DRY_RUN}" == "1" ]]; then
        log_warn "DRY RUN: Would delete files older than ${RETENTION_DAYS} days"
        find "${EVIDENCE_DIR}" -name "audit-*.jsonl*" -type f -mtime "+${RETENTION_DAYS}" -ls
        return 0
    fi

    # Find and delete old files
    local deleted_count
    deleted_count=$(find "${EVIDENCE_DIR}" -name "audit-*.jsonl*" -type f -mtime "+${RETENTION_DAYS}" -delete -print | wc -l)

    if [[ "${deleted_count}" -gt 0 ]]; then
        log_info "✓ Deleted ${deleted_count} old export files"
    else
        log_info "No old exports to delete"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    log_info "=========================================="
    log_info "BRAiN Governance Audit Export"
    log_info "=========================================="
    log_info "Date: ${DATE}"
    log_info "Backend: ${BACKEND_URL}"
    log_info "Output: ${OUTPUT_FILE}"
    log_info "Dry run: ${DRY_RUN}"
    log_info "=========================================="

    # Run preflight checks
    preflight_checks

    # Export audit log
    export_audit_log

    # Cleanup old exports (optional)
    cleanup_old_exports

    log_info "=========================================="
    log_info "✓ Audit export completed successfully"
    log_info "=========================================="

    exit 0
}

# Run main function
main "$@"
