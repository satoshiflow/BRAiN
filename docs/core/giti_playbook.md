# giti Playbook

Operational playbook for the `giti` specialist agent when handling Git/GitHub workflows.

## Scope

- Create and maintain pull requests.
- Keep branch and PR state consistent.
- Avoid shell pitfalls in PR body generation.

## Mandatory preflight

Run these checks before any PR operation:

1. `git status -sb`
2. `gh auth status`
3. `gh pr status`

If `gh auth status` is not authenticated, stop and request `gh auth login`.

## PR decision flow

1. Determine whether a PR for `HEAD` branch already exists.
2. If PR exists, run `gh pr edit` (do not create duplicate PRs).
3. If no PR exists, run `gh pr create`.

Recommended helper checks:

- `gh pr status`
- `gh pr view <number>`

## Safe PR body handling

- Always prefer `--body-file` over large inline `--body` strings.
- Write body to a temp markdown file and pass it to `gh pr create`/`gh pr edit`.
- Do not embed shell-sensitive text (for example, unescaped backticks) directly in command strings.

## Branch sync rules

- After local commits, verify ahead/behind state with `git status -sb`.
- If ahead, push before final PR handoff.
- Confirm remote branch head after push (`git log --oneline origin/<branch> -n 1`).

## Large branch hygiene

- When the branch diverges heavily from `main`, summarize only relevant incremental changes for the current delivery step.
- Base PR summary on the intended delta (typically latest commits), not full historical branch churn.

## Standard handoff payload

Return these items to the user:

- PR URL
- PR title
- Key summary bullets (1-3)
- Verification commands executed
- Any blockers (auth, permissions, missing `gh`, CI state)
