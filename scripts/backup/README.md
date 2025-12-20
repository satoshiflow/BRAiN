# BRAiN Backup & Restore Guide

Automated backup and restore scripts for BRAiN Core databases.

## Features

- **Automated Backups:** PostgreSQL, Redis, and Qdrant
- **Compression:** gzip for all backups
- **Retention:** Automatic cleanup of old backups (30 days default)
- **S3 Upload:** Optional AWS S3 storage
- **Restore:** Complete system restore from backups

---

## Quick Start

### Manual Backup

```bash
# Run backup manually
./scripts/backup/backup.sh

# With custom backup directory
BACKUP_DIR=/custom/path ./scripts/backup/backup.sh

# With S3 upload
S3_BUCKET=my-bucket ./scripts/backup/backup.sh
```

### Restore from Backup

```bash
# Restore from specific backup
./scripts/backup/restore.sh /var/backups/brain/20251220

# Interactive confirmation required
# WARNING: This will overwrite current data!
```

---

## Automated Backups

### Cron Setup

Add to crontab for daily backups at 2 AM:

```bash
crontab -e

# Add this line:
0 2 * * * /home/user/BRAiN/scripts/backup/backup.sh >> /var/log/brain-backup.log 2>&1
```

### Docker Compose Service

Use the included docker-compose backup service:

```yaml
# docker-compose.prod.yml
backup:
  image: offen/docker-volume-backup:latest
  environment:
    BACKUP_CRON_EXPRESSION: "0 2 * * *"  # Daily at 2 AM
    BACKUP_RETENTION_DAYS: "30"
    BACKUP_FILENAME: "brain-backup-%Y%m%d-%H%M%S.tar.gz"
  volumes:
    - brain_pg_data:/backup/postgres:ro
    - brain_redis_data:/backup/redis:ro
    - brain_qdrant_data:/backup/qdrant:ro
    - ./backups:/archive
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKUP_DIR` | `/var/backups/brain` | Backup storage directory |
| `RETENTION_DAYS` | `30` | Days to keep backups |
| `S3_BUCKET` | - | AWS S3 bucket name (optional) |
| `S3_PATH` | `brain-backups` | S3 path prefix |
| `POSTGRES_CONTAINER` | `brain-postgres` | PostgreSQL container name |
| `REDIS_CONTAINER` | `brain-redis` | Redis container name |
| `QDRANT_CONTAINER` | `brain-qdrant` | Qdrant container name |
| `POSTGRES_USER` | `brain` | PostgreSQL username |
| `POSTGRES_DB` | `brain` | PostgreSQL database name |

### Example Custom Configuration

```bash
# Custom backup location and retention
BACKUP_DIR=/mnt/nas/brain-backups \
RETENTION_DAYS=90 \
./scripts/backup/backup.sh

# With S3 upload
S3_BUCKET=my-backup-bucket \
S3_PATH=production/brain \
AWS_PROFILE=production \
./scripts/backup/backup.sh
```

---

## Backup Structure

```
/var/backups/brain/
├── 20251220/
│   ├── postgres_20251220_020000.sql.gz
│   ├── redis_20251220_020000.rdb.gz
│   ├── qdrant_20251220_020000.tar.gz
│   └── backup_report_20251220_020000.txt
├── 20251221/
│   └── ...
└── ...
```

---

## Restore Procedures

### Full System Restore

1. **Stop BRAiN services:**
   ```bash
   docker compose down
   ```

2. **Run restore script:**
   ```bash
   ./scripts/backup/restore.sh /var/backups/brain/20251220
   ```

3. **Verify restore:**
   - Check logs for errors
   - Verify data integrity

4. **Restart services:**
   ```bash
   docker compose up -d
   ```

### Individual Component Restore

**PostgreSQL only:**
```bash
gunzip -c /var/backups/brain/20251220/postgres_*.sql.gz | \
  docker exec -i brain-postgres psql -U brain -d brain
```

**Redis only:**
```bash
gunzip -c /var/backups/brain/20251220/redis_*.rdb.gz > /tmp/dump.rdb
docker cp /tmp/dump.rdb brain-redis:/data/dump.rdb
docker restart brain-redis
```

**Qdrant only:**
```bash
docker cp /var/backups/brain/20251220/qdrant_*.tar.gz brain-qdrant:/tmp/backup.tar.gz
docker exec brain-qdrant tar xzf /tmp/backup.tar.gz -C /
docker restart brain-qdrant
```

---

## S3 Integration

### Setup AWS CLI

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region: us-east-1

# Test connection
aws s3 ls s3://your-bucket/
```

### S3 Lifecycle Policy

Configure S3 to automatically transition old backups to cheaper storage:

```json
{
  "Rules": [
    {
      "Id": "TransitionOldBackups",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

---

## Monitoring & Alerts

### Check Backup Status

```bash
# View latest backup report
cat /var/backups/brain/$(ls -t /var/backups/brain/ | head -1)/backup_report_*.txt

# Check backup sizes
du -sh /var/backups/brain/*/

# List all backups
find /var/backups/brain/ -name "*.gz" -type f -exec ls -lh {} \;
```

### Email Notifications

Add email notification to cron:

```bash
# In crontab
MAILTO=admin@example.com
0 2 * * * /home/user/BRAiN/scripts/backup/backup.sh
```

### Slack Notifications

Add to backup.sh:

```bash
# At end of main() function
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"BRAiN backup completed successfully"}' \
  https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

## Troubleshooting

### Backup Fails

```bash
# Check container status
docker ps | grep brain

# Check disk space
df -h /var/backups/brain

# Check permissions
ls -la /var/backups/brain

# View detailed logs
./scripts/backup/backup.sh 2>&1 | tee backup.log
```

### Restore Fails

```bash
# Verify backup integrity
gunzip -t /var/backups/brain/20251220/postgres_*.sql.gz

# Check container logs
docker logs brain-postgres
docker logs brain-redis
docker logs brain-qdrant

# Manual restore attempt
# See "Individual Component Restore" section
```

---

## Best Practices

1. **Test Restores Regularly**
   - Monthly restore test to staging environment
   - Verify data integrity after restore

2. **Monitor Backup Size**
   - Track backup size trends
   - Alert on sudden size changes

3. **Secure Backups**
   - Encrypt backups for sensitive data
   - Restrict access to backup directory
   - Use S3 encryption at rest

4. **Multiple Backup Locations**
   - Local backups for fast restore
   - S3 for offsite disaster recovery
   - Consider separate region backups

5. **Document Recovery Time Objective (RTO)**
   - Test and measure restore time
   - Plan for acceptable downtime

---

## Security

### Encrypt Backups

```bash
# Encrypt backup
gpg --symmetric --cipher-algo AES256 backup.sql.gz

# Decrypt backup
gpg --decrypt backup.sql.gz.gpg > backup.sql.gz
```

### Secure Backup Directory

```bash
chmod 700 /var/backups/brain
chown root:root /var/backups/brain
```

---

## Support

For issues or questions:
- Check logs in `/var/log/brain-backup.log`
- Review backup reports in backup directory
- Contact: admin@brain.falklabs.de
