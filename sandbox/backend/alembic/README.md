# Alembic Database Migrations

**Status:** ✅ Configured (v0.3.0)
**Database:** PostgreSQL (async via asyncpg)

---

## Overview

Alembic manages database schema migrations for BRAiN. It uses async SQLAlchemy with PostgreSQL.

---

## Quick Start

### 1. Create a Migration

```bash
# Auto-generate migration from models
cd backend
alembic revision --autogenerate -m "add user table"

# Create empty migration (manual)
alembic revision -m "custom migration"
```

### 2. Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one step
alembic upgrade +1

# Upgrade to specific revision
alembic upgrade abc123
```

### 3. Rollback Migrations

```bash
# Downgrade one step
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123

# Rollback to initial state
alembic downgrade base
```

---

## Migration History

```bash
# Show current version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic show head
```

---

## Configuration

### Database URL

Set in `.env`:
```bash
DATABASE_URL=postgresql+asyncpg://brain:brain@localhost:5432/brain
```

Or via environment variable:
```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@host/db"
```

### Async Support

This Alembic setup is configured for **async SQLAlchemy**:
- Uses `async_engine_from_config`
- Runs migrations with `asyncio.run()`
- Compatible with `asyncpg` driver

---

## Adding Models

To enable auto-generation, import your models in `alembic/env.py`:

```python
# alembic/env.py
from app.core.db import Base
from app.modules.dna.models import DNASnapshot
from app.modules.missions.models import Mission
# ... import all models

target_metadata = Base.metadata  # Important!
```

Then run:
```bash
alembic revision --autogenerate -m "initial models"
```

---

## Migration Structure

```
backend/
├── alembic/
│   ├── versions/          # Migration files
│   │   └── 001_initial_schema.py
│   ├── env.py             # Alembic environment config
│   ├── script.py.mako     # Migration template
│   └── README.md          # This file
├── alembic.ini            # Alembic configuration
└── app/
    └── core/
        └── db.py          # SQLAlchemy Base
```

---

## Common Tasks

### Add a New Table

1. Define model in `app/modules/mymodule/models.py`:
```python
from sqlalchemy import Column, Integer, String
from app.core.db import Base

class MyModel(Base):
    __tablename__ = "my_table"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
```

2. Import in `alembic/env.py`:
```python
from app.modules.mymodule.models import MyModel
```

3. Generate migration:
```bash
alembic revision --autogenerate -m "add my_table"
```

4. Review generated migration in `alembic/versions/`

5. Apply:
```bash
alembic upgrade head
```

### Modify a Column

```python
# In migration file
def upgrade():
    op.alter_column('users', 'email',
                    existing_type=sa.String(100),
                    type_=sa.String(255))

def downgrade():
    op.alter_column('users', 'email',
                    existing_type=sa.String(255),
                    type_=sa.String(100))
```

### Add an Index

```python
def upgrade():
    op.create_index('idx_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('idx_users_email')
```

---

## Docker Usage

Migrations run automatically in Docker via Dockerfile:

```dockerfile
# Option 1: Run migrations on startup
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0"]

# Option 2: Separate migration step
RUN alembic upgrade head
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

Or manually:
```bash
docker compose exec backend alembic upgrade head
```

---

## Troubleshooting

### Error: "Can't locate revision identified by 'abc123'"

**Solution:** Check `alembic_version` table in database:
```sql
SELECT * FROM alembic_version;
```

Delete and re-run:
```sql
DELETE FROM alembic_version;
```
```bash
alembic upgrade head
```

### Error: "Target database is not up to date"

**Solution:**
```bash
alembic stamp head  # Mark current state as latest
```

### Error: "No module named 'app'"

**Solution:** Run from `backend/` directory:
```bash
cd backend
alembic upgrade head
```

---

## Best Practices

1. **Always review auto-generated migrations** - Alembic doesn't detect everything
2. **Test migrations on dev database first**
3. **Use `alembic downgrade` to test rollback**
4. **Keep migrations small and focused**
5. **Add comments explaining complex migrations**
6. **Backup production database before migrating**

---

## Production Deployment

### Pre-deployment

1. Test migrations on staging:
```bash
alembic upgrade head
```

2. Create database backup:
```bash
pg_dump brain > backup_$(date +%Y%m%d).sql
```

### Deployment

1. Put app in maintenance mode
2. Run migrations:
```bash
alembic upgrade head
```
3. Restart application
4. Verify database state

### Rollback

If deployment fails:
```bash
alembic downgrade -1  # Rollback one migration
# or
psql brain < backup_20241219.sql  # Restore from backup
```

---

## Future Enhancements

- [ ] Add migration testing in CI/CD
- [ ] Automated backup before migrations
- [ ] Migration dry-run mode
- [ ] Schema validation after migrations

---

## Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Version:** 0.3.0
**Last Updated:** 2024-12-19
