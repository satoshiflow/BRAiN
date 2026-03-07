# Secrets Reference (Local, Non-Value)

Purpose: track required secret names without storing real secret values in docs.

## Rules

- Do not commit real secret values into repository docs.
- Keep real values in local `.env` files or secret manager.
- Use placeholders in all committed artifacts.

## Secret variables in active local setup

- `OPENROUTER_API_KEY`
- `BRAIN_DMZ_GATEWAY_SECRET`
- `BRAIN_JWT_PRIVATE_KEY` (optional in local; ephemeral fallback active for development)
- `POSTGRES_PASSWORD`

## Local source locations (for operator only)

- Project root: `.env`
- Backend runtime: `backend/.env`

## Rotation guidance

- Rotate `BRAIN_DMZ_GATEWAY_SECRET` before staging/prod.
- Replace placeholder `OPENROUTER_API_KEY` before external model usage.
- Provide stable `BRAIN_JWT_PRIVATE_KEY` for non-ephemeral auth tokens in staging/prod.
