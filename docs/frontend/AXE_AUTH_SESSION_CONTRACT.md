# AXE Auth Session Contract

Purpose: define the minimal runtime contract between AXE UI auth state and BRAiN auth endpoints so session behavior stays secure and predictable.

## Session states

- `loading`: auth mutation in progress (`login` only in current implementation)
- `authenticated`: access token, refresh token, and user profile are loaded and usable
- `unauthenticated`: no usable session remains; protected requests must not proceed

## Backend endpoint expectations

- `POST /api/auth/login`
  - `200`: returns `TokenPair`
  - `401`: invalid credentials
- `GET /api/auth/me`
  - `200`: returns current user profile
  - `401`: access token invalid/expired
  - `403`: user disabled
- `POST /api/auth/refresh`
  - `200`: returns rotated `TokenPair`
  - `401`: refresh token invalid/expired
  - `403`: user disabled
  - `503`: auth backend temporarily unavailable
- `POST /api/auth/logout`
  - `204`: revoke success or already effectively logged out

## AXE UI runtime rules

1. Requests use the current access token.
2. Only a real `401` triggers refresh retry logic.
3. If refresh succeeds:
   - replace access token
   - replace refresh token
   - reload current user profile
   - retry the original request exactly once
4. If refresh fails:
   - clear all local auth state
   - surface the refresh failure to the caller
5. Logout always clears local auth state, even if backend revocation fails.

## Security posture

- Unauthorized detection must use status-aware errors, not fragile message substring guessing alone.
- AXE UI must fail closed on refresh failure.
- Invitation links must come from configuration, never hardcoded product URLs in runtime code.

## Current verification

- Backend auth refresh coverage:
  - `backend/tests/test_auth_refresh_e2e.py`
  - `backend/tests/test_auth_invitation_urls.py`
- AXE UI session coverage:
  - `frontend/axe_ui/hooks/__tests__/useAuthSession.test.tsx`
