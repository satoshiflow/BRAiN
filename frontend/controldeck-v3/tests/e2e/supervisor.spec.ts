import { expect, test } from "@playwright/test";

import { mockAuthenticatedSession } from "./helpers/mock-session";

test("supervisor inbox and detail decision flow work for paperclip escalations", async ({ page }) => {
  let escalationStatus = "queued";
  let reviewedBy: string | null = null;
  let reviewedAt: string | null = null;
  let decisionReason: string | null = null;

  await mockAuthenticatedSession(page);

  await page.route("**/api/supervisor/escalations/domain?limit=100", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            escalation_id: "esc_123",
            status: escalationStatus,
            received_at: "2026-04-02T00:00:00Z",
            domain_key: "external_apps.paperclip.execution.axe_worker_bridge",
            requested_by: "operator-1",
            risk_tier: "high",
            correlation_id: "corr-1",
            reviewed_by: reviewedBy,
            reviewed_at: reviewedAt,
            decision_reason: decisionReason,
            notes: { action_request_id: "actreq_1" },
          },
        ],
        total: 1,
      }),
    });
  });

  await page.route("**/api/supervisor/escalations/domain/esc_123", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        escalation_id: "esc_123",
        status: escalationStatus,
        received_at: "2026-04-02T00:00:00Z",
        domain_key: "external_apps.paperclip.execution.axe_worker_bridge",
        requested_by: "operator-1",
        risk_tier: "high",
        correlation_id: "corr-1",
        reviewed_by: reviewedBy,
        reviewed_at: reviewedAt,
        decision_reason: decisionReason,
        notes: { action_request_id: "actreq_1", target_ref: "task-paperclip-1" },
      }),
    });
  });

  await page.route("**/api/supervisor/escalations/domain/esc_123/decision", async (route) => {
    escalationStatus = "approved";
    reviewedBy = "operator-1";
    reviewedAt = "2026-04-02T00:05:00Z";
    decisionReason = "Approved after supervisor review";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        escalation_id: "esc_123",
        status: escalationStatus,
        received_at: "2026-04-02T00:00:00Z",
        domain_key: "external_apps.paperclip.execution.axe_worker_bridge",
        requested_by: "operator-1",
        risk_tier: "high",
        correlation_id: "corr-1",
        reviewed_by: reviewedBy,
        reviewed_at: reviewedAt,
        decision_reason: decisionReason,
        notes: { source: "controldeck_v3_supervisor" },
      }),
    });
  });

  await page.goto("/supervisor?scope=paperclip");
  await expect(page.getByText("Supervisor Inbox")).toBeVisible();
  await expect(page.getByText("external_apps.paperclip.execution.axe_worker_bridge")).toBeVisible();

  await expect(page.locator('a[href="/supervisor/esc_123"]')).toBeVisible();
  await page.goto("/supervisor/esc_123");
  await expect(page).toHaveURL(/\/supervisor\/esc_123/);
  await expect(page.getByText("Escalation details")).toBeVisible();

  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("textbox", { name: "Reason" }).fill("Approved after supervisor review");
  await page.getByRole("button", { name: "Save decision" }).click();

  await expect(page.getByText("Status").locator("xpath=..").getByText("approved")).toBeVisible();
  await expect(page.getByText("Approved after supervisor review")).toBeVisible();
});
