# KI1 Slice 1 - ControlDeck Contract Audit

Status: Completed (architecture/audit phase).
Scope: `frontend/control_deck` governance-relevant surfaces.

## 1. Classification model

- `real`: wired to backend contracts and primarily usable
- `drift`: partly wired but mismatched with target architecture
- `mock`: has fallback/mock data paths masking backend gaps
- `missing`: placeholder/under-construction, no functional contract path

## 2. Priority matrix (governance/provider-critical)

| Surface | Path | Classification | Current backend contract | Gap to target |
|---|---|---|---|---|
| Governance | `app/governance/page.tsx` | missing | none (placeholder) | Must become provider/governance control surface |
| LLM Settings | `app/settings/llm/page.tsx` | drift | `/api/admin/llm-config` | Legacy AXE-LLM config flow, not Provider Portal model |
| Policy | `app/policy/page.tsx` | real | policy hooks + API via `usePolicyEngine` | Needs alignment with new provider governance IA |
| Settings General | `app/settings/general/page.tsx` | missing | none | Placeholder only |
| Settings Security | `app/settings/security/page.tsx` | missing | none | Placeholder only |
| API Keys | `app/settings/api-keys/page.tsx` | drift | local form-heavy behavior | Must not become provider secret truth |
| Core Modules | `app/core/modules/page.tsx` | real | `/api/core/modules/...` | Healthy, keep as read surface |
| Missions History | `app/missions/history/page.tsx` | mock | `/api/missions/events/history` + mock fallback | Remove mock fallback once contract stabilized |
| Immune Events | `app/immune/events/page.tsx` | mock | `/api/threats/events` + mock fallback | Replace fallback by real error-state handling |
| Fred Bridge | `app/fred-bridge/*` | drift | mixed real + mock endpoints | Keep out of provider/governance critical path |

## 3. API contract findings

### Stable and reusable

- `/api/core/modules/ui-manifest`
- `/api/core/modules/{name}`
- `/api/missions/events/history`
- `/api/admin/llm-config` (exists, but architecture-drifted for provider target)

### Mixed or fallback-heavy

- `/api/threats/events` surfaces use mock fallback behavior in UI
- Fred-Bridge pages still reference mock helper routes in user-facing flows

### Missing for target governance/provider UX

- ControlDeck has no integrated Provider Portal API client yet
- No control-deck-native flow for:
  - provider registry CRUD
  - secret set/rotate/deactivate
  - model registry CRUD
  - provider test/health visualization

## 4. Navigation and IA findings

- Governance surface exists in navigation scope but is placeholder.
- LLM settings currently behave as runtime config page, not governance portal.
- Security and General settings are placeholders and should not remain in
  critical nav without implementation.

## 5. Required contract-cleanup outcomes (before UI expansion)

1. Decide and lock Provider Portal route in ControlDeck (recommended:
   `/settings/llm-providers`).
2. Keep `settings/llm` only as transition shim or explicitly deprecate after
   provider portal rollout.
3. Replace mock fallbacks in governance-critical views with explicit error/
   empty states.
4. Ensure API helper usage is standardized (`frontend/control_deck/lib/api.ts`)
   for authenticated governance flows.

## 6. Implementation priority from audit

Priority 1:
- `app/governance/page.tsx`
- provider portal route + API client layer

Priority 2:
- `app/settings/llm/page.tsx` convergence handling
- `app/settings/api-keys/page.tsx` responsibility narrowing

Priority 3:
- mock fallback cleanup in mission/immune pages
- nav cleanup for placeholder settings pages

## 7. Slice 1 exit criteria

- Governance and provider-critical surfaces are classified and prioritized.
- Contract drift points are explicit.
- ControlDeck work can proceed without architecture ambiguity.
