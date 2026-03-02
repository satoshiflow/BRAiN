# Branch Protection Rules Setup

**Repository:** satoshiflow/BRAiN

## Branch Strategy

```
main  ← Production (stable releases only)
  ↑
stage ← Testing (pre-production)
  ↑
dev   ← Development (active development)
```

---

## GitHub Branch Protection Rules

### 1. Protect `main` (Production)

**Settings → Branches → Add Rule**

```yaml
Branch name pattern: main

✅ Require a pull request before merging
   ✅ Require approvals: 1
   ✅ Dismiss stale pull request approvals when new commits are pushed
   ✅ Require review from Code Owners (optional)

✅ Require status checks to pass before merging
   ✅ Require branches to be up to date before merging
   Status checks:
     - test-backend (if CI configured)
     - build-frontend (if CI configured)

✅ Require conversation resolution before merging

✅ Require signed commits (optional, recommended)

✅ Require linear history (recommended)

✅ Include administrators (recommended for consistency)

✅ Restrict pushes
   - Only allow Pull Requests
   - No direct pushes (not even admins)

✅ Allow force pushes: NO
✅ Allow deletions: NO
```

---

### 2. Protect `stage` (Testing)

```yaml
Branch name pattern: stage

✅ Require a pull request before merging
   ✅ Require approvals: 1

✅ Require status checks to pass before merging
   Status checks:
     - test-backend
     - build-frontend

✅ Require conversation resolution before merging

✅ Allow force pushes: NO
✅ Allow deletions: NO
```

---

### 3. Protect `dev` (Development)

```yaml
Branch name pattern: dev

✅ Require a pull request before merging
   ⚠️  Require approvals: 0 (auto-merge for claude/* branches)

✅ Require status checks to pass before merging (optional)
   Status checks:
     - test-backend (optional, can fail)

✅ Allow force pushes: NO
✅ Allow deletions: NO
```

---

### 4. Allow Claude Branches

```yaml
Branch name pattern: claude/*

⚠️  NO protection (Claude can push directly)

Allow:
- Direct pushes
- Force pushes (for rebases)
- Deletions (for cleanup)
```

---

## Workflow

### Development Flow

```bash
# 1. Claude creates feature branch
git checkout -b claude/new-feature-<session-id>

# 2. Claude develops and pushes
git push -u origin claude/new-feature-<session-id>

# 3. Claude creates PR to dev
gh pr create --base dev --head claude/new-feature-<session-id>

# 4. Auto-merge or manual review
# PR merges into dev

# 5. Cleanup after merge
git push origin --delete claude/new-feature-<session-id>
```

### Testing Flow

```bash
# When dev is stable, create PR: dev → stage
gh pr create --base stage --head dev \
  --title "chore: Promote dev to stage for testing" \
  --body "Testing release candidate"

# Test on stage environment (/srv/stage/)
# If tests pass, proceed to production
```

### Production Release

```bash
# Create PR: stage → main
gh pr create --base main --head stage \
  --title "release: v2.1.0" \
  --body "Production release v2.1.0"

# After merge:
# - Tag release
git tag -a v2.1.0 -m "Release v2.1.0"
git push --tags

# - Deploy to production (/srv/prod/)
```

---

## Quick Setup (GitHub CLI)

```bash
# Install GitHub CLI
brew install gh  # macOS
# or
sudo apt install gh  # Ubuntu

# Login
gh auth login

# Create branch protection rules
gh api repos/satoshiflow/BRAiN/branches/main/protection \
  --method PUT \
  --input protection-main.json

# (See protection-*.json files for rule configs)
```

---

## Manual Setup (GitHub Web UI)

1. Go to: https://github.com/satoshiflow/BRAiN/settings/branches
2. Click "Add branch protection rule"
3. Enter branch pattern (main, stage, dev)
4. Configure settings as shown above
5. Click "Create" or "Save changes"

---

## Default Branch

**Set default branch to `dev`:**

1. Go to: https://github.com/satoshiflow/BRAiN/settings
2. Scroll to "Default branch"
3. Click pencil icon
4. Select `dev`
5. Click "Update"

This ensures:
- PRs default to `dev` (not `main`)
- Clone defaults to `dev`
- GitHub UI shows `dev` by default

---

## Environment-Branch Mapping

| Environment | Branch | Server Path | Purpose |
|-------------|--------|-------------|---------|
| Development | `dev` | `/srv/dev/` | Active development |
| Staging | `stage` | `/srv/stage/` | Pre-production testing |
| Production | `main` | `/srv/prod/` | Stable releases |

---

## CI/CD Integration

GitHub Actions should deploy based on branch:

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches:
      - dev
      - stage
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to environment
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            ./deploy.sh prod
          elif [[ "${{ github.ref }}" == "refs/heads/stage" ]]; then
            ./deploy.sh stage
          elif [[ "${{ github.ref }}" == "refs/heads/dev" ]]; then
            ./deploy.sh dev
          fi
```

---

## Verification

Check protection status:

```bash
# List protected branches
gh api repos/satoshiflow/BRAiN/branches --jq '.[] | select(.protected == true) | .name'

# Check specific branch protection
gh api repos/satoshiflow/BRAiN/branches/main/protection
```

---

**Next:** Run `setup_branches.sh` to create the branches, then configure protection rules.
