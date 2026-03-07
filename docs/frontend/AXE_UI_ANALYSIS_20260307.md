# AXE UI Architecture Analysis (2026-03-07)

Scope: `frontend/axe_ui` only.

## 1) Architecture overview

AXE UI is implemented as a Next.js 14 App Router frontend.

Key structure:
- `app/` pages: `page.tsx`, `chat/page.tsx`, `dashboard/page.tsx`, `agents/page.tsx`, `settings/page.tsx`, `widget-test/page.tsx`
- `components/` navigation and UI primitives
- `lib/config.ts` and `lib/api.ts` API access helpers

Current interaction model:
- chat calls `POST /api/axe/chat` via `NEXT_PUBLIC_BRAIN_API_BASE`
- health checks call `/api/health`
- most "operations" views currently use mock/static data (not direct infrastructure control calls)

## 2) Communication with BRAiN APIs

Observed API usage:
- `chat/page.tsx`: `fetch(${API_BASE}/api/axe/chat)`
- `page.tsx` and `dashboard/page.tsx`: `fetch(${API_BASE}/api/health)`

Strength:
- AXE mostly talks to BRAiN HTTP APIs and does not directly connect to Redis/Postgres/Qdrant.

Issues:
- inconsistent API base defaults:
  - `lib/config.ts` and `lib/api.ts`: default production domain
  - several pages: hardcoded `http://localhost:8000` or `https://api.brain.falklabs.de`
- no centralized API client usage across all pages.

## 3) Command interface architecture

Primary command interface is the chat page (`app/chat/page.tsx`):
- keeps local conversation history
- submits structured message arrays to BRAiN
- receives textual response

Strength:
- clear human interaction flow
- mobile-aware input UX

Weakness:
- no explicit mission command mode or typed intent contract in UI layer
- no explicit context panel for mission/result rationale from supervisor.

## 4) Separation from ControlDeck responsibilities

Target separation:
- AXE = human interaction layer
- ControlDeck v2 = operations and system controls

Current status:
- good: AXE does not directly manage infra primitives (containers/workers/databases).
- weak boundary: AXE contains pages and labels with operations flavor (`dashboard`, `agents`, "manage agent fleet", "view metrics").
- these are currently mostly presentation/mock, but semantics drift toward ops dashboard territory.

## 5) Potential architectural issues

1. Responsibility drift in IA (information architecture)
- AXE navigation includes dashboard/agents/settings with ops wording.

2. Endpoint/config drift risk
- mixed API base defaults and duplicated per-page constants.

3. Mock-vs-real ambiguity
- pages display operational stats but use hardcoded/mock values, which can mislead users.

4. Widget test page import path risk
- `app/widget-test/page.tsx` imports from `../../src/components/FloatingAxe`; this should be validated against actual component tree to avoid latent runtime breakage.

## 6) Recommended improvements

Priority 1 (boundary safety):
- Reframe AXE navigation around interaction intent:
  - Keep: Home, Chat, Missions, Explanations/Results
  - Move ops-heavy concepts to ControlDeck v2 links (or remove from AXE)

Priority 2 (API consistency):
- enforce one API base resolver in `lib/config.ts`
- remove hardcoded per-page API bases
- route all fetches through `lib/api.ts`

Priority 3 (interaction-layer strengthening):
- add explicit mission command composer (human intent -> mission request)
- add result explanation panel (why/what changed)
- keep system awareness lightweight and non-operational

Priority 4 (truthful UX):
- label mock data explicitly as simulated, or wire to actual supervisor/mission endpoints

Priority 5 (hardening):
- add basic AXE integration tests:
  - chat request/response contract
  - health fetch fallback behavior
  - API base env override behavior

## Conclusion

AXE UI is close to the intended human interaction role at transport level (API-centric, no direct infra control), but its page semantics currently overlap with operations/dashboard language. To preserve architecture boundaries, AXE should be narrowed to command + interaction + explanation surfaces, while operational controls and detailed telemetry remain in ControlDeck v2.
