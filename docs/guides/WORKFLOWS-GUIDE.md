# 🚀 GitHub Workflows - Kompletter Guide

**Letztes Update:** 11. Dezember 2025

---

## 📋 Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Tägliche Verwendung](#tägliche-verwendung)
3. [Workflow-Details](#workflow-details)
4. [Conventions & Best Practices](#conventions--best-practices)
5. [Status Checks & Debugging](#status-checks--debugging)
6. [Notfallmaßnahmen](#notfallmaßnahmen)
7. [Checklisten](#checklisten)

---

## 🎯 Überblick

### Was sind GitHub Workflows?

Automatisierte Prozesse, die nach bestimmten Events (Push, PR, Tag) ausgelöst werden:
- **Testing** (Tests laufen automatisch)
- **Linting** (Code-Qualität)
- **Building** (Docker Images bauen)
- **Deployment** (Auf Server deployen)
- **Releasing** (Neue Versionen veröffentlichen)

### 9 Implementierte Workflows

| Workflow | Auslöser | Zweck | Dauer |
|----------|----------|-------|-------|
| **frontend-ci.yml** | Push/PR zu `frontend/**` | ESLint, TypeScript, Build | 3-5 min |
| **backend-ci.yml** | Push/PR zu `backend/**` | Ruff, MyPy, Pytest | 5-7 min |
| **lint-test.yml** | Push zu main/v2/develop | Schnelle Validation + Security | 5-10 min |
| **build.yml** | Push/PR, Manual | Docker Multi-stage Builds | 10-15 min |
| **deploy.yml** | Push zu main, Manual | Staging → Production | 15-20 min |
| **release.yml** | Tag push (v*.*.*)  | GitHub Release + Docker Push | 10-15 min |
| **code-quality.yml** | Push zu main, Weekly | Complexity, Dependencies | 5-10 min |
| **scheduled-maintenance.yml** | Weekly (Mo 3 Uhr) | Security Audits, Updates | 10-15 min |
| **pull-request.yml** | PR open/edit | Validation, Auto-Labeling | 2-3 min |

---

## 🏃 Tägliche Verwendung

### Szenario 1: Neues Feature entwickeln

```bash
# 1. Branch erstellen
git checkout -b feature/meine-funktion

# 2. Code ändern (Backend oder Frontend)
vim backend/app/main.py
# oder
vim frontend/control_deck/app/page.tsx

# 3. Lokal testen (WICHTIG!)
cd backend && pytest tests/ -v
# oder
cd frontend/control_deck && npm run build

# 4. Commit mit Conventional Commits Format
git commit -m "feat: Neue Agentenlogik hinzugefügt"
# oder
git commit -m "fix: Bug in Karma-Berechnung behoben"
# oder
git commit -m "docs: README aktualisiert"

# 5. Push zu GitHub
git push origin feature/meine-funktion

# 6. Pull Request erstellen (GitHub UI)
# https://github.com/satoshiflow/BRAiN/pulls
# Klick "New Pull Request" → compare: feature/meine-funktion → main/v2
```

**Was passiert automatisch:**
1. ✅ `pull-request.yml` validiert PR Title + Description
2. ✅ `pull-request.yml` fügt automatisch Labels hinzu (backend, frontend, etc.)
3. ✅ `pull-request.yml` schlägt Reviewer vor (CODEOWNERS)
4. ✅ `backend-ci.yml` ODER `frontend-ci.yml` läuft (je nachdem was du changed hast)
5. ✅ `lint-test.yml` läuft (zusätzlich, für schnelle Feedback)
6. ✅ Du siehst Status Checks: ✅ oder ❌

**Deine Aufgaben:**
- ✅ Alle Status Checks müssen grün sein
- ✅ Code Review von anderen
- ✅ Merge zu `main` oder `v2` (wenn alles ok)

---

### Szenario 2: Bug fixen

```bash
# 1. Branch für Bug
git checkout -b fix/karma-timeout

# 2. Code ändern
vim backend/app/modules/karma/core/service.py

# 3. Tests schreiben/updaten
vim backend/tests/test_karma.py

# 4. Lokal testen
cd backend && pytest tests/test_karma.py -v

# 5. Commit
git commit -m "fix: Karma-Berechnung bei großen Agenten-Mengen"
git commit -m "test: Added test case for karma timeout"

# 6. Push
git push origin fix/karma-timeout

# 7. PR erstellen → Merge → Auto-Deploy
```

**Status Checks:**
- `lint-test` ✅ (Schnelle Checks)
- `backend-ci` ✅ (Tests mit PostgreSQL + Redis)
- Green = Ready to merge!

---

### Szenario 3: Frontend ändern

```bash
# 1. Branch
git checkout -b ui/dashboard-redesign

# 2. Code ändern
vim frontend/control_deck/components/Dashboard.tsx

# 3. Lokal bauen
cd frontend/control_deck && npm run build

# 4. Type-Check
npm run type-check

# 5. Commit
git commit -m "feat: New dashboard layout with charts"

# 6. Push
git push origin ui/dashboard-redesign

# Status Checks laufen automatisch
```

---

### Szenario 4: Nach Merge - Automatisches Deployment

```
Du: Merge PR zu main
    ↓
GitHub: build.yml startet
    ├─→ Backend Docker Build
    ├─→ Control Deck Docker Build
    ├─→ Axe UI Docker Build
    └─→ Nginx Docker Build
    ↓
Images zu ghcr.io gepusht
    ↓
GitHub: deploy.yml startet (nur wenn Push zu main)
    ├─→ pre-deploy-tests (Integration Tests)
    ├─→ deploy-staging (Test Environment)
    │   ├─ Health Checks
    │   └─ GitHub Comment (Deployment Info)
    └─→ deploy-production (Nur mit Approval!)
        ├─ Weitere Health Checks
        ├─ Smoke Tests
        └─ Success Notification

✅ Live auf Production!
```

**Deine Aufgaben:**
- Nur Code mergen, der Tests besteht ✅
- Eventuell Production Deployment genehmigen
- Bei Failure: Logs prüfen + Manual Rollback möglich

---

### Szenario 5: Neue Version Release

```bash
# 1. CHANGELOG.md aktualisieren
vim CHANGELOG.md

# Füg ein unter "## Unreleased":
# ## [2.0.0] - 2025-12-11
# ### Added
# - Feature X
# - Feature Y
# ### Fixed
# - Bug A
# ### Changed
# - Breaking change B

# 2. Commit
git add CHANGELOG.md
git commit -m "bump: Version 2.0.0"

# 3. Tag erstellen
git tag v2.0.0

# 4. Push
git push origin v2.0.0

# Fertig! ✅ Alles läuft automatisch
```

**Was passiert automatisch:**
1. ✅ `release.yml` validiert Version Format (v2.0.0)
2. ✅ `release.yml` prüft CHANGELOG.md
3. ✅ Baut Docker Images mit Tags:
   - `backend:2.0.0`
   - `control-deck:2.0.0`
   - `axe-ui:2.0.0`
   - `nginx:2.0.0`
   - Auch als `:latest`
4. ✅ Pusht zu ghcr.io (GitHub Container Registry)
5. ✅ Erstellt GitHub Release mit Changelog

**Du musst nichts weiter machen!** 🎉

---

## 🔧 Workflow-Details

### 1. frontend-ci.yml (Frontend CI)

**Trigger:**
- Push zu Branches mit `frontend/**` Changes
- PRs zu `frontend/**`

**Jobs:**
1. `lint-control-deck` - ESLint + TypeScript
2. `lint-axe-ui` - ESLint + TypeScript
3. `build-control-deck` - Next.js Build
4. `build-axe-ui` - Next.js Build

**Features:**
- NPM Dependency Caching (schneller)
- Type-Check mit TypeScript Compiler
- Build Artifacts für später

**Fehlerbeispiele:**
```
❌ ESLint failed: Missing semicolon
Fix: npm run lint -- --fix

❌ Type error: Property 'foo' not found
Fix: Prüf deine TypeScript Types

❌ Build failed: Module not found
Fix: npm ci (reinstall dependencies)
```

---

### 2. backend-ci.yml (Backend CI)

**Trigger:**
- Push zu Branches mit `backend/**` Changes
- PRs zu `backend/**`

**Jobs:**
1. `lint` - Ruff + Pylint Linting
2. `type-check` - MyPy Type-Checking
3. `test` - Pytest mit PostgreSQL + Redis Services

**Features:**
- PostgreSQL pgvector Support
- Redis für Cache Tests
- Coverage Reporting zu Codecov
- Python 3.11 Standard

**Fehlerbeispiele:**
```
❌ Ruff error: Import not used
Fix: Remove import or use it

❌ Type error: Expected str, got int
Fix: Add type hints or convert type

❌ Test failed: AssertionError
Fix: Prüf deine Test-Logic oder Code
```

**Lokal testen:**
```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Services starten (Docker Compose)
docker-compose up postgres redis

# Tests laufen
pytest tests/ -v
```

---

### 3. lint-test.yml (Quick Validation)

**Trigger:**
- Immer bei Push zu main/v2/develop
- PR Creation/Update

**Jobs:**
1. `backend-lint-test` - Backend Ruff + Pytest
2. `frontend-lint` - Frontend ESLint (matrix: beide apps)
3. `security-scan` - Trivy Vulnerability Scan
4. `health-check` - Docker Compose Validierung

**Besonderheit:** Läuft für ALLE PRs, nicht nur auf bestimmte Paths

---

### 4. build.yml (Docker Builds)

**Trigger:**
- Push zu main/v2/develop
- PRs (nur Build, kein Push)
- Manual Trigger (workflow_dispatch)

**Jobs (parallel):**
- `build-backend` - Python FastAPI
- `build-control-deck` - Next.js
- `build-axe-ui` - Next.js
- `build-nginx` - Reverse Proxy

**Features:**
- Multi-stage Docker Builds
- GitHub Actions Cache (schneller)
- Push zu ghcr.io nur bei Push (nicht bei PR)

**Tags:**
```
ghcr.io/satoshiflow/BRAiN/backend:v2       # Branch name
ghcr.io/satoshiflow/BRAiN/backend:abc123   # Git SHA
ghcr.io/satoshiflow/BRAiN/backend:latest   # Main branch only
ghcr.io/satoshiflow/BRAiN/backend:2.0.0    # Release version
```

---

### 5. deploy.yml (Deployment Pipeline)

**Trigger:**
- Push zu main Branch
- Manual Trigger (workflow_dispatch)
- Nach erfolgreichem build.yml

**Jobs:**
1. `pre-deploy-tests` - Integration Tests
2. `deploy-staging` - Test Environment
3. `deploy-production` - Live Environment (mit Approval)
4. `rollback` - Auto-Rollback bei Failure

**Features:**
- Environment-basierte Deployments
- GitHub Deployment API Integration
- Health Checks nach Deploy
- Automatic Rollback bei Failure

**Deployment Optionen (konfigurierbar):**
```yaml
# Option 1: Docker Compose (Self-hosted)
docker-compose -f docker-compose.yml up -d

# Option 2: Kubernetes
kubectl apply -f k8s/staging/
kubectl apply -f k8s/production/

# Option 3: Cloud (AWS ECS, Google Cloud Run)
# Anpassbar je nach Platform
```

---

### 6. release.yml (Release Management)

**Trigger:**
- Git Tag Push (v*.*.*)
- Manual mit Version Input

**Jobs:**
1. `validate-release` - Version Format Check
2. `build-release` - Docker Images mit Version
3. `create-github-release` - GitHub Release erstellen
4. `notify-release` - Benachrichtigung

**Features:**
- Semantic Version Validation
- CHANGELOG.md Verification
- OCI Image Labels (version, revision)

---

### 7. code-quality.yml (Quality Analysis)

**Trigger:**
- Push zu main/v2/develop
- PRs
- Weekly Schedule

**Jobs:**
- `code-complexity` - Radon Analysis (Cyclomatic, Maintainability)
- `dependency-check` - pip-audit + npm audit
- `documentation` - Prüf fehlende README files
- `test-coverage-report` - Coverage Report + PR Comment

---

### 8. scheduled-maintenance.yml (Wöchentliche Checks)

**Trigger:**
- Jeden Montag 3 Uhr UTC

**Jobs:**
- `dependencies-update` - Outdated Packages Check
- `docker-cleanup` - Old Image Cleanup
- `base-images-update` - Base Image Updates
- `security-audit-schedule` - Trivy Full Scan
- `database-backup-check` - Backup Verification
- `logs-and-monitoring-check` - Monitoring Setup Validation

---

### 9. pull-request.yml (PR Management)

**Trigger:**
- PR open/edit/synchronize

**Jobs:**
- `validate-pr` - PR Title + Body Validation
- `label-pr` - Auto-Label basierend auf Files
- `request-reviewers` - Reviewer Suggestion (CODEOWNERS)
- `changelog-check` - Prüf CHANGELOG.md Update
- `commit-lint` - Commit Message Validation
- `code-review-assistant` - Suggestions für Reviewer

---

## 📝 Conventions & Best Practices

### 1. Conventional Commits Format

**MUSS sein für automatische Changelog + Validierung!**

```bash
# Format
git commit -m "<type>(<scope>): <description>"

# Types
feat:     # Neue Feature
fix:      # Bug Fix
docs:     # Dokumentation
style:    # Code Formatting (keine Logic Change)
refactor: # Code Restructuring
test:     # Tests hinzufügen/updaten
chore:    # Maintenance (Dependencies, etc.)
ci:       # CI/CD Changes

# Scope (Optional)
(karma)      # Welches Modul/Feature
(missions)
(frontend)
(database)

# Description
# - Kleinbuchstaben
# - Imperativ ("add", nicht "added")
# - Keine Periode am Ende

# ✅ RICHTIG
git commit -m "feat(karma): Add reputation decay calculation"
git commit -m "fix(missions): Handle null deadline gracefully"
git commit -m "docs: Update deployment guide"
git commit -m "test: Add edge case tests for evolution"

# ❌ FALSCH
git commit -m "update"
git commit -m "WIP"
git commit -m "Fixed bug"  # Großbuchstabe
git commit -m "Add new feature in karma module"  # Scope fehlt
```

**Warum?**
- ✅ Automatische Changelog Generation
- ✅ Semantic Versioning (auto major/minor/patch)
- ✅ PR Validation
- ✅ Better Git History

---

### 2. Pull Request Format

```markdown
# PR Title (MUSS Conventional Commits Format sein!)
feat(missions): Add deadline enforcement

## Beschreibung
Missions können jetzt mit Deadlines erstellt werden. Das System enforced
automatisch Deadlines und markiert Missions als "expired" wenn sie überschritten.

## Type of Change
- [ ] Bug fix (non-breaking)
- [x] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation update

## Changes
- Added deadline parameter to Mission schema
- Added deadline enforcement in executor
- Added expiration check in mission list
- Added tests for deadline validation

## Testing
Lokal getestet mit:
- PostgreSQL (migrations included)
- Redis (cache invalidation)
- 15 neue Pytest test cases
- Coverage: 87%

## Breaking Changes
Keine

## Deployment Notes
- Keine DB Migration nötig
- Backward compatible mit v1.9

## Checklist
- [x] Tests added/updated
- [x] CHANGELOG.md updated
- [x] Documentation updated
- [x] Code reviewed
- [x] All status checks passing
```

---

### 3. Branch Naming

```bash
# Feature
git checkout -b feature/mission-deadlines
git checkout -b feature/agent-learning

# Bug Fix
git checkout -b fix/karma-timeout
git checkout -b fix/memory-leak

# Documentation
git checkout -b docs/deployment-guide
git checkout -b docs/api-reference

# Infrastructure
git checkout -b infra/docker-optimization
git checkout -b infra/kubernetes-setup

# Refactoring
git checkout -b refactor/mission-executor
git checkout -b refactor/event-bus
```

---

### 4. CHANGELOG.md Format

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- New features here

### Fixed
- Bug fixes here

### Changed
- Changes here

### Removed
- Removed features here

### Security
- Security fixes here

## [2.0.0] - 2025-12-11

### Added
- Karma reputation system with decay
- Mission deadline enforcement
- Agent evolution with genetic algorithms
- Multi-tenant support

### Fixed
- Fixed database connection pooling
- Fixed memory leak in event bus

### Changed
- Breaking: Removed deprecated credits API
- Updated all dependencies

### Security
- Fixed SQL injection vulnerability
- Updated security headers
```

---

## 🔍 Status Checks & Debugging

### Status Checks auf PR sehen

```
✅ lint-test - All checks passed
   └─→ Backend linting, tests
   └─→ Frontend linting, build
   └─→ Security scan passed

✅ backend-ci - All checks passed
   └─→ Ruff check passed
   └─→ MyPy type-check passed
   └─→ Pytest passed (95% coverage)

✅ frontend-ci - All checks passed
   └─→ ESLint passed
   └─→ TypeScript check passed
   └─→ Build successful

✅ build - Docker images built
   └─→ All images pushed to ghcr.io
```

---

### Wenn Status Check RED ist (❌)

**Schritt 1: Click auf roten Check**
```
PR → Status Checks → Click auf ❌ Check → "Details"
```

**Schritt 2: Error Logs lesen**
```
Build logs zeigen genau wo der Fehler ist
z.B.: "ruff check failed: E501 line too long"
```

**Schritt 3: Lokal fixen**

**Beispiel 1: Ruff Error (Backend)**
```bash
cd backend

# Error sehen
ruff check app/

# Auto-fix versuchen
ruff check app/ --fix

# Manuell fixen wenn nötig
# z.B. Imports entfernen, Zeilen kürzen

# Testen
ruff check app/  # Sollte jetzt ✅ sein
```

**Beispiel 2: Test Failed (Backend)**
```bash
cd backend

# Test lokal laufen
pytest tests/ -v

# Spezifischer Test
pytest tests/test_karma.py::test_reputation_decay -v

# Mit mehr Info
pytest tests/ -v -s  # -s zeigt print() statements

# Fehler fixen
vim app/modules/karma/core/service.py

# Nochmal testen
pytest tests/ -v
```

**Beispiel 3: Build Failed (Frontend)**
```bash
cd frontend/control_deck

# Dependencies neu installieren
npm ci

# Type-Check
npm run type-check

# Build
npm run build

# Fehler debuggen
# z.B. TypeScript Error
# Property 'foo' does not exist
# → Prüf deine Types/Interfaces
```

**Beispiel 4: Type Error (Backend)**
```bash
cd backend

# MyPy type-check
mypy app/ --ignore-missing-imports

# Error sehen und fixen
vim app/modules/karma/core/service.py
# Füg Type Hints ein oder fix Type Mismatch

# Nochmal testen
mypy app/
```

---

### Häufige Fehler & Lösungen

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| `E501 line too long` | Zeile > 88 Zeichen | Zeile brechen oder `# noqa: E501` |
| `F401 unused import` | Import wird nicht benutzt | Import entfernen oder nutzen |
| `Type error: Expected str, got int` | Type Mismatch | Type Hint hinzufügen oder konvertieren |
| `AssertionError in tests` | Test schlägt fehl | Test-Logic oder Code fixen |
| `ModuleNotFoundError` | Modul nicht installiert | `pip install -r requirements.txt` |
| `npm ERR! peer dependency missing` | npm Conflict | `npm ci` statt `npm install` |
| `TypeScript error: not assignable` | Type Incompatibility | Types korrigieren |
| `Docker build failed` | Dockerfile Error | Dockerfile prüfen, z.B. RUN commands |

---

## 🚨 Notfallmaßnahmen

### Szenario 1: Deploy schief gelaufen

```
Production zeigt Error

Schneller Fix:
1. GitHub Actions → deploy.yml → Check Logs
2. Identify Problem
3. Fix lokal: git commit -m "hotfix: ..."
4. Push: git push origin main
5. deploy.yml läuft nochmal automatisch
6. Rollback ist automatisch aktiviert, falls nötig
```

---

### Szenario 2: Tests fallen immer durch

```
Status Check ❌ trotz lokalem Fix

Debug:
1. Full log lesen (nicht nur Error Message)
2. Services prüfen (PostgreSQL, Redis laufen?)
3. pip install oder npm ci neu machen
4. Clean rebuild: docker-compose down && docker-compose up
5. Spezifischen Test laufen: pytest tests/test_xyz.py -v
```

---

### Szenario 3: Versehentlich zu main gemergt

```
Merge war Mistake (z.B. nicht fertig entwickelt)

Fix:
1. GitHub: Revert PR erstellen (Button auf Merge Commit)
2. Code lokal fixen
3. Neu committen zu richtigem Branch
4. Nochmal PR erstellen

Oder manuell:
git revert <commit-sha>
git push origin main
```

---

### Szenario 4: Ich will manuell deployen

```
GitHub Actions UI:

1. Geh zu Actions Tab
2. Filter: Deploy Workflow
3. Click "Run workflow"
4. Wähl Branch (main, v2, etc.)
5. Click grüner "Run workflow" Button

Workflow startet → Staging → Production
```

---

### Szenario 5: Docker Image zu ghcr.io pushen

```
Normalerweise automatisch bei build.yml

Manuell (falls nötig):
# Local Docker Push (requires authentication)
docker login ghcr.io -u USERNAME -p GITHUB_TOKEN
docker tag backend:latest ghcr.io/satoshiflow/BRAiN/backend:latest
docker push ghcr.io/satoshiflow/BRAiN/backend:latest

Aber: Besser über build.yml laufen lassen (automatisch + konsistent)
```

---

## ✅ Checklisten

### Checkliste BEVOR du Code pushst

- [ ] Code lokal getestet
- [ ] Tests laufen: `pytest tests/ -v` (Backend)
- [ ] Tests laufen: `npm run build` (Frontend)
- [ ] Linting: `ruff check backend/`
- [ ] Type-Check: `mypy backend/`
- [ ] CHANGELOG.md aktualisiert (bei Features/Fixes)
- [ ] Commit Message folgt Conventional Commits: `feat: ...`
- [ ] Branch Name ist aussagekräftig: `feature/xyz`
- [ ] Keine sensiblen Daten commitet (API Keys, Passwords)

---

### Checkliste für PR

- [ ] PR Title folgt Conventional Commits Format
- [ ] PR Description ist aussagekräftig
- [ ] Tests sind geschrieben/aktualisiert
- [ ] Code Coverage ist nicht gesunken
- [ ] CHANGELOG.md ist aktualisiert
- [ ] Dokumentation ist aktualisiert (falls nötig)
- [ ] Alle Status Checks sind grün ✅
- [ ] Mindestens 1 Code Review bestanden
- [ ] Keine `console.log()` oder `print()` Debug Statements
- [ ] Breaking Changes dokumentiert (falls vorhanden)

---

### Checkliste für Release

- [ ] CHANGELOG.md unter `## Unreleased` aktualisiert
- [ ] Alle Features/Bugfixes dokumentiert
- [ ] Version Bump geplant (major.minor.patch)
- [ ] Commit erstellt: `bump: Version x.y.z`
- [ ] Tag erstellt: `git tag vx.y.z`
- [ ] Tag gepusht: `git push origin vx.y.z`
- [ ] release.yml läuft automatisch
- [ ] GitHub Release wurde erstellt
- [ ] Docker Images sind auf ghcr.io

---

### Checkliste für Deployment

- [ ] Feature ist komplett + tested
- [ ] PR Review bestanden
- [ ] Zu main/v2 gemergt
- [ ] build.yml hat Docker Images gebaut
- [ ] deploy.yml startet automatisch
- [ ] Staging Deployment erfolgreich
- [ ] Production Approval gegeben
- [ ] Production Deployment erfolgreich
- [ ] Health Checks grün
- [ ] Monitoring zeigt keine Errors
- [ ] User können Feature nutzen

---

## 📚 Weitere Ressourcen

### Dokumentationen im Repo
```
.github/WORKFLOWS.md               ← Detaillierte Workflow-Dokumentation
.github/AUTOMATION-CHECKLIST.md    ← Roadmap für weitere Automatisierung
.github/CODEOWNERS                 ← Reviewer-Zuweisung
docs/WORKFLOWS-GUIDE.md            ← Diese Datei
DEVELOPMENT.md                     ← Lokale Setup
README.md                          ← Project Overview
CHANGELOG.md                       ← Release History
```

### Externe Links
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

---

## 🎓 Quick Reference

### Häufige Commands

```bash
# Branch Management
git checkout -b feature/xyz              # Neuer Branch
git push origin feature/xyz              # Zu GitHub pushen
git pull origin main                     # Latest von main

# Commits
git commit -m "feat: Description"        # Conventional Commits
git commit --amend                       # Letzten Commit editieren
git reset HEAD~1                         # Letzten Commit rückgängig

# Tags (Releases)
git tag v2.0.0                           # Tag erstellen
git push origin v2.0.0                   # Tag pushen
git tag -d v2.0.0                        # Tag löschen

# Testing
pytest tests/ -v                         # Alle Tests Backend
pytest tests/test_xyz.py -v              # Spezifischer Test
npm run build                            # Frontend bauen
npm run lint                             # Frontend lint

# Linting
ruff check backend/                      # Ruff linting
mypy backend/                            # Type-Check
npm run lint                             # Frontend ESLint
```

---

## 💡 Pro-Tipps

**1. Lokal Docker Compose testen (wie Production):**
```bash
docker-compose up -d
# Dein ganzes System läuft jetzt lokal
# Ports: http://localhost:3000 (Frontend)
#        http://localhost:8000 (Backend API)
```

**2. GitHub Actions Log streamen:**
```bash
# Mit GitHub CLI
gh run watch 123456
# Zeigt Logs in Echtzeit
```

**3. Commits vor Push üben:**
```bash
# Commit ohne zu pushen
git commit -m "feat: xyz"

# Noch zurück kann man mit:
git reset HEAD~1
```

**4. Schnell PR Status checken:**
```bash
# Mit GitHub CLI
gh pr view 42 --web
# Öffnet PR im Browser
```

**5. Alte Branches löschen:**
```bash
# Nach Merge
git branch -D feature/xyz
# Remote auch löschen
git push origin --delete feature/xyz
```

---

## 📞 Support & Kontakt

Falls Problems mit Workflows:

1. **Logs lesen** → GitHub Actions UI
2. **.github/WORKFLOWS.md** → Detaillierte Infos
3. **Diese Datei (WORKFLOWS-GUIDE.md)** → Praktische Beispiele
4. **GitHub Docs** → Offizielle Dokumentation

---

**Zuletzt aktualisiert:** 11. Dezember 2025  
**Workflows Version:** 2.0  
**Repository:** [BRAiN](https://github.com/satoshiflow/BRAiN)
