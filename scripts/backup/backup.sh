#!/bin/bash

################################################################################
# BRAiN Automated Backup Script
#
# Backs up:
# - PostgreSQL database
# - Redis data
# - Qdrant vector database
#
# Retention: 30 days (configurable)
# Compression: gzip
# Optional: AWS S3 upload
################################################################################

set -e  # Exit on error
set -u  # Error on undefined variable

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/brain}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y%m%d)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Docker container names (adjust if needed)
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-brain-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-brain-redis}"
QDRANT_CONTAINER="${QDRANT_CONTAINER:-brain-qdrant}"

# Database credentials (from environment or defaults)
POSTGRES_USER="${POSTGRES_USER:-brain}"
POSTGRES_DB="${POSTGRES_DB:-brain}"

# AWS S3 (optional)
S3_BUCKET="${S3_BUCKET:-}"
S3_PATH="${S3_PATH:-brain-backups}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_container() {
    local container=$1
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        log_error "Container ${container} is not running!"
        return 1
    fi
    return 0
}

################################################################################
# Backup Functions
################################################################################

backup_postgres() {
    log_info "Starting PostgreSQL backup..."

    local backup_file="${BACKUP_DIR}/${DATE_DIR}/postgres_${TIMESTAMP}.sql.gz"
    mkdir -p "$(dirname "${backup_file}")"

    if check_container "${POSTGRES_CONTAINER}"; then
        docker exec "${POSTGRES_CONTAINER}" \
            pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
            | gzip > "${backup_file}"

        local size=$(du -h "${backup_file}" | cut -f1)
        log_info "PostgreSQL backup completed: ${backup_file} (${size})"
        return 0
    else
        return 1
    fi
}

backup_redis() {
    log_info "Starting Redis backup..."

    local backup_file="${BACKUP_DIR}/${DATE_DIR}/redis_${TIMESTAMP}.rdb"
    mkdir -p "$(dirname "${backup_file}")"

    if check_container "${REDIS_CONTAINER}"; then
        # Trigger Redis save
        docker exec "${REDIS_CONTAINER}" redis-cli SAVE

        # Copy RDB file
        docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "${backup_file}"

        # Compress
        gzip "${backup_file}"

        local size=$(du -h "${backup_file}.gz" | cut -f1)
        log_info "Redis backup completed: ${backup_file}.gz (${size})"
        return 0
    else
        return 1
    fi
}

backup_qdrant() {
    log_info "Starting Qdrant backup..."

    local backup_file="${BACKUP_DIR}/${DATE_DIR}/qdrant_${TIMESTAMP}.tar.gz"
    mkdir -p "$(dirname "${backup_file}")"

    if check_container "${QDRANT_CONTAINER}"; then
        # Create tar archive inside container
        docker exec "${QDRANT_CONTAINER}" \
            tar czf /tmp/qdrant_backup.tar.gz /qdrant/storage

        # Copy archive out
        docker cp "${QDRANT_CONTAINER}:/tmp/qdrant_backup.tar.gz" "${backup_file}"

        # Cleanup temp file
        docker exec "${QDRANT_CONTAINER}" rm /tmp/qdrant_backup.tar.gz

        local size=$(du -h "${backup_file}" | cut -f1)
        log_info "Qdrant backup completed: ${backup_file} (${size})"
        return 0
    else
        return 1
    fi
}

upload_to_s3() {
    if [ -z "${S3_BUCKET}" ]; then
        log_info "S3 upload disabled (S3_BUCKET not set)"
        return 0
    fi

    log_info "Uploading backups to S3..."

    if command -v aws &> /dev/null; then
        aws s3 sync "${BACKUP_DIR}/${DATE_DIR}/" \
            "s3://${S3_BUCKET}/${S3_PATH}/${DATE_DIR}/" \
            --storage-class STANDARD_IA

        log_info "S3 upload completed"
    else
        log_warn "AWS CLI not installed, skipping S3 upload"
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."

    find "${BACKUP_DIR}" -type f -mtime +${RETENTION_DAYS} -delete
    find "${BACKUP_DIR}" -type d -empty -delete

    log_info "Cleanup completed"
}

generate_backup_report() {
    local report_file="${BACKUP_DIR}/${DATE_DIR}/backup_report_${TIMESTAMP}.txt"

    cat > "${report_file}" <<EOF
BRAiN Backup Report
===================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Backup Directory: ${BACKUP_DIR}/${DATE_DIR}

Files Created:
--------------
$(ls -lh "${BACKUP_DIR}/${DATE_DIR}" | tail -n +2)

Total Backup Size:
------------------
$(du -sh "${BACKUP_DIR}/${DATE_DIR}" | cut -f1)

Disk Space:
-----------
$(df -h "${BACKUP_DIR}" | tail -n 1)

EOF

    log_info "Backup report generated: ${report_file}"
}

################################################################################
# Main Execution
################################################################################

main() {
    log_info "========================================="
    log_info "BRAiN Backup Starting"
    log_info "========================================="

    # Create backup directory
    mkdir -p "${BACKUP_DIR}/${DATE_DIR}"

    # Run backups
    local failed=0

    backup_postgres || ((failed++))
    backup_redis || ((failed++))
    backup_qdrant || ((failed++))

    # Generate report
    generate_backup_report

    # Optional S3 upload
    upload_to_s3

    # Cleanup old backups
    cleanup_old_backups

    # Summary
    log_info "========================================="
    if [ $failed -eq 0 ]; then
        log_info "Backup completed successfully!"
    else
        log_warn "Backup completed with ${failed} failures"
        exit 1
    fi
    log_info "========================================="
}

# Run main function
main "$@"
