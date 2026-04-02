import { expect, test } from "@playwright/test";

import { mockAuthenticatedSession } from "./helpers/mock-session";

test("external operations supports action approval and supervisor deep-links", async ({ page }) => {
  let pendingRequests = [
    {
      request_id: "actreq_1",
      tenant_id: "tenant-a",
      principal_id: "operator-1",
      action: "request_escalation",
      reason: "Needs supervisor review",
      status: "pending",
      target_type: "execution",
      target_ref: "task-paperclip-1",
      skill_run_id: "run-1",
      mission_id: "mission-1",
      decision_id: "rdec-1",
      correlation_id: "corr-1",
      created_at: "2026-04-02T00:00:00Z",
      updated_at: "2026-04-02T00:00:00Z",
      execution_result: {},
    },
  ];

  await mockAuthenticatedSession(page);

  await page.route("**/api/runtime-control/resolve", async (route) => {
    const body = JSON.stringify({
      decision_id: "rdec-1",
      effective_config: {
        workers: { external: { paperclip: { enabled: true }, openclaw: { enabled: true } } },
        security: { allowed_connectors: ["paperclip", "openclaw"] },
      },
      selected_model: "gpt-5.4",
      selected_worker: "paperclip",
      selected_route: "external_executor.paperclip",
      applied_policies: [],
      applied_overrides: [],
      explain_trace: [],
      validation: { valid: true, issues: [] },
    });
    await route.fulfill({ status: 200, contentType: "application/json", body });
  });

  await page.route("**/api/tasks?task_type=paperclip_work&limit=20", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "00000000-0000-0000-0000-000000000001",
            task_id: "task-paperclip-1",
            name: "Paperclip TaskLease",
            description: "External execution",
            task_type: "paperclip_work",
            category: "skill_engine",
            tags: ["paperclip"],
            status: "failed",
            priority: 75,
            payload: {},
            config: {},
            tenant_id: "tenant-a",
            mission_id: "mission-1",
            skill_run_id: "run-1",
            correlation_id: "corr-1",
            claimed_by: null,
            claimed_at: null,
            started_at: null,
            completed_at: null,
            result: null,
            error_message: "Connector timed out",
            created_at: "2026-04-02T00:00:00Z",
            updated_at: "2026-04-02T00:00:00Z",
          },
        ],
        total: 1,
        by_status: { failed: 1 },
      }),
    });
  });

  await page.route("**/api/tasks?task_type=openclaw_work&limit=20", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0, by_status: {} }),
    });
  });

  await page.route("**/api/runtime-control/timeline?limit=120", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            event_id: "evt-1",
            event_type: "external.action_request.paperclip.approved.v1",
            entity_type: "external_action_request",
            entity_id: "actreq_1",
            actor_id: "operator-1",
            actor_type: "human",
            tenant_id: "tenant-a",
            correlation_id: "corr-1",
            created_at: "2026-04-02T00:00:00Z",
            payload: {
              target_type: "execution",
              target_ref: "task-paperclip-1",
              skill_run_id: "run-1",
              decision_id: "rdec-1",
              execution_result: { supervisor_escalation_id: "esc_123" },
            },
          },
        ],
        total: 1,
      }),
    });
  });

  await page.route("**/api/external-apps/paperclip/action-requests", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: pendingRequests, total: pendingRequests.length }),
    });
  });

  await page.route("**/api/external-apps/paperclip/action-requests/actreq_1/approve", async (route) => {
    pendingRequests = [];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        request_id: "actreq_1",
        tenant_id: "tenant-a",
        principal_id: "operator-1",
        action: "request_escalation",
        reason: "Needs supervisor review",
        status: "approved",
        target_type: "execution",
        target_ref: "task-paperclip-1",
        skill_run_id: "run-1",
        mission_id: "mission-1",
        decision_id: "rdec-1",
        correlation_id: "corr-1",
        created_at: "2026-04-02T00:00:00Z",
        updated_at: "2026-04-02T00:01:00Z",
        approved_by: "operator-1",
        approved_at: "2026-04-02T00:01:00Z",
        decision_reason: "Approved via ControlDeck",
        execution_result: { supervisor_escalation_id: "esc_123", supervisor_status: "queued" },
      }),
    });
  });

  await page.route("**/api/supervisor/escalations/domain?limit=20", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            escalation_id: "esc_123",
            status: "queued",
            received_at: "2026-04-02T00:00:00Z",
            domain_key: "external_apps.paperclip.execution.axe_worker_bridge",
            requested_by: "operator-1",
            risk_tier: "high",
            correlation_id: "corr-1",
            reviewed_by: null,
            reviewed_at: null,
            decision_reason: null,
            notes: {},
          },
        ],
        total: 1,
      }),
    });
  });

  await page.goto("/external-operations");

  await expect(page.getByText("External Operations")).toBeVisible();
  await expect(page.getByText("Action Request Inbox")).toBeVisible();
  await expect(page.getByText("Supervisor Inbox")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open detail" })).toBeVisible();

  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("textbox", { name: "Reason" }).fill("Approved for supervisor escalation");
  await page.getByRole("button", { name: "Approve request" }).click();

  await expect(page.getByText("Keine offenen Requests.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open inbox" })).toBeVisible();
});
