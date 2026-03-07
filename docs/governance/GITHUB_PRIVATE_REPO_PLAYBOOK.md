# GitHub Private Repo Playbook

Goal: Set BRAiN repository to private while preserving safe day-to-day development (commit, push, PR, merge).

## Preconditions

- You are repo owner/admin.
- GitHub CLI is installed and authenticated.
- At least one backup admin is defined.

```bash
gh auth status
gh repo view satoshiflow/BRAiN --json nameWithOwner,isPrivate,viewerPermission
```

## 1) Set Repository to Private

```bash
gh repo edit satoshiflow/BRAiN --visibility private --accept-visibility-change-consequences
```

Verify:

```bash
gh repo view satoshiflow/BRAiN --json isPrivate --jq .isPrivate
```

Expected: `true`

## 2) Keep Access Safe (No Lockout)

- Keep at least 2 admin users (owner + backup).
- Add contributors with least privilege (`push` unless admin is required).

Add collaborator (example):

```bash
gh api -X PUT repos/satoshiflow/BRAiN/collaborators/<github-username> -f permission=push
```

Permissions:
- `pull`: read-only
- `push`: standard contributor
- `maintain`: repo maintenance without destructive admin controls
- `admin`: full control (use sparingly)

## 3) Protect `main` Branch

Recommended baseline:
- Require pull request before merge
- Require at least 1 approval
- Require status checks before merge
- Include administrators in restrictions

Example (baseline protection):

```bash
gh api -X PUT repos/satoshiflow/BRAiN/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  -f required_status_checks.strict=true \
  -F required_status_checks.contexts[]='CI / test' \
  -f enforce_admins=true \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f required_pull_request_reviews.dismiss_stale_reviews=true \
  -f restrictions='null'
```

Note: Replace status check contexts with your real check names.

## 4) Validate Workflow (Push + PR + Merge)

1. Create test branch:

```bash
git checkout -b test/private-repo-check
```

2. Make a tiny doc change and push:

```bash
git add docs/governance/GITHUB_PRIVATE_REPO_PLAYBOOK.md
git commit -m "docs: add private repo governance playbook"
git push -u origin test/private-repo-check
```

3. Open PR and merge after checks pass:

```bash
gh pr create --fill
gh pr merge --squash --auto
```

## 5) Optional Hardening

- Enable branch deletion protection.
- Require signed commits.
- Restrict who can push to `main`.
- Use CODEOWNERS for critical backend paths.

## Quick Rollback Guidance

- If someone loses access after private switch, restore via owner/admin account:

```bash
gh api -X PUT repos/satoshiflow/BRAiN/collaborators/<github-username> -f permission=push
```

- If branch protection blocks urgent fix, use admin account and temporary policy update, then restore policy immediately.
