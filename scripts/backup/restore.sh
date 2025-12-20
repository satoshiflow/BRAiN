#!/bin/bash

################################################################################
# BRAiN Restore Script
#
# Restores backups for:
# - PostgreSQL database
# - Redis data
# - Qdrant vector database
#
# Usage:
#   ./restore.sh <backup_directory>
#   ./restore.sh /var/backups/brain/20251220
################################################################################

set -e  # Exit on error
set -u  # Error on undefined variable

# Configuration
BACKUP_DIR="${1:-}"

# Docker container names
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-brain-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-brain-redis}"
QDRANT_CONTAINER="${QDRANT_CONTAINER:-brain-qdrant}"

# Database credentials
POSTGRES_USER="${POSTGRES_USER:-brain}"
POSTGRES_DB="${POSTGRES_DB:-brain}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

check_backup_dir() {
    if [ -z "${BACKUP_DIR}" ]; then
        log_error "Usage: $0 <backup_directory>"
        log_error "Example: $0 /var/backups/brain/20251220"
        exit 1
    fi

    if [ ! -d "${BACKUP_DIR}" ]; then
        log_error "Backup directory does not exist: ${BACKUP_DIR}"
        exit 1
    fi
}

confirm_restore() {
    log_warn "========================================="
    log_warn "WARNING: This will overwrite current data!"
    log_warn "Backup directory: ${BACKUP_DIR}"
    log_warn "========================================="
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo

    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi
}

################################################################################
# Restore Functions
################################################################################

restore_postgres() {
    log_info "Restoring PostgreSQL..."

    # Find latest PostgreSQL backup
    local backup_file=$(find "${BACKUP_DIR}" -name "postgres_*.sql.gz" -type f | sort -r | head -n 1)

    if [ -z "${backup_file}" ]; then
        log_error "No PostgreSQL backup found in ${BACKUP_DIR}"
        return 1
    fi

    log_info "Using backup: ${backup_file}"

    # Drop existing database (if exists) and recreate
    docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
    docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -c "CREATE DATABASE ${POSTGRES_DB};"

    # Restore
    gunzip -c "${backup_file}" | docker exec -i "${POSTGRES_CONTAINER}" \
        psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

    log_info "PostgreSQL restore completed"
}

restore_redis() {
    log_info "Restoring Redis..."

    # Find latest Redis backup
    local backup_file=$(find "${BACKUP_DIR}" -name "redis_*.rdb.gz" -type f | sort -r | head -n 1)

    if [ -z "${backup_file}" ]; then
        log_error "No Redis backup found in ${BACKUP_DIR}"
        return 1
    fi

    log_info "Using backup: ${backup_file}"

    # Stop Redis
    docker exec "${REDIS_CONTAINER}" redis-cli SHUTDOWN NOSAVE || true
    sleep 2

    # Decompress and copy RDB file
    gunzip -c "${backup_file}" > /tmp/dump.rdb
    docker cp /tmp/dump.rdb "${REDIS_CONTAINER}:/data/dump.rdb"
    rm /tmp/dump.rdb

    # Start Redis
    docker start "${REDIS_CONTAINER}" || true
    sleep 2

    log_info "Redis restore completed"
}

restore_qdrant() {
    log_info "Restoring Qdrant..."

    # Find latest Qdrant backup
    local backup_file=$(find "${BACKUP_DIR}" -name "qdrant_*.tar.gz" -type f | sort -r | head -n 1)

    if [ -z "${backup_file}" ]; then
        log_error "No Qdrant backup found in ${BACKUP_DIR}"
        return 1
    fi

    log_info "Using backup: ${backup_file}"

    # Stop Qdrant
    docker stop "${QDRANT_CONTAINER}" || true
    sleep 2

    # Copy backup to container and extract
    docker cp "${backup_file}" "${QDRANT_CONTAINER}:/tmp/qdrant_backup.tar.gz"
    docker start "${QDRANT_CONTAINER}" || true
    sleep 2

    docker exec "${QDRANT_CONTAINER}" rm -rf /qdrant/storage/*
    docker exec "${QDRANT_CONTAINER}" tar xzf /tmp/qdrant_backup.tar.gz -C /
    docker exec "${QDRANT_CONTAINER}" rm /tmp/qdrant_backup.tar.gz

    # Restart Qdrant
    docker restart "${QDRANT_CONTAINER}"

    log_info "Qdrant restore completed"
}

verify_restore() {
    log_info "Verifying restore..."

    # PostgreSQL
    if docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT 1" > /dev/null 2>&1; then
        log_info "✓ PostgreSQL is responsive"
    else
        log_error "✗ PostgreSQL verification failed"
    fi

    # Redis
    if docker exec "${REDIS_CONTAINER}" redis-cli PING | grep -q "PONG"; then
        log_info "✓ Redis is responsive"
    else
        log_error "✗ Redis verification failed"
    fi

    # Qdrant
    if docker exec "${QDRANT_CONTAINER}" wget -q -O- http://localhost:6333/health | grep -q "ok"; then
        log_info "✓ Qdrant is responsive"
    else
        log_warn "✗ Qdrant verification failed (may need more startup time)"
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    log_info "========================================="
    log_info "BRAiN Restore Starting"
    log_info "========================================="

    check_backup_dir
    confirm_restore

    # List available backups
    log_info "Available backups in ${BACKUP_DIR}:"
    ls -lh "${BACKUP_DIR}"
    echo

    # Run restores
    local failed=0

    restore_postgres || ((failed++))
    restore_redis || ((failed++))
    restore_qdrant || ((failed++))

    # Verify
    verify_restore

    # Summary
    log_info "========================================="
    if [ $failed -eq 0 ]; then
        log_info "Restore completed successfully!"
        log_info "Please restart all BRAiN services to ensure clean state"
    else
        log_error "Restore completed with ${failed} failures"
        exit 1
    fi
    log_info "========================================="
}

# Run main function
main "$@"
