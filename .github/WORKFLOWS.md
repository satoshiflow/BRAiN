# GitHub Workflows

Automatisierte CI/CD Pipelines für BRAiN-Projekt. Diese Dokumentation erklärt die verschiedenen Workflows und deren Zweck.

## 📋 Workflow-Übersicht

### 1. **frontend-ci.yml** - Frontend Continuous Integration
**Trigger:** Push/PR auf `frontend/**` Dateien

**Jobs:**
- `lint-control-deck` - ESLint + TypeScript type-checking für Control Deck
- `lint-axe-ui` - ESLint + TypeScript type-checking für Axe UI
- `build-control-deck` - Next.js Build, Artifact Upload
- `build-axe-ui` - Next.js Build, Artifact Upload

**Features:**
- NPM Dependency Caching für schnelle Builds
- Path-based filtering (nur wenn Frontend sich ändert)
- Type-checking mit TypeScript Compiler
- Build Artifacts für später Nutzung

---

### 2. **backend-ci.yml** - Backend Continuous Integration
**Trigger:** Push/PR auf `backend/**` Dateien

**Jobs:**
- `lint` - Ruff + Pylint für Code Quality
- `type-check` - MyPy für Type Safety
- `test` - Pytest mit PostgreSQL + Redis Services
  - Coverage Report zu Codecov
  - PostgreSQL pgvector Support
  - Redis für Cache Tests

**Features:**
- Service Containers (PostgreSQL, Redis)
- Coverage Reporting
- Python 3.11 Standard
- Pip Dependency Caching

---

### 3. **lint-test.yml** - Quick Validation (Alle)
**Trigger:** Push/PR auf `main`, `v2`, `develop`

**Jobs:**
- `backend-lint-test` - Backend Ruff + Mypy + Tests (mit Coverage)
- `frontend-lint` - Frontend ESLint + Type-Check (Matrix: beide Apps)
- `security-scan` - Trivy Vulnerability Scanning (alle Files)
- `health-check` - Docker Compose Validierung + Critical Files Check

**Features:**
- Schnelle Feedback für Pull Requests
- Security Vulnerability Scanning (SARIF Upload)
- File Integrity Checks
- Docker Compose Syntax Validation

---

### 4. **build.yml** - Docker Image Build & Push
**Trigger:** Push auf `backend/**`, `frontend/**`, `nginx/**` oder `docker-compose.yml`

**Jobs** (parallel):
- `build-backend` - Backend Docker Build
- `build-control-deck` - Control Deck Docker Build
- `build-axe-ui` - Axe UI Docker Build
- `build-nginx` - Nginx Reverse Proxy Build

**Features:**
- Multi-stage Docker Builds
- GitHub Actions Cache für Layer Caching
- Push zu `ghcr.io` (GitHub Container Registry)
- Semantic Tags:
  - `branch-name` (z.B. `v2`, `main`)
  - `sha` (Git Commit SHA)
  - `latest` (für Default Branch)
  - Semver Tags bei Releases

**Push nur bei:**
- Push zu `main`, `v2`, `develop`
- Workflow Dispatch (manuell)
- NICHT bei Pull Requests (nur Build ohne Push)

---

### 5. **deploy.yml** - Deployment Pipeline
**Trigger:** 
- Push zu `main` Branch
- Workflow Dispatch (manuell)
- Nach erfolgreichem `build.yml` Workflow

**Jobs:**
1. `pre-deploy-tests` - Integration + Smoke Tests
2. `deploy-staging` - Deploy zu Staging Environment
   - Health Checks
   - GitHub Comment Notification
3. `deploy-production` - Deploy zu Production
   - Deployment Status Tracking
   - Smoke Tests nach Deploy
4. `rollback` - Auto-Rollback bei Failure

**Features:**
- Environment-basierte Deployments
- Pre-deployment Testing
- Health Checks
- GitHub Deployment API Integration
- Automatic Rollback
- Deployment Status Updates

**Deployment Optionen:**
```bash
# Docker Compose (Self-hosted)
docker-compose up -d

# Kubernetes
kubectl apply -f k8s/staging/
kubectl apply -f k8s/production/

# Cloud (AWS ECS, Google Cloud Run, etc.)
# - Anpassbar je nach Platform
```

---

### 6. **release.yml** - Release Management
**Trigger:** 
- Git Tag Push (`v*.*.*`)
- Workflow Dispatch mit Manual Version Input

**Jobs:**
1. `validate-release` - Validiere Version Format & CHANGELOG
2. `build-release` - Docker Build mit Version Tags
3. `create-github-release` - GitHub Release mit Changelog
4. `notify-release` - Release Notification

**Features:**
- Semantic Version Validation (v2.0.0)
- CHANGELOG.md Verification
- Docker Images mit Version Tags zu ghcr.io
- Automatische GitHub Release Erstellung
- OCI Image Labels (version, revision)

**Release Flow:**
```bash
# 1. Tag mit Version erstellen
git tag v2.0.0

# 2. Push Tag
git push origin v2.0.0

# 3. Automatisch:
#    - Images built: backend:2.0.0, control-deck:2.0.0, etc.
#    - GitHub Release created
#    - Latest Tags updated
```

---

## 🔧 Environment Setup

### Erforderlich für Workflows:

#### 1. GitHub Secrets
```
GITHUB_TOKEN - Automatisch bereitgestellt (keine Konfiguration nötig)
```

