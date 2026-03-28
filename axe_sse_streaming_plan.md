# AXE SSE Streaming Implementation Plan

## Overview
Implement Server-Sent Events (SSE) streaming for AXE Chat with run ID management.

## Phases

### Phase 1: Run ID Management (COMPLETED)
- **Goal:** Add run_id to ChatResponse
- **Changes:**
  - Added `run_id: Optional[str]` field to `ChatResponse` schema in `backend/app/modules/axe_fusion/router.py`
  - Both direct execution path and skillrun_bridge path now return run_id

### Phase 2: Event Emission (COMPLETED)
- **Goal:** Emit lifecycle events for direct execution path
- **Events emitted:**
  - `RUN_CREATED` - When run starts
  - `RUN_STATE_CHANGED` - From queued to running
  - `RUN_SUCCEEDED` - When chat completes successfully
- **Implementation:**
  - Used existing `AXEStreamService` from `backend/app/modules/axe_streams/service.py`
  - Events emitted at: start of direct execution and after successful completion

### Phase 3: Frontend Integration (COMPLETED)
- **Goal:** Wire up frontend to use run_id for SSE subscriptions
- **Changes:**
  - Added `run_id?: string` to `AxeChatResponse` in `frontend/axe_ui/lib/contracts.ts`
  - Frontend hook `useAXERunStream.ts` already exists with proper event handling
  - SSE endpoint at `/api/axe/runs/{run_id}/events` already implemented
- **How it works:**
  1. Frontend calls `/api/axe/chat`
  2. Response includes `run_id`
  3. Frontend uses `run_id` to subscribe to SSE events at `/api/axe/runs/{run_id}/events`
  4. Events: `axe.run.state_changed`, `axe.token.stream`, `axe.run.succeeded`, `axe.run.failed`

### Phase 4: Token Streaming (COMPLETED)
- **Goal:** Stream LLM tokens in real-time via SSE
- **Implementation:**
  - Added `stream: bool` parameter to `ChatRequest` schema (router.py line 327)
  - `AXEllmClient.stream_chat()` uses `httpx.AsyncClient.stream()` with callback (lines 280-369)
  - `AXEFusionService.stream_chat()` creates token emission callback (lines 687-800)
  - Token callback emits via `AXEStreamService.emit_token_stream()` (line 723)
  - Router calls `stream_chat()` when `stream=true` (lines 806-820)
- **How it works:**
  1. Frontend sends POST `/api/axe/chat` with `stream: true`
  2. Response returns `run_id`
  3. Frontend subscribes to GET `/api/axe/runs/{run_id}/events`
  4. Tokens stream as `axe.token.stream` events
  5. Final token includes `finish_reason`

## Files Modified

### Backend
- `backend/app/modules/axe_fusion/router.py` - Added run_id to ChatResponse and event emission

### Frontend
- `frontend/axe_ui/lib/contracts.ts` - Added run_id to AxeChatResponse type

## Testing
- RC staging gate passed (all tests)
- Direct execution path returns run_id in response
- Events are emitted to AXEStreamService
- Frontend types updated to match backend response

## Next Steps for Full Token Streaming

*None - Phase 4 implementation complete.*

## Architecture Summary

```
┌─────────────────┐     POST /api/axe/chat      ┌─────────────────┐
│   Frontend      │ ──────────────────────────▶│   Backend       │
│   AXE UI        │                            │   AXE Fusion    │
└─────────────────┘                            └────────┬────────┘
                                                         │
                                                         │ returns run_id
                                                         ▼
┌─────────────────┐     GET /api/axe/runs/{run_id}/events ┌─────────────────┐
│   EventSource   │◀─────────────────────────────────────│   SSE Endpoint │
│   (Browser)     │                                    │   (router.py)   │
└─────────────────┘                                    └────────┬────────┘
                                                              │
                                                              ▼
                                                     ┌─────────────────┐
                                                     │ AXEStreamService│
                                                     │ + Redis Pub/Sub │
                                                     └─────────────────┘
                                                              │
                           ┌───────────────┬───────────────┬┘
                           ▼               ▼               ▼
                    RUN_CREATED  RUN_STATE_CHANGED  RUN_SUCCEEDED
                    (optional)   TOKEN_STREAM       (optional)
```

## Event Types
- `axe.run.created` - Run created
- `axe.run.state_changed` - State transition (queued → running → succeeded/failed)
- `axe.token.stream` - Token delta during streaming (Phase 4)
- `axe.token.complete` - Final token with finish_reason (Phase 4)
- `axe.run.succeeded` - Run completed successfully
- `axe.run.failed` - Run failed
- `axe.error` - Error occurred