#### 2. Optional Secrets (für erweiterte Features)
```
# Codecov Integration
CODECOV_TOKEN

# Deployment Credentials
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
KUBERNETES_CONFIG  # Base64 encoded kubeconfig

# Slack/Discord Notifications
SLACK_WEBHOOK_URL
DISCORD_WEBHOOK_URL
```

#### 3. Environment Konfiguration (Settings > Environments)
```
staging:
  - Auto-deployment: main branch
  - Protection Rules: Require review

production:
  - Auto-deployment: main branch (nach staging approval)
  - Protection Rules: Require review + admins
  - Wait Timer: 1-12 hours (optional)
```

---

## 📊 Workflow Triggers & Dependencies

```
┌─ PUSH to feature branch
│
├─→ frontend-ci.yml (if frontend/* changed)
├─→ backend-ci.yml (if backend/* changed)
│
└─ PUSH to main/v2/develop
   │
   ├─→ lint-test.yml (Always runs)
   ├─→ build.yml (Docker builds)
   │   │
   │   └─→ deploy.yml (if push to main)
   │       ├─→ deploy-staging
   │       ├─→ deploy-production
   │       └─→ rollback (on failure)
   │
   └─ PUSH new TAG (v*.*.*)
       │
       └─→ release.yml
           ├─→ validate-release
           ├─→ build-release
           ├─→ create-github-release
           └─→ notify-release
```

---

## 🚀 Verwendungsbeispiele

### Pull Request Workflow
```bash
# 1. Feature Branch erstellen
git checkout -b feature/my-feature

# 2. Code ändern (z.B. Backend)
# vim backend/app/main.py

# 3. Push
git push origin feature/my-feature

# 4. GitHub Actions läuft automatisch:
#    - backend-ci.yml: Tests, Lint, Type-Check
#    - lint-test.yml: Schnelle Validierung
```

### Frontend-Only Change
```bash
git checkout -b ui/button-colors
# vim frontend/control_deck/app/page.tsx
git push origin ui/button-colors

# Nur frontend-ci.yml wird ausgelöst (nicht backend-ci.yml)
```

### Release Process
```bash
# 1. CHANGELOG.md aktualisieren
vim CHANGELOG.md
# ## [2.0.0] - 2025-12-11
# ### Added
# - Feature X
# - Feature Y

# 2. Commit & Tag
git add CHANGELOG.md
git commit -m "bump: Version 2.0.0"
git tag v2.0.0
git push origin v2.0.0

# 3. release.yml läuft:
#    - Validiert Version Format
#    - Buildet Docker Images: 2.0.0 + latest
#    - Erstellt GitHub Release mit Changelog
#    - Updated ghcr.io Container Registry
```

### Manual Deploy
```bash
# GitHub UI: Actions > Deploy > Run workflow > main
# Oder CLI:
gh workflow run deploy.yml --ref main
```

---

## 🔍 Status Checks & Badges

### Badge für README.md
```markdown
![Frontend CI](https://github.com/satoshiflow/BRAiN/workflows/Frontend%20CI/badge.svg)
![Backend CI](https://github.com/satoshiflow/BRAiN/workflows/Backend%20CI/badge.svg)
![Build](https://github.com/satoshiflow/BRAiN/workflows/Build%20Docker%20Images/badge.svg)
![Deploy](https://github.com/satoshiflow/BRAiN/workflows/Deploy/badge.svg)
![Lint & Test](https://github.com/satoshiflow/BRAiN/workflows/Lint%20%26%20Test/badge.svg)
```

### Status Check Konfiguration (Branch Protection)
Settings > Branches > Branch Protection Rules
```
Required status checks:
  ✓ frontend-ci (wenn Frontend geändert)
  ✓ backend-ci (wenn Backend geändert)
  ✓ lint-test (immer)
```

---

## 🛠️ Häufige Anpassungen

### Docker Registry wechseln (z.B. Docker Hub)
Ändere in `build.yml` und `release.yml`:
```yaml
REGISTRY: docker.io
IMAGE_NAME: myusername/brain
```

### Zusätzliche Python Linter hinzufügen
In `backend-ci.yml`:
```yaml
- name: Lint with Flake8
  run: |
    pip install flake8
    flake8 backend/app
```

### Coverage Threshold
In `backend-ci.yml`:
```yaml
- name: Check coverage
  run: |
    pytest tests/ --cov=app --cov-fail-under=80
```

### Deployment zu Kubernetes
In `deploy.yml`:
```yaml
- name: Deploy to Kubernetes
  run: |
    kubectl apply -f k8s/staging/ --namespace=staging
    kubectl rollout status deployment/brain-backend -n staging
```

---

## ⚠️ Häufige Fehler & Lösungen

| Problem | Lösung |
|---------|--------|
| "No compatible version found" | `npm ci` statt `npm install` verwenden |
| Tests fail mit DB Connection | Stelle sicher Services (postgres, redis) laufen |
| Docker Build Timeout | Erhöhe `timeout-minutes` in Workflow |
| Coverage nicht uploaded | Codecov Token prüfen oder CODECOV_TOKEN Secret setzen |
| Deploy schlägt fehl | `pre-deploy-tests` Job Logs prüfen, möglicherweise fehlende .env |

---

## 📚 Weitere Ressourcen

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Buildx Documentation](https://docs.docker.com/build/architecture/)
- [Pytest with asyncio](https://pytest-asyncio.readthedocs.io/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